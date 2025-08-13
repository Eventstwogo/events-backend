from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from paypalcheckoutsdk.orders import OrdersCaptureRequest, OrdersCreateRequest
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
from event_service.services.bookings import (
    build_booking_details_response,
    build_enhanced_booking_response,
    build_user_bookings_list_response,
    check_existing_booking,
    create_booking,
    get_all_bookings_with_details,
    get_booking_by_id,
    get_organizer_bookings_with_events_and_slots,
    get_organizer_events_with_stats,
    get_simple_organizer_bookings,
    get_user_bookings,
    mark_booking_as_paid,
    update_booking_status,
    verify_booking_constraints,
)
from event_service.utils.paypal_client import paypal_client
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models.events import BookingStatus
from shared.db.sessions.database import get_db

# from shared.utils.email_utils.admin_emails import send_booking_success_email
from shared.utils.email_utils.admin_emails import send_booking_success_email
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


def extract_approval_url_from_paypal_response(response: Any) -> Optional[str]:
    """
    Safely extract the approval URL from PayPal response.

    Args:
        response: PayPal SDK response object

    Returns:
        Optional[str]: The approval URL if found, None otherwise
    """
    try:
        if not response or not hasattr(response, "result"):
            return None

        if not hasattr(response.result, "links") or not response.result.links:
            return None

        for link in response.result.links:
            if (
                hasattr(link, "rel")
                and hasattr(link, "href")
                and link.rel == "approve"
            ):
                return link.href

        return None
    except Exception:
        return None


def check_paypal_payment_status(response: Any) -> Optional[str]:
    """
    Safely extract the payment status from PayPal response.

    Args:
        response: PayPal SDK response object

    Returns:
        Optional[str]: The payment status if found, None otherwise
    """
    try:
        if not response or not hasattr(response, "result"):
            return None

        if hasattr(response.result, "status"):
            return response.result.status

        return None
    except Exception:
        return None


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
    # Step 1: Check for duplicate booking
    can_book_duplicate, duplicate_message, _ = await check_existing_booking(
        db,
        booking_data.user_id,
        booking_data.event_id,
        str(booking_data.slot),
        booking_data.booking_date,
    )

    if not can_book_duplicate:
        return api_response(
            status.HTTP_400_BAD_REQUEST, message=duplicate_message
        )

    # Step 2: Verify booking constraints
    can_book, constraint_message = await verify_booking_constraints(
        db,
        booking_data.event_id,
        booking_data.num_seats,
        str(booking_data.slot),
    )

    if not can_book:
        return api_response(
            status.HTTP_400_BAD_REQUEST, message=constraint_message
        )

    # Step 3: Create booking
    booking = await create_booking(db, booking_data)

    # Step 4: Generate PayPal Order
    request = OrdersCreateRequest()
    request.headers["prefer"] = "return=representation"

    request.request_body(
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "AUD",
                        "value": str(round(booking_data.total_price, 2)),
                    }
                }
            ],
            "application_context": {
                "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                "brand_name": "Events2Go",
                "landing_page": "LOGIN",
                "locale": "en-AU",
                "user_action": "PAY_NOW",
                # "return_url": f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-success?booking_id={booking.booking_id}",
                # "cancel_url": f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-failure?booking_id={booking.booking_id}",
                "return_url": f"{settings.API_BACKEND_URL}/api/v1/bookings/confirm?booking_id={booking.booking_id}",
                "cancel_url": f"{settings.API_BACKEND_URL}/api/v1/bookings/cancel?booking_id={booking.booking_id}",
            },
        }
    )

    try:
        response = paypal_client.client.execute(request)

        # Extract approval URL using helper function
        approval_url = extract_approval_url_from_paypal_response(response)

        if not approval_url:
            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Unable to generate PayPal approval URL",
            )

        return api_response(
            status_code=status.HTTP_200_OK,
            message="Redirect to PayPal for payment",
            data={"approval_url": approval_url},
        )
    except Exception as e:
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

        if payment_status == "COMPLETED":
            await mark_booking_as_paid(db, booking_id)

            # Get booking details with relations for email
            booking = await get_booking_by_id(
                db, booking_id, load_relations=True
            )

            if booking and booking.user and booking.booked_event:
                # Send booking success email
                try:
                    # Format the event date
                    event_date = booking.booked_event.start_date.strftime(
                        "%B %d, %Y"
                    )
                    if (
                        booking.booked_event.end_date
                        != booking.booked_event.start_date
                    ):
                        event_date += f" - {booking.booked_event.end_date.strftime('%B %d, %Y')}"

                    # Get user name using the property (automatically decrypts)
                    user_name = (
                        booking.user.username
                        or booking.user.first_name
                        or "Valued Customer"
                    )
                    if booking.user.last_name:
                        user_name += f" {booking.user.last_name}"

                    # Get event category name (you might need to adjust this based on your category model)
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

                    # Send the email
                    send_booking_success_email(
                        email=booking.user.email,  # Using the property that automatically decrypts
                        user_name=user_name,
                        booking_id=booking.booking_id,
                        event_title=booking.booked_event.event_title,
                        event_date=event_date,
                        event_location=event_location,
                        event_category=event_category,
                        time_slot=booking.slot.replace("_", " ").title(),
                        num_seats=booking.num_seats,
                        price_per_seat=float(booking.price_per_seat),
                        total_price=float(booking.total_price),
                        booking_date=booking.booking_date.strftime("%B %d, %Y"),
                    )
                except Exception as email_error:
                    # Log the error but don't fail the booking confirmation
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

    except Exception as e:
        # Redirect to error page with optional message
        return RedirectResponse(
            url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking/error?message={str(e)}",
            status_code=302,
        )


