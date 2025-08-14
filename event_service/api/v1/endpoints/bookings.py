from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from paypalcheckoutsdk.orders import OrdersCaptureRequest
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.bookings import (
    AllBookingsListResponse,
    BookingCreateRequest,
    BookingDetailsResponse,
    BookingResponse,
    BookingStatusUpdateRequest,
    OrganizerBookingsResponse,
    OrganizerEventsStatsResponse,
    SimpleOrganizerBookingsResponse,
    UserBookingsListResponse,
)
from event_service.services.booking_helpers import (
    check_paypal_payment_status,
    create_paypal_order,
    release_event_slot_on_cancel,
    release_held,
    update_event_slot_after_payment,
    validate_booking,
    verify_and_hold_seats,
)
from event_service.services.bookings import (
    build_booking_details_response,
    build_enhanced_booking_response,
    build_user_bookings_list_response,
    create_booking_record,
    get_all_bookings_with_details,
    get_booking_by_id,
    get_organizer_bookings_with_events_and_slots,
    get_organizer_events_with_stats,
    get_simple_organizer_bookings,
    get_user_bookings,
    mark_booking_as_paid,
    update_booking_status,
)
from event_service.utils.paypal_client import paypal_client
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models import BookingStatus, EventBooking, EventStatus
from shared.db.sessions.database import get_db
from shared.utils.email_utils.admin_emails import send_booking_success_email
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Integrated in Application frontend",
)
@exception_handler
async def create_event_booking(
    booking_data: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    # Step 1: Validate booking
    can_book, message = await validate_booking(
        db,
        user_id=booking_data.user_id,
        event_id=booking_data.event_id,
        slot=str(booking_data.slot),
        booking_date=booking_data.booking_date,
        num_seats=booking_data.num_seats,
    )
    if not can_book:
        return api_response(status.HTTP_400_BAD_REQUEST, message=message)

    # Step 2: Verify availability and HOLD seats under a transaction
    try:
        # Lock, check, hold
        event, _ = await verify_and_hold_seats(
            db=db,
            event_id=booking_data.event_id,
            booking_date=booking_data.booking_date,
            slot_key=str(booking_data.slot),
            num_seats=booking_data.num_seats,
        )

        # Create booking record in PROCESSING (still inside the same transaction)
        # Ensure total_price & price_per_seat are sane (optionally enforce price from JSON)
        booking = await create_booking_record(db, booking_data)
        # Transaction committed here: held seats + booking created
    except ValueError as ve:
        # Expected business error (availability, validation...)
        await db.rollback()
        return api_response(status.HTTP_400_BAD_REQUEST, message=str(ve))
    except IntegrityError:
        await db.rollback()
        return api_response(
            status.HTTP_409_CONFLICT,
            message="Concurrent booking conflict. Please try again.",
        )
    except Exception as e:
        await db.rollback()
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Unexpected error: {str(e)}",
        )

    # Step 3: Create PayPal order
    try:
        approval_url = await create_paypal_order(
            booking_data.total_price, booking.booking_id
        )
        if not approval_url:
            # Release held seats & mark booking FAILED
            async with db.begin():
                await release_held(
                    db,
                    slot_id=event.slot_id,
                    booking_date=booking_data.booking_date,
                    slot_key=str(booking_data.slot),
                    seats=booking_data.num_seats,
                )
                # Update booking status to FAILED
                await db.execute(
                    update(EventBooking)
                    .where(EventBooking.booking_id == booking.booking_id)
                    .values(
                        booking_status=BookingStatus.FAILED,
                        updated_at=func.now(),
                    )
                )
            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Unable to generate PayPal approval URL",
            )

        return api_response(
            status_code=status.HTTP_200_OK,
            message="Redirect to PayPal for payment",
            data={
                "approval_url": approval_url,
                "booking_id": booking.booking_id,
            },
        )

    except Exception as e:
        # On PayPal errors, release held seats & mark booking FAILED
        async with db.begin():
            await release_held(
                db,
                slot_id=event.slot_id,
                booking_date=booking_data.booking_date,
                slot_key=str(booking_data.slot),
                seats=booking_data.num_seats,
            )
            await db.execute(
                update(EventBooking)
                .where(EventBooking.booking_id == booking.booking_id)
                .values(
                    booking_status=BookingStatus.FAILED, updated_at=func.now()
                )
            )
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"PayPal error: {str(e)}",
        )


