import logging
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, case, desc, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from event_service.schemas.bookings import (
    AllBookingsEventDetails,
    AllBookingsItemResponse,
    AllBookingsListResponse,
    BookingCreateRequest,
    BookingDetailsResponse,
    BookingEventDetails,
    BookingResponse,
    BookingStatusUpdateRequest,
    BookingUserDetails,
    BookingWithEventResponse,
    BookingWithUserResponse,
    OrganizerBookingDetails,
    OrganizerBookingsResponse,
    OrganizerEventDetails,
    OrganizerEventsCount,
    OrganizerEventWithSlots,
    OrganizerSlotDetails,
    SimpleOrganizerBookingItem,
    SimpleOrganizerBookingsResponse,
    UserBookingItemResponse,
    UserBookingsListResponse,
)
from event_service.services.seat_holding import (
    cleanup_expired_holds,
    get_held_seats_count,
    hold_seats,
)
from shared.db.models import (
    AdminUser,
    BookingStatus,
    Event,
    EventBooking,
    EventSlot,
    EventStatus,
)
from shared.utils.file_uploads import get_media_url
from shared.utils.id_generators import generate_digits_letters

logger = logging.getLogger(__name__)


async def _determine_slot_key_from_time(
    db: AsyncSession, event_id: str, slot_time: str, booking_date: str
) -> Optional[str]:
    """
    Determine the slot_key (e.g., 'slot_1') from the slot time string.

    Args:
        db: Database session
        event_id: Event ID
        slot_time: Time string (e.g., "10:00 AM - 12:00 PM")
        booking_date: Date string (e.g., "2024-01-15")

    Returns:
        Slot key (e.g., "slot_1") or None if not found
    """
    try:
        # Get event and its slot data
        event_query = select(Event).where(Event.event_id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            return None

        # Get event slot
        slot_query = select(EventSlot).where(EventSlot.slot_id == event.slot_id)
        slot_result = await db.execute(slot_query)
        event_slot = slot_result.scalar_one_or_none()

        if not event_slot or not event_slot.slot_data:
            return None

        # Search through slot data to find matching time
        for date_key, date_slots in event_slot.slot_data.items():
            if date_key == booking_date and isinstance(date_slots, dict):
                for slot_key, slot_info in date_slots.items():
                    start_time = slot_info.get("start_time", "")
                    end_time = slot_info.get("end_time", "")

                    # Create possible time format combinations for matching
                    possible_formats = [
                        f"{start_time} - {end_time}",
                        f"{start_time}:00 - {end_time}:00",
                        f"{start_time} AM - {end_time} PM",
                        f"{start_time} PM - {end_time} PM",
                        f"{start_time} AM - {end_time} AM",
                    ]

                    if slot_time in possible_formats or (
                        start_time in slot_time and end_time in slot_time
                    ):
                        return slot_key

        return None

    except Exception as e:
        logger.error(f"Error determining slot key from time: {str(e)}")
        return None


def _extract_slot_time(event: Event, slot: str) -> Optional[str]:
    """
    Extract slot time information from event slot data.

    Args:
        event: The event object with slot data
        slot: The slot string to find time information for

    Returns:
        Formatted time string (e.g., "10:00 AM - 12:00 PM") or None if not found
    """
    if not event or not hasattr(event, "slots") or not event.slots:
        return None

    try:
        # Look through all event slots to find matching slot data
        for event_slot in event.slots:
            if not event_slot.slot_data:
                continue

            # slot_data is a JSONB field containing date -> slot mappings
            for date_key, date_slots in event_slot.slot_data.items():
                if isinstance(date_slots, dict):
                    for slot_key, slot_details in date_slots.items():
                        # Check if this slot matches the booking slot
                        if slot_key == slot or slot == slot_key:
                            start_time = slot_details.get("start_time")
                            end_time = slot_details.get("end_time")

                            if start_time and end_time:
                                return f"{start_time} - {end_time}"
                            elif start_time:
                                return start_time

        # If no specific time found, return the slot string as is
        return slot

    except Exception as e:
        logger.warning(
            f"Error extracting slot time for slot '{slot}': {str(e)}"
        )
        return slot


def _extract_event_address(event: Event) -> Optional[str]:
    """
    Extract event address from extra_data field.

    Args:
        event: The event object with extra_data

    Returns:
        Address string from extra_data or None if not found
    """
    if not event or not event.extra_data:
        return None

    try:
        # Look for common address field names in extra_data
        address_fields = [
            "address",
            "event_address",
            "location_address",
            "venue_address",
        ]

        for field in address_fields:
            if field in event.extra_data and event.extra_data[field]:
                return str(event.extra_data[field])

        return None

    except Exception as e:
        logger.warning(f"Error extracting event address: {str(e)}")
        return None


async def check_existing_booking(
    db: AsyncSession, user_id: str, event_id: str, slot: str, booking_date: date
) -> Tuple[bool, str, Optional[EventBooking]]:
    """
    Check if user has existing booking for the same event and slot.
    Returns (can_book, message, existing_booking)
    """
    logger.info(
        f"Checking booking: user_id={user_id}, event_id={event_id}, slot={slot}, type={type(slot)}"
    )

    # Use SQLAlchemy ORM query instead of raw SQL
    query = (
        select(EventBooking)
        .where(
            and_(
                EventBooking.user_id == user_id,
                EventBooking.event_id == event_id,
                EventBooking.slot == str(slot),
                EventBooking.booking_date == booking_date,
            )
        )
        .order_by(desc(EventBooking.created_at))
    )

    result = await db.execute(query)
    existing_booking = result.scalar_one_or_none()

    if existing_booking:
        logger.warning(
            f"Booking already exists: booking_id={existing_booking.booking_id}"
        )
        return (
            False,
            f"You already have a booking for this event and slot with status: {existing_booking.booking_status}.",
            existing_booking,
        )

    return True, "No existing booking found", None


async def mark_booking_as_paid(db: AsyncSession, booking_id: str) -> None:
    # Fetch the booking
    result = await db.execute(
        select(EventBooking).where(EventBooking.booking_id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise ValueError(f"Booking with ID {booking_id} not found.")

    if booking.payment_status == "COMPLETED":
        # Already marked as paid, skip update
        return

    # Update booking status
    booking.booking_status = BookingStatus.APPROVED
    booking.payment_status = "COMPLETED"
    await db.commit()
    await db.refresh(booking)


async def create_booking_record(
    db: AsyncSession, booking_data: BookingCreateRequest
):
    logger.info(f"Creating booking record: {booking_data.model_dump()}")

    query = (
        insert(EventBooking)
        .values(
            booking_id=generate_digits_letters(6),
            user_id=booking_data.user_id,
            event_id=booking_data.event_id,
            num_seats=booking_data.num_seats,
            price_per_seat=booking_data.price_per_seat,
            total_price=booking_data.total_price,
            slot=str(booking_data.slot),
            booking_date=booking_data.booking_date
            or func.current_date(),  # Use date object or default
            booking_status=BookingStatus.PROCESSING,
        )
        .returning(EventBooking)
    )

    try:
        result = await db.execute(query)
        await db.commit()
        booking = result.scalars().first()

        if booking is None:
            logger.error(
                "Failed to create booking: No booking returned from database"
            )
            raise ValueError("Failed to create booking record")

        logger.info(f"Booking created: booking_id={booking.booking_id}")
        return booking
    except Exception as e:
        logger.error(f"Failed to create booking: {str(e)}")
        await db.rollback()
        raise


async def create_booking(db: AsyncSession, booking_data: BookingCreateRequest):
    # Log the slot value for debugging
    print(
        f"Received slot: {booking_data.slot}, type: {type(booking_data.slot)}"
    )

    can_book, message, existing_booking = await check_existing_booking(
        db,
        booking_data.user_id,
        booking_data.event_id,
        str(booking_data.slot),  # Ensure string
        booking_data.booking_date,
    )
    if not can_book:
        raise HTTPException(status_code=400, detail=message)

    # Verify other constraints including held seats
    can_book, message = await verify_booking_constraints(
        db,
        booking_data.event_id,
        booking_data.num_seats,
        str(booking_data.slot),
        str(booking_data.booking_date),
    )
    if not can_book:
        raise HTTPException(status_code=400, detail=message)

    # Create the booking record first
    booking = await create_booking_record(db, booking_data)

    # Hold seats immediately after creating the booking
    # We need to determine the slot_key from the slot time string
    slot_key = await _determine_slot_key_from_time(
        db,
        booking_data.event_id,
        str(booking_data.slot),
        str(booking_data.booking_date),
    )

    if slot_key:
        hold_success, hold_message = await hold_seats(
            db,
            booking_data.event_id,
            booking.booking_id,
            slot_key,
            str(booking_data.booking_date),
            booking_data.num_seats,
        )

        if not hold_success:
            logger.warning(
                f"Failed to hold seats for booking {booking.booking_id}: {hold_message}"
            )
            # Note: We don't fail the booking creation if seat holding fails
            # as this is a temporary hold mechanism
    else:
        logger.warning(
            f"Could not determine slot_key for booking {booking.booking_id}, "
            f"slot: {booking_data.slot}, date: {booking_data.booking_date}"
        )

    return booking


async def get_booking_by_id(
    db: AsyncSession, booking_id: str, load_relations: bool = False
) -> Optional[EventBooking]:
    """Get booking by ID with optional relations"""

    query = select(EventBooking).where(EventBooking.booking_id == booking_id)

    if load_relations:
        query = query.options(
            selectinload(EventBooking.user),
            selectinload(EventBooking.booked_event),
        )

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_booking_status(
    db: AsyncSession, booking_id: str, status_data: BookingStatusUpdateRequest
) -> Optional[EventBooking]:
    """Update booking status"""

    booking = await get_booking_by_id(db, booking_id)
    if not booking:
        return None

    # Update booking status directly (already a BookingStatus enum)
    booking.booking_status = status_data.booking_status

    await db.commit()
    await db.refresh(booking)

    return booking


async def get_user_bookings(
    db: AsyncSession,
    user_id: str,
    status_filter: Optional[BookingStatus] = None,
    page: int = 1,
    per_page: int = 10,
) -> Tuple[List[EventBooking], int]:
    """Get bookings for a specific user with pagination"""

    # Base query
    query = select(EventBooking).where(EventBooking.user_id == user_id)

    # Add status filter if provided
    if status_filter is not None:
        query = query.where(EventBooking.booking_status == status_filter)

    # Add relations
    query = query.options(selectinload(EventBooking.booked_event))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Add pagination and ordering
    query = query.order_by(desc(EventBooking.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    bookings = result.scalars().all()

    return list(bookings), total


async def get_event_bookings(
    db: AsyncSession,
    event_id: str,
    status_filter: Optional[BookingStatus] = None,
    page: int = 1,
    per_page: int = 10,
) -> Tuple[List[EventBooking], int]:
    """Get bookings for a specific event with pagination"""

    # Base query
    query = select(EventBooking).where(EventBooking.event_id == event_id)

    # Add status filter if provided
    if status_filter is not None:
        query = query.where(EventBooking.booking_status == status_filter)

    # Add relations
    query = query.options(selectinload(EventBooking.user))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Add pagination and ordering
    query = query.order_by(desc(EventBooking.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    bookings = result.scalars().all()

    return list(bookings), total


async def get_organizer_bookings(
    db: AsyncSession,
    organizer_id: str,
    status_filter: Optional[BookingStatus] = None,
    page: int = 1,
    per_page: int = 10,
) -> Tuple[List[EventBooking], int]:
    """Get all bookings for events organized by a specific organizer"""

    # Base query joining with events
    query = (
        select(EventBooking)
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(Event.organizer_id == organizer_id)
    )

    # Add status filter if provided
    if status_filter is not None:
        query = query.where(EventBooking.booking_status == status_filter)

    # Add relations
    query = query.options(
        selectinload(EventBooking.user), selectinload(EventBooking.booked_event)
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Add pagination and ordering
    query = query.order_by(desc(EventBooking.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    bookings = result.scalars().all()

    return list(bookings), total


async def get_booking_stats_for_user(db: AsyncSession, user_id: str) -> dict:
    """Get booking statistics for a user"""

    query = select(
        func.count(EventBooking.booking_id).label("total_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.APPROVED, 1))
        ).label("approved_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.PROCESSING, 1))
        ).label("pending_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.CANCELLED, 1))
        ).label("cancelled_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.FAILED, 1))
        ).label("failed_bookings"),
        func.coalesce(
            func.sum(
                case(
                    (
                        EventBooking.booking_status == BookingStatus.APPROVED,
                        EventBooking.total_price,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("total_revenue"),
        func.coalesce(
            func.sum(
                case(
                    (
                        EventBooking.booking_status == BookingStatus.APPROVED,
                        EventBooking.num_seats,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("total_seats_booked"),
    ).where(EventBooking.user_id == user_id)

    result = await db.execute(query)
    stats = result.first()

    if not stats:
        return {
            "total_bookings": 0,
            "approved_bookings": 0,
            "pending_bookings": 0,
            "cancelled_bookings": 0,
            "failed_bookings": 0,
            "total_revenue": 0.0,
            "total_seats_booked": 0,
        }

    return {
        "total_bookings": stats.total_bookings or 0,
        "approved_bookings": stats.approved_bookings or 0,
        "pending_bookings": stats.pending_bookings or 0,
        "cancelled_bookings": stats.cancelled_bookings or 0,
        "failed_bookings": stats.failed_bookings or 0,
        "total_revenue": float(stats.total_revenue or 0),
        "total_seats_booked": stats.total_seats_booked or 0,
    }


async def get_booking_stats_for_event(db: AsyncSession, event_id: str) -> dict:
    """Get booking statistics for an event"""

    query = select(
        func.count(EventBooking.booking_id).label("total_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.APPROVED, 1))
        ).label("approved_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.PROCESSING, 1))
        ).label("pending_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.CANCELLED, 1))
        ).label("cancelled_bookings"),
        func.count(
            case((EventBooking.booking_status == BookingStatus.FAILED, 1))
        ).label("failed_bookings"),
        func.coalesce(
            func.sum(
                case(
                    (
                        EventBooking.booking_status == BookingStatus.APPROVED,
                        EventBooking.total_price,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("total_revenue"),
        func.coalesce(
            func.sum(
                case(
                    (
                        EventBooking.booking_status == BookingStatus.APPROVED,
                        EventBooking.num_seats,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("total_seats_booked"),
    ).where(EventBooking.event_id == event_id)

    result = await db.execute(query)
    stats = result.first()

    if not stats:
        return {
            "total_bookings": 0,
            "approved_bookings": 0,
            "pending_bookings": 0,
            "cancelled_bookings": 0,
            "failed_bookings": 0,
            "total_revenue": 0.0,
            "total_seats_booked": 0,
        }

    return {
        "total_bookings": stats.total_bookings or 0,
        "approved_bookings": stats.approved_bookings or 0,
        "pending_bookings": stats.pending_bookings or 0,
        "cancelled_bookings": stats.cancelled_bookings or 0,
        "failed_bookings": stats.failed_bookings or 0,
        "total_revenue": float(stats.total_revenue or 0),
        "total_seats_booked": stats.total_seats_booked or 0,
    }


async def verify_booking_constraints(
    db: AsyncSession,
    event_id: str,
    num_seats: int,
    slot: str,
    booking_date: Optional[str] = None,
) -> Tuple[bool, str]:
    """Verify if booking can be made (check event capacity, availability, etc.)"""

    # Get event details
    event_query = select(Event).where(Event.event_id == event_id)
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()

    if not event:
        return False, "Event not found"

    if event.event_status == EventStatus.INACTIVE:
        return False, "Event is inactive"

    if event.event_status == EventStatus.PENDING:
        return False, "Event is pending for slots"

    # Check if event has ended
    if event.end_date and event.end_date < datetime.now(timezone.utc).date():
        return False, "Event has already ended"

    # Get event slot data to check capacity
    slot_query = select(EventSlot).where(EventSlot.slot_id == event.slot_id)
    slot_result = await db.execute(slot_query)
    event_slot = slot_result.scalar_one_or_none()

    if not event_slot:
        return False, "Event slot configuration not found"

    if event_slot.slot_status:
        return False, "Event slot is inactive"

    # Clean up expired holds first
    await cleanup_expired_holds(db, event_slot.id)

    # Get total approved bookings for this event and slot
    approved_bookings_query = select(
        func.coalesce(func.sum(EventBooking.num_seats), 0)
    ).where(
        and_(
            EventBooking.event_id == event_id,
            EventBooking.slot == slot,
            EventBooking.booking_status == BookingStatus.APPROVED,
        )
    )

    approved_result = await db.execute(approved_bookings_query)
    total_booked_seats = approved_result.scalar() or 0

    # Check slot capacity from JSONB data
    slot_data = event_slot.slot_data or {}
    slot_capacity = None
    matched_slot_key = None
    matched_date_key = None

    # Find the matching slot in JSONB data
    for date_key, date_slots in slot_data.items():
        for slot_key, slot_info in date_slots.items():
            start_time = slot_info.get("start_time", "")
            end_time = slot_info.get("end_time", "")

            # Create possible time format combinations for matching
            possible_formats = [
                f"{start_time} - {end_time}",
                f"{start_time}:00 - {end_time}:00",
                f"{start_time} AM - {end_time} PM",
                f"{start_time} PM - {end_time} PM",
                f"{start_time} AM - {end_time} AM",
            ]

            if slot in possible_formats or (
                start_time in slot and end_time in slot
            ):
                slot_capacity = slot_info.get("capacity", 0)
                matched_slot_key = slot_key
                matched_date_key = date_key
                break

        if slot_capacity is not None:
            break

    # If we found slot capacity, check availability including held seats
    if slot_capacity is not None and matched_slot_key and matched_date_key:
        # Get currently held seats for this slot and date
        held_seats_count = await get_held_seats_count(
            event_slot, matched_slot_key, matched_date_key
        )

        # Calculate total unavailable seats (booked + held)
        total_unavailable_seats = total_booked_seats + held_seats_count
        available_seats = slot_capacity - total_unavailable_seats

        if available_seats < num_seats:
            return (
                False,
                f"Not enough seats available. Only {available_seats} seats left for this slot "
                f"(Capacity: {slot_capacity}, Booked: {total_booked_seats}, Held: {held_seats_count})",
            )
    else:
        # Fallback: If no specific slot capacity found, allow booking but warn
        # This maintains backward compatibility
        pass

    return True, "Booking can be made"


def build_booking_with_event_response(
    booking: EventBooking,
) -> BookingWithEventResponse:
    """Build booking response with event details"""
    response_data = {
        "booking_id": booking.booking_id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "num_seats": booking.num_seats,
        "price_per_seat": booking.price_per_seat,
        "total_price": booking.total_price,
        "slot": booking.slot,
        "booking_date": booking.booking_date,
        "booking_status": booking.booking_status,
        "created_at": booking.created_at,
        "updated_at": booking.updated_at,
        # Payment details
        "payment_status": booking.payment_status,
        "paypal_order_id": booking.paypal_order_id,
    }

    # Add event details if available
    if hasattr(booking, "booked_event") and booking.booked_event:
        # Extract event address from extra_data
        event_address = _extract_event_address(booking.booked_event)

        response_data.update(
            {
                "event_title": booking.booked_event.event_title,
                "event_slug": booking.booked_event.event_slug,
                "event_location": booking.booked_event.location,
                "event_address": event_address,
                "event_start_date": booking.booked_event.start_date,
                "event_end_date": booking.booked_event.end_date,
                "event_card_image": get_media_url(
                    booking.booked_event.card_image
                ),
            }
        )

        # Extract slot time information from event slot data
        slot_time = _extract_slot_time(booking.booked_event, booking.slot)
        response_data["slot_time"] = slot_time

    return BookingWithEventResponse(**response_data)


def build_booking_with_user_response(
    booking: EventBooking,
) -> BookingWithUserResponse:
    """Build booking response with user details"""
    response_data = {
        "booking_id": booking.booking_id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "num_seats": booking.num_seats,
        "price_per_seat": booking.price_per_seat,
        "total_price": booking.total_price,
        "slot": booking.slot,
        "booking_date": booking.booking_date,
        "booking_status": booking.booking_status,
        "created_at": booking.created_at,
        "updated_at": booking.updated_at,
        # Payment details
        "payment_status": booking.payment_status,
        "paypal_order_id": booking.paypal_order_id,
    }

    # Add user details if available (handle encrypted fields)
    if hasattr(booking, "user") and booking.user:
        response_data.update(
            {
                "user_email": booking.user.email,  # This will use the property to decrypt
                "user_first_name": booking.user.first_name,
                "user_last_name": booking.user.last_name,
                "user_profile_picture": get_media_url(
                    booking.user.profile_picture
                ),
            }
        )

    return BookingWithUserResponse(**response_data)


def build_enhanced_booking_response(booking: EventBooking) -> BookingResponse:
    """Build enhanced booking response with both user and event details"""

    response_data = {
        "booking_id": booking.booking_id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "num_seats": booking.num_seats,
        "price_per_seat": booking.price_per_seat,
        "total_price": booking.total_price,
        "slot": booking.slot,
        "booking_date": booking.booking_date,
        "booking_status": booking.booking_status,
        "created_at": booking.created_at,
        "updated_at": booking.updated_at,
        # Payment details
        "payment_status": booking.payment_status,
        "paypal_order_id": booking.paypal_order_id,
    }

    # Add user details if available (handle encrypted fields)
    if hasattr(booking, "user") and booking.user:
        response_data.update(
            {
                "user_email": booking.user.email,  # This will use the property to decrypt
                "user_first_name": booking.user.first_name or "",
                "user_last_name": booking.user.last_name or "",
                "user_profile_picture": get_media_url(
                    booking.user.profile_picture
                ),
            }
        )

    # Add event details if available
    if hasattr(booking, "booked_event") and booking.booked_event:
        # Extract event address from extra_data
        event_address = _extract_event_address(booking.booked_event)

        response_data.update(
            {
                "event_title": booking.booked_event.event_title,
                "event_slug": booking.booked_event.event_slug,
                "event_location": booking.booked_event.location,
                "event_address": event_address,
                "event_start_date": booking.booked_event.start_date,
                "event_end_date": booking.booked_event.end_date,
                "event_card_image": get_media_url(
                    booking.booked_event.card_image
                ),
            }
        )

        # Extract slot time information from event slot data
        slot_time = _extract_slot_time(booking.booked_event, booking.slot)
        response_data["slot_time"] = slot_time

    return BookingResponse(**response_data)


def build_booking_details_response(
    booking: EventBooking,
) -> BookingDetailsResponse:
    """Build detailed booking response with nested user and event details"""

    # Validate that we have the required relationships loaded
    if not hasattr(booking, "user") or not booking.user:
        raise ValueError("Booking must have user relationship loaded")

    if not hasattr(booking, "booked_event") or not booking.booked_event:
        raise ValueError("Booking must have event relationship loaded")

    # Build user details
    user_details = BookingUserDetails(
        user_id=booking.user.user_id,
        email=booking.user.email,
        username=booking.user.username,
    )

    # Build event details
    event_address = _extract_event_address(booking.booked_event)
    event_details = BookingEventDetails(
        event_id=booking.booked_event.event_id,
        organizer_name=booking.booked_event.organizer.username,
        title=booking.booked_event.event_title,
        slug=booking.booked_event.event_slug,
        location=booking.booked_event.location,
        address=event_address,
        start_date=booking.booked_event.start_date,
        end_date=booking.booked_event.end_date,
        card_image=get_media_url(booking.booked_event.card_image),
    )

    # Extract slot time information
    slot_time = _extract_slot_time(booking.booked_event, booking.slot)

    # Build the main response
    return BookingDetailsResponse(
        booking_id=booking.booking_id,
        num_seats=booking.num_seats,
        price_per_seat=booking.price_per_seat,
        total_price=booking.total_price,
        slot=booking.slot,
        slot_time=slot_time,
        booking_date=booking.booking_date,
        booking_status=str(booking.booking_status),
        payment_status=booking.payment_status,
        paypal_order_id=booking.paypal_order_id,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
        user=user_details,
        event=event_details,
    )


def build_user_bookings_list_response(
    bookings: List[EventBooking], total: int, page: int, per_page: int
) -> UserBookingsListResponse:
    """Build user bookings list response with pagination"""

    # Build individual booking items
    booking_items = []
    for booking in bookings:
        # Extract slot time information
        slot_time = None
        if hasattr(booking, "booked_event") and booking.booked_event:
            slot_time = _extract_slot_time(booking.booked_event, booking.slot)

        # Get event title and card image
        event_title = ""
        event_card_image = None
        if hasattr(booking, "booked_event") and booking.booked_event:
            event_title = booking.booked_event.event_title or ""
            event_card_image = booking.booked_event.card_image

        booking_item = UserBookingItemResponse(
            booking_id=booking.booking_id,
            event_title=event_title,
            event_card_image=get_media_url(event_card_image),
            slot_time=slot_time,
            num_seats=booking.num_seats,
            booking_date=booking.booking_date,
            total_price=booking.total_price,
            booking_status=str(booking.booking_status),
        )
        booking_items.append(booking_item)

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page

    return UserBookingsListResponse(
        events=booking_items,
        page=page,
        per_page=per_page,
        total_items=total,
        total_pages=total_pages,
    )


async def get_organizer_bookings_with_events_and_slots(
    db: AsyncSession,
    organizer_id: str,
    event_id: Optional[str] = None,
    status_filter: Optional[BookingStatus] = None,
    page: int = 1,
    per_page: int = 10,
) -> OrganizerBookingsResponse:
    """
    Get organizer bookings organized by events and slots with detailed structure
    """

    # Base query for events by organizer
    events_query = select(Event).where(Event.organizer_id == organizer_id)

    # Add event_id filter if provided
    if event_id:
        events_query = events_query.where(Event.event_id == event_id)

    # Load relationships
    events_query = events_query.options(
        selectinload(Event.slots),
        selectinload(Event.bookings).selectinload(EventBooking.user),
    )

    # Add pagination to events
    events_query = events_query.offset((page - 1) * per_page).limit(per_page)

    # Execute events query
    events_result = await db.execute(events_query)
    events = events_result.scalars().all()

    # Count total events for pagination
    count_query = select(func.count(Event.event_id)).where(
        Event.organizer_id == organizer_id
    )
    if event_id:
        count_query = count_query.where(Event.event_id == event_id)

    total_result = await db.execute(count_query)
    total_events = total_result.scalar() or 0

    # Count active/inactive events
    active_count_query = select(func.count(Event.event_id)).where(
        and_(
            Event.organizer_id == organizer_id,
            Event.event_status == EventStatus.ACTIVE,
        )
    )
    inactive_count_query = select(func.count(Event.event_id)).where(
        and_(
            Event.organizer_id == organizer_id,
            Event.event_status == EventStatus.INACTIVE,
        )
    )

    active_result = await db.execute(active_count_query)
    inactive_result = await db.execute(inactive_count_query)

    active_count = active_result.scalar() or 0
    inactive_count = inactive_result.scalar() or 0

    # Build response structure
    events_with_slots = []

    for event in events:
        # Build event details
        event_details = OrganizerEventDetails(
            event_id=event.event_id,
            title=event.event_title,
            slug=event.event_slug,
            card_image=get_media_url(event.card_image),
            start_date=event.start_date,
            end_date=event.end_date,
            status=(
                "active"
                if event.event_status == EventStatus.ACTIVE
                else "inactive"
            ),
            slots_count=len(event.slots) if event.slots else 0,
        )

        # Build slots with bookings
        slots_details = []

        # Get unique slots from bookings and slot data
        slot_map = {}

        # First, collect all slots from event.slots (slot configuration)
        if event.slots:
            for event_slot in event.slots:
                if event_slot.slot_data:
                    for date_key, date_slots in event_slot.slot_data.items():
                        if isinstance(date_slots, dict):
                            for slot_key, slot_details in date_slots.items():
                                if slot_key not in slot_map:
                                    start_time = slot_details.get(
                                        "start_time", ""
                                    )
                                    end_time = slot_details.get("end_time", "")
                                    slot_time = (
                                        f"{start_time} - {end_time}"
                                        if start_time and end_time
                                        else slot_key
                                    )
                                    capacity = slot_details.get("capacity", 0)

                                    slot_map[slot_key] = {
                                        "slot_id": slot_key,
                                        "slot_time": slot_time,
                                        "total_capacity": capacity,
                                        "bookings": [],
                                    }

        # Then, add bookings to slots
        if event.bookings:
            for booking in event.bookings:
                # Apply status filter if provided
                if status_filter and booking.booking_status != status_filter:
                    continue

                slot_key = booking.slot

                # If slot not in map, create it with basic info
                if slot_key not in slot_map:
                    slot_map[slot_key] = {
                        "slot_id": slot_key,
                        "slot_time": slot_key,  # Use slot key as fallback
                        "total_capacity": 0,
                        "bookings": [],
                    }

                booking_details = OrganizerBookingDetails(
                    booking_id=booking.booking_id,
                    booking_date=booking.booking_date,
                    num_seats=booking.num_seats,
                    total_price=booking.total_price,
                    booking_status=str(booking.booking_status),
                    payment_status=booking.payment_status,
                    paypal_order_id=booking.paypal_order_id,
                    created_at=booking.created_at,
                    updated_at=booking.updated_at,
                    username=booking.user.username,
                )

                slot_map[slot_key]["bookings"].append(booking_details)

        # Convert slot_map to list and calculate statistics
        for slot_key, slot_info in slot_map.items():
            # Calculate booked seats (only approved bookings)
            booked_seats = sum(
                booking.num_seats
                for booking in slot_info["bookings"]
                if booking.booking_status == "approved"
            )

            total_capacity = slot_info["total_capacity"]
            remaining_seats = max(0, total_capacity - booked_seats)

            slot_details = OrganizerSlotDetails(
                slot_id=slot_info["slot_id"],
                slot_time=slot_info["slot_time"],
                total_capacity=total_capacity,
                booked_seats=booked_seats,
                remaining_seats=remaining_seats,
                user_bookings_count=len(slot_info["bookings"]),
                bookings=slot_info["bookings"],
            )

            slots_details.append(slot_details)

        # Sort slots by slot_id for consistent ordering
        slots_details.sort(key=lambda x: x.slot_id)

        event_with_slots = OrganizerEventWithSlots(
            event=event_details, slots=slots_details
        )

        events_with_slots.append(event_with_slots)

    # Build events count
    events_count = OrganizerEventsCount(
        total=active_count + inactive_count,
        active=active_count,
        inactive=inactive_count,
    )

    # Calculate pagination
    total_pages = (total_events + per_page - 1) // per_page

    return OrganizerBookingsResponse(
        events_count=events_count,
        events=events_with_slots,
        total_items=total_events,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


async def get_all_bookings_with_details(
    db: AsyncSession,
    status_filter: Optional[BookingStatus] = None,
    page: int = 1,
    per_page: int = 10,
) -> AllBookingsListResponse:
    """
    Get all bookings with complete details including user, event, and organizer information
    """

    # Base query for all bookings with relationships
    query = select(EventBooking).options(
        selectinload(EventBooking.user),
        selectinload(EventBooking.booked_event).selectinload(Event.organizer),
    )

    # Add status filter if provided
    if status_filter:
        query = query.where(EventBooking.booking_status == status_filter)

    # Count total bookings
    count_query = select(func.count(EventBooking.booking_id))
    if status_filter:
        count_query = count_query.where(
            EventBooking.booking_status == status_filter
        )

    total_result = await db.execute(count_query)
    total_bookings = total_result.scalar() or 0

    # Add pagination and ordering
    query = query.order_by(desc(EventBooking.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute query
    result = await db.execute(query)
    bookings = result.scalars().all()

    # Build response items
    booking_items = []

    for booking in bookings:
        # Build event details
        event_details = AllBookingsEventDetails(
            event_id=booking.booked_event.event_id,
            event_title=booking.booked_event.event_title,
            event_slug=booking.booked_event.event_slug,
            start_date=booking.booked_event.start_date,
            end_date=booking.booked_event.end_date,
            location=booking.booked_event.location,
            card_image=get_media_url(booking.booked_event.card_image),
        )

        # Build organizer details
        organizer = booking.booked_event.organizer
        organizer_name = organizer.username if organizer else ""

        # Build complete booking item
        booking_item = AllBookingsItemResponse(
            booking_id=booking.booking_id,
            num_seats=booking.num_seats,
            price_per_seat=booking.price_per_seat,
            total_price=booking.total_price,
            slot=booking.slot,
            booking_date=booking.booking_date,
            booking_status=str(booking.booking_status),
            payment_status=booking.payment_status,
            paypal_order_id=booking.paypal_order_id,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            username=booking.user.username,
            organizer_name=organizer_name,
            event=event_details,
        )

        booking_items.append(booking_item)

    # Calculate pagination
    total_pages = (total_bookings + per_page - 1) // per_page

    return AllBookingsListResponse(
        bookings=booking_items,
        total_items=total_bookings,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


async def get_simple_organizer_bookings(
    db: AsyncSession,
    organizer_id: str,
    event_id: Optional[str] = None,
    status_filter: Optional[BookingStatus] = None,
    page: int = 1,
    per_page: int = 10,
) -> SimpleOrganizerBookingsResponse:
    """
    Get organizer bookings in a simple flat structure for tabular display
    """

    # Base query for bookings with relationships
    query = (
        select(EventBooking)
        .options(
            selectinload(EventBooking.user),
            selectinload(EventBooking.booked_event).selectinload(Event.slots),
        )
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(Event.organizer_id == organizer_id)
    )

    # Add event_id filter if provided
    if event_id:
        query = query.where(Event.event_id == event_id)

    # Add status filter if provided
    if status_filter:
        query = query.where(EventBooking.booking_status == status_filter)

    # Count total bookings
    count_query = (
        select(func.count(EventBooking.booking_id))
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(Event.organizer_id == organizer_id)
    )

    if event_id:
        count_query = count_query.where(Event.event_id == event_id)
    if status_filter:
        count_query = count_query.where(
            EventBooking.booking_status == status_filter
        )

    total_result = await db.execute(count_query)
    total_bookings = total_result.scalar() or 0

    # Add pagination and ordering
    query = query.order_by(desc(EventBooking.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    # Execute query
    result = await db.execute(query)
    bookings = result.scalars().all()

    # Build simple response items
    booking_items = []

    for booking in bookings:
        # Get slot time from event slots
        slot_time = booking.slot  # Default to slot key

        if booking.booked_event.slots:
            for event_slot in booking.booked_event.slots:
                if event_slot.slot_data:
                    for date_key, date_slots in event_slot.slot_data.items():
                        if (
                            isinstance(date_slots, dict)
                            and booking.slot in date_slots
                        ):
                            slot_details = date_slots[booking.slot]
                            start_time = slot_details.get("start_time", "")
                            end_time = slot_details.get("end_time", "")
                            if start_time and end_time:
                                slot_time = f"{start_time} - {end_time}"
                            break

        booking_item = SimpleOrganizerBookingItem(
            booking_id=booking.booking_id,
            event_title=booking.booked_event.event_title,
            event_id=booking.booked_event.event_id,
            card_image=get_media_url(booking.booked_event.card_image),
            user_name=booking.user.username,
            user_email=booking.user.email,
            slot_time=slot_time,
            booking_date=booking.booking_date,
            num_seats=booking.num_seats,
            total_price=booking.total_price,
            booking_status=str(booking.booking_status),
            payment_status=booking.payment_status,
            created_at=booking.created_at,
        )

        booking_items.append(booking_item)

    # Calculate pagination
    total_pages = (total_bookings + per_page - 1) // per_page

    return SimpleOrganizerBookingsResponse(
        bookings=booking_items,
        total_items=total_bookings,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


async def get_organizer_events_with_stats(
    db: AsyncSession, organizer_id: str
) -> dict:
    # # Fetch organizer basic info
    # organizer_query = select(AdminUser).where(AdminUser.user_id == organizer_id)
    # organizer_result = await db.execute(organizer_query)
    # organizer = organizer_result.first()
    # if not organizer:
    #     return {"error": "Organizer not found"}

    # Query all events with aggregated booking stats in ONE go
    events_query = (
        select(
            Event.event_id,
            Event.event_title,
            Event.card_image,
            func.coalesce(func.sum(EventBooking.num_seats), 0).label(
                "total_tickets"
            ),
            func.coalesce(func.sum(EventBooking.total_price), 0.0).label(
                "total_revenue"
            ),
        )
        .join(
            EventBooking,
            and_(
                EventBooking.event_id == Event.event_id,
                EventBooking.booking_status == BookingStatus.APPROVED,
                EventBooking.payment_status == "COMPLETED",
            ),
            isouter=True,
        )
        .where(Event.organizer_id == organizer_id)
        .group_by(Event.event_id, Event.event_title, Event.card_image)
    )
    events_result = await db.execute(events_query)

    events = [
        {
            "event_id": row.event_id,
            "event_title": row.event_title,
            "card_image": row.card_image,
            "total_tickets": int(row.total_tickets or 0),
            "total_revenue": round(float(row.total_revenue or 0.0), 2),
        }
        for row in events_result.fetchall()
    ]

    return {
        "organizer_id": organizer_id,
        "organizer_name": "",
        "events": events,
    }