@router.get(
    "/cancel", summary="Indirectly integrated with Application frontend"
)
@exception_handler
async def cancel_booking(booking_id: str, db: AsyncSession = Depends(get_db)):
    update_data = BookingStatusUpdateRequest(
        booking_status=BookingStatus.CANCELLED
    )
    booking = await update_booking_status(db, booking_id, update_data)

    # return api_response(
    #     status_code=status.HTTP_200_OK,
    #     message="Booking cancelled by user",
    #     data={"booking_id": booking_id},
    # )

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


# @router.get(
#     "/event/{event_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=BookingWithUserListResponse,
# )
# @exception_handler
# async def get_event_bookings_endpoint(
#     event_id: str,
#     status_filter: Optional[BookingStatus] = Query(
#         None,
#         description="Filter by booking status (failed, processing, approved, cancelled)",
#     ),
#     page: int = Query(1, ge=1, description="Page number"),
#     per_page: int = Query(10, ge=1, le=100, description="Items per page"),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Get all bookings for a specific event (for organizers)

#     - **event_id**: ID of the event
#     - **status_filter**: Optional filter by booking status (failed, processing, approved, cancelled)
#     - **page**: Page number for pagination
#     - **per_page**: Number of items per page (max 100)
#     """

#     bookings, total = await get_event_bookings(
#         db, event_id, status_filter, page, per_page
#     )

#     # Build response with user details
#     booking_responses = [
#         build_booking_with_user_response(booking) for booking in bookings
#     ]

#     total_pages = (total + per_page - 1) // per_page

#     response_data = BookingWithUserListResponse(
#         bookings=booking_responses,
#         total=total,
#         page=page,
#         per_page=per_page,
#         total_pages=total_pages,
#     )

#     return api_response(
#         message=f"Retrieved {len(bookings)} bookings for event",
#         data=response_data,
#         status_code=status.HTTP_200_OK,
#     )


# @router.get(
#     "/stats/user/{user_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=BookingStatsResponse,
# )
# @exception_handler
# async def get_user_booking_stats(
#     user_id: str,
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Get booking statistics for a specific user

#     - **user_id**: ID of the user
#     """

#     stats = await get_booking_stats_for_user(db, user_id)

#     return api_response(
#         message="User booking statistics retrieved successfully",
#         data=BookingStatsResponse(**stats),
#         status_code=status.HTTP_200_OK,
#     )


# @router.get(
#     "/stats/event/{event_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=BookingStatsResponse,
# )
# @exception_handler
# async def get_event_booking_stats(
#     event_id: str,
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Get booking statistics for a specific event

#     - **event_id**: ID of the event
#     """

#     stats = await get_booking_stats_for_event(db, event_id)

#     return api_response(
#         message="Event booking statistics retrieved successfully",
#         data=BookingStatsResponse(**stats),
#         status_code=status.HTTP_200_OK,
#     )