@router.get(
    "/confirm", summary="Indirectly integrated with Application frontend"
)
@exception_handler
async def confirm_booking(
    token: str, booking_id: str, db: AsyncSession = Depends(get_db)
):
    # Capture the payment
    request = OrdersCaptureRequest(token)
    try:
        response = paypal_client.client.execute(request)

        # Check payment status using helper function
        payment_status = check_paypal_payment_status(response)

        # Fetch booking with relations
        booking = await get_booking_by_id(db, booking_id, load_relations=True)

        # 1. Validate booking existence & status
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")
        if booking.booking_status != BookingStatus.PROCESSING:
            raise HTTPException(
                status_code=400, detail="Booking is not in processing state."
            )
        if booking.payment_status == "COMPLETED":
            raise HTTPException(
                status_code=400, detail="Payment already completed."
            )

        # 2. Validate event status
        if (
            not booking.booked_event
            or booking.booked_event.event_status != EventStatus.ACTIVE
        ):
            raise HTTPException(
                status_code=400, detail="Event is not active or not found."
            )

        if payment_status == "COMPLETED":
            # 3. Update slot_data JSONB
            await update_event_slot_after_payment(
                db=db,
                slot_id=booking.booked_event.slot_id,
                booking_date=str(booking.booking_date),
                slot_key=booking.slot,
                num_seats=booking.num_seats,
            )

            # 4. Update booking status
            booking.booking_status = BookingStatus.APPROVED
            booking.payment_status = "COMPLETED"
            await db.commit()
            await db.refresh(booking)

            # 5. Send booking email
            try:
                event_date = booking.booked_event.start_date.strftime(
                    "%B %d, %Y"
                )
                if (
                    booking.booked_event.end_date
                    != booking.booked_event.start_date
                ):
                    event_date += f" - {booking.booked_event.end_date.strftime('%B %d, %Y')}"

                user_name = (
                    booking.user.username
                    or booking.user.first_name
                    or "Valued Customer"
                )
                if booking.user.last_name:
                    user_name += f" {booking.user.last_name}"

                event_category = (
                    booking.booked_event.category.category_name or "General"
                )
                event_location = (
                    booking.booked_event.location
                    or (booking.booked_event.extra_data or {}).get(
                        "address", ""
                    )
                    or ""
                )

                send_booking_success_email(
                    email=booking.user.email,
                    user_name=user_name,
                    booking_id=booking.booking_id,
                    event_title=booking.booked_event.event_title,
                    event_slug=booking.booked_event.event_slug,
                    event_date=event_date,
                    event_location=event_location.title(),
                    event_category=event_category,
                    time_slot=booking.slot.replace("_", " ").title(),
                    num_seats=booking.num_seats,
                    price_per_seat=float(booking.price_per_seat),
                    total_price=float(booking.total_price),
                    booking_date=booking.booking_date.strftime("%B %d, %Y"),
                )
            except Exception as email_error:
                print(
                    f"Failed to send booking confirmation email: {email_error}"
                )

            # Redirect to frontend success page
            return RedirectResponse(
                url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-success?booking_id={booking_id}",
                status_code=302,
            )
        else:
            # Redirect to frontend failure page
            return RedirectResponse(
                url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-failure",
                status_code=302,
            )

    except HTTPException:
        raise
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking/error?message={str(e)}",
            status_code=302,
        )


@router.get(
    "/cancel", summary="Indirectly integrated with Application frontend"
)
@exception_handler
async def cancel_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    # Fetch booking with relations
    booking = await get_booking_by_id(db, booking_id, load_relations=True)

    # 1. Validate booking existence & status
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.booking_status != BookingStatus.PROCESSING:
        raise HTTPException(
            status_code=400, detail="Booking is not in processing state."
        )
    if booking.payment_status == "COMPLETED":
        raise HTTPException(
            status_code=400, detail="Cannot cancel a completed payment."
        )

    # 2. Validate event status
    if (
        not booking.booked_event
        or booking.booked_event.event_status != EventStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=400, detail="Event is not active or not found."
        )

    # 3. Release held seats from slot_data
    await release_event_slot_on_cancel(
        db=db,
        slot_id=booking.booked_event.slot_id,
        booking_date=str(booking.booking_date),
        slot_key=booking.slot,
        num_seats=booking.num_seats,
    )

    # 4. Update booking status & payment status
    booking.booking_status = BookingStatus.CANCELLED
    booking.payment_status = "FAILED"

    await db.commit()
    await db.refresh(booking)

    # Redirect to frontend booking failure page
    return RedirectResponse(
        url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-failure?booking_id={booking_id}",
        status_code=302,
    )


