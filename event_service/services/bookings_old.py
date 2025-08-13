from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from event_service.schemas.bookings import (
    BookingCreateRequest,
    BookingResponse,
    BookingStatusUpdateRequest,
    BookingWithEventResponse,
    BookingWithUserResponse,
)
from shared.db.models import BookingStatus, Event, EventBooking, EventStatus


async def check_existing_booking(
    db: AsyncSession, user_id: str, event_id: str, num_seats: int
) -> Tuple[bool, str, Optional[EventBooking]]:
    """
    Check if user has existing booking for the same event with same number of seats.
    Returns (can_book, message, existing_booking)
    """

    # Check for existing bookings with same user_id, event_id, and num_seats
    existing_booking_query = (
        select(EventBooking)
        .where(
            and_(
                EventBooking.user_id == user_id,
                EventBooking.event_id == event_id,
                EventBooking.num_seats == num_seats,
            )
        )
        .order_by(desc(EventBooking.created_at))
    )

    result = await db.execute(existing_booking_query)
    existing_booking = result.scalar_one_or_none()

    if not existing_booking:
        return True, "No existing booking found", None

    # Check the status of the existing booking
    if existing_booking.booking_status == BookingStatus.APPROVED:
        # User can book more tickets for the same event
        return (
            True,
            "Previous booking approved, can book more tickets",
            existing_booking,
        )

    elif existing_booking.booking_status == BookingStatus.PROCESSING:
        return (
            False,
            "You have already booked this event and the booking status is under processing. Please wait for approval.",
            existing_booking,
        )

    elif existing_booking.booking_status == BookingStatus.FAILED:
        # Allow new booking for failed bookings
        return (
            True,
            "Previous booking failed, can create new booking",
            existing_booking,
        )

    elif existing_booking.booking_status == BookingStatus.CANCELLED:
        # Allow new booking for cancelled bookings
        return (
            True,
            "Previous booking cancelled, can create new booking",
            existing_booking,
        )

    else:
        # Fallback for any other status
        return (
            False,
            f"You have an existing booking with status: {existing_booking.booking_status}",
            existing_booking,
        )


async def create_booking(
    db: AsyncSession, booking_data: BookingCreateRequest
) -> EventBooking:
    """Create a new event booking"""

    # Parse booking_date if provided, otherwise use current date
    if booking_data.booking_date:
        parsed_booking_date = datetime.strptime(
            booking_data.booking_date, "%Y-%m-%d"
        ).date()
    else:
        parsed_booking_date = datetime.now(timezone.utc).date()

    # Round prices to 2 decimal places (already done in validation, but ensure consistency)
    price_per_seat = round(booking_data.price_per_seat, 2)
    total_price = round(booking_data.total_price, 2)

    # Create booking instance
    booking = EventBooking(
        user_id=booking_data.user_id,
        event_id=booking_data.event_id,
        num_seats=booking_data.num_seats,
        price_per_seat=price_per_seat,
        total_price=total_price,
        slot=booking_data.slot,
        booking_date=parsed_booking_date,
        booking_status=BookingStatus.PROCESSING,  # Always start with PROCESSING status
    )

    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return booking


async def get_booking_by_id(
    db: AsyncSession, booking_id: int, load_relations: bool = False
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
    db: AsyncSession, booking_id: int, status_data: BookingStatusUpdateRequest
) -> Optional[EventBooking]:
    """Update booking status"""

    booking = await get_booking_by_id(db, booking_id)
    if not booking:
        return None

    # Convert string status to BookingStatus enum
    booking.booking_status = status_data.get_booking_status_enum()

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
    db: AsyncSession, event_id: str, num_seats: int, slot: str
) -> Tuple[bool, str]:
    """Verify if booking can be made (check event capacity, availability, etc.)"""

    # Get event details
    event_query = select(Event).where(Event.event_id == event_id)
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()

    if not event:
        return False, "Event not found"

    if event.event_status == EventStatus.ACTIVE:
        return False, "Event is inactive"

    # Check if event has ended
    if event.end_date and event.end_date < datetime.now(timezone.utc).date():
        return False, "Event has already ended"

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

    # Check if there are enough seats available
    # Note: You might want to add a max_capacity field to Event model
    # For now, we'll assume a default capacity or skip this check
    # if event.max_capacity and (total_booked_seats + num_seats) > event.max_capacity:
    #     return False, f"Not enough seats available. Only {event.max_capacity - total_booked_seats} seats left"

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
    }

    # Add event details if available
    if hasattr(booking, "booked_event") and booking.booked_event:
        response_data.update(
            {
                "event_title": booking.booked_event.event_title,
                "event_slug": booking.booked_event.event_slug,
                "event_location": booking.booked_event.location,
                "event_start_date": booking.booked_event.start_date,
                "event_end_date": booking.booked_event.end_date,
            }
        )

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
    }

    # Add user details if available (handle encrypted fields)
    if hasattr(booking, "user") and booking.user:
        response_data.update(
            {
                "user_email": booking.user.email,  # This will use the property to decrypt
                "user_first_name": booking.user.first_name,
                "user_last_name": booking.user.last_name,
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
    }

    # Add user details if available (handle encrypted fields)
    if hasattr(booking, "user") and booking.user:
        response_data.update(
            {
                "user_email": booking.user.email,  # This will use the property to decrypt
                "user_first_name": booking.user.first_name or "",
                "user_last_name": booking.user.last_name or "",
            }
        )

    # Add event details if available
    if hasattr(booking, "booked_event") and booking.booked_event:
        response_data.update(
            {
                "event_title": booking.booked_event.event_title,
                "event_slug": booking.booked_event.event_slug,
                "event_location": booking.booked_event.location,
                "event_start_date": booking.booked_event.start_date,
                "event_end_date": booking.booked_event.end_date,
            }
        )

    return BookingResponse(**response_data)