@router.patch(
    "/status/{booking_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingResponse,
    summary="Integrated in Application frontend",
)
@exception_handler
async def update_booking_status_endpoint(
    booking_id: str,
    status_data: BookingStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update booking status

    - **booking_id**: ID of the booking to update
    - **booking_status**: New status (failed, processing, approved, cancelled)
    """

    booking = await update_booking_status(db, booking_id, status_data)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
        )

    # Load relations for enhanced response
    booking_with_relations = await get_booking_by_id(
        db, booking.booking_id, load_relations=True
    )

    if not booking_with_relations:
        # This should not happen since we just updated the booking, but handle it for type safety
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated booking",
        )

    return api_response(
        message="Booking status updated successfully",
        data=build_enhanced_booking_response(booking_with_relations),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    response_model=AllBookingsListResponse,
    summary="Integrated in Admin frontend",
)
@exception_handler
async def get_all_bookings_endpoint(
    status_filter: Optional[BookingStatus] = Query(
        None,
        description="Filter by booking status (failed, processing, approved, cancelled)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bookings with complete details including user, event, and organizer information

    - **status_filter**: Optional filter by booking status (failed, processing, approved, cancelled)
    - **page**: Page number for pagination
    - **per_page**: Number of items per page (max 100)

    Returns detailed information for each booking including:
    - Complete booking details (seats, price, status, etc.)
    - User information (name, email, profile picture)
    - Event information (title, dates, location, etc.)
    - Organizer information (name, email)
    """

    response_data = await get_all_bookings_with_details(
        db, status_filter, page, per_page
    )

    return api_response(
        message=f"Retrieved {len(response_data.bookings)} bookings with complete details",
        data=response_data,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/{booking_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingDetailsResponse,
    summary="Integrated in Organizer and Application frontend",
)
@exception_handler
async def get_booking_details(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get booking details by ID with nested user and event information

    - **booking_id**: ID of the booking to retrieve
    """

    booking = await get_booking_by_id(db, booking_id, load_relations=True)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
        )

    return api_response(
        message="Booking retrieved successfully",
        data=build_booking_details_response(booking),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/user/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserBookingsListResponse,
    summary="Integrated in Application frontend",
)
@exception_handler
async def get_user_bookings_endpoint(
    user_id: str,
    status_filter: Optional[BookingStatus] = Query(
        None,
        description="Filter by booking status (failed, processing, approved, cancelled)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bookings for a specific user

    - **user_id**: ID of the user
    - **status_filter**: Optional filter by booking status (failed, processing, approved, cancelled)
    - **page**: Page number for pagination
    - **per_page**: Number of items per page (max 100)
    """

    bookings, total = await get_user_bookings(
        db, user_id, status_filter, page, per_page
    )

    # Build response with pagination and simplified booking data
    response_data = build_user_bookings_list_response(
        bookings, total, page, per_page
    )

    return api_response(
        message="User bookings retrieved successfully",
        data=response_data,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/organizer/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=SimpleOrganizerBookingsResponse,
    summary="Integrated in Organizer frontend",
)
@exception_handler
async def get_organizer_bookings_endpoint(
    organizer_id: str,
    event_id: Optional[str] = Query(
        None, description="Optional filter by specific event ID"
    ),
    status_filter: Optional[BookingStatus] = Query(
        None,
        description="Filter by booking status (failed, processing, approved, cancelled)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bookings for events organized by a specific organizer in a simple tabular format

    - **organizer_id**: ID of the organizer
    - **event_id**: Optional filter by specific event ID
    - **status_filter**: Optional filter by booking status (failed, processing, approved, cancelled)
    - **page**: Page number for pagination
    - **per_page**: Number of items per page (max 100)

    Returns a simple flat list of bookings with essential details for tabular display:
    - Booking ID, Event Title, User Name/Email
    - Slot Time, Booking Date, Number of Seats
    - Total Price, Booking Status, Payment Status
    """

    response_data = await get_simple_organizer_bookings(
        db, organizer_id, event_id, status_filter, page, per_page
    )

    return api_response(
        message="Retrieved bookings for organizer",
        data=response_data,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/organizer/{organizer_id}/detailed",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerBookingsResponse,
    summary="Not integrated in any frontend",
)
@exception_handler
async def get_organizer_bookings_detailed_endpoint(
    organizer_id: str,
    event_id: Optional[str] = Query(
        None, description="Optional filter by specific event ID"
    ),
    status_filter: Optional[BookingStatus] = Query(
        None,
        description="Filter by booking status (failed, processing, approved, cancelled)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bookings for events organized by a specific organizer with detailed event and slot structure

    This endpoint provides the full nested structure with events, slots, and bookings.
    Use the main /organizer/{organizer_id} endpoint for simple tabular data.

    - **organizer_id**: ID of the organizer
    - **event_id**: Optional filter by specific event ID
    - **status_filter**: Optional filter by booking status (failed, processing, approved, cancelled)
    - **page**: Page number for pagination
    - **per_page**: Number of items per page (max 100)
    """

    response_data = await get_organizer_bookings_with_events_and_slots(
        db, organizer_id, event_id, status_filter, page, per_page
    )

    return api_response(
        message="Retrieved detailed bookings for organizer",
        data=response_data,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/organizer/revenue/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerEventsStatsResponse,
    summary="Not integrated in any frontend",
)
@exception_handler
async def get_organizer_revenue_endpoint(
    organizer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get total revenue for an organizer based on approved bookings with completed payments

    - **organizer_id**: ID of the organizer

    Returns:
    - Total revenue from approved bookings with completed payments
    - Total number of qualifying bookings
    - Currency (AUD)
    """

    revenue_data = await get_organizer_events_with_stats(db, organizer_id)

    return api_response(
        message="Organizer revenue retrieved successfully",
        data=revenue_data,
        status_code=status.HTTP_200_OK,
    )
