from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.bookings import (
    BookingCreateRequest,
    BookingListResponse,
    BookingResponse,
    BookingStatsResponse,
    BookingStatusUpdateRequest,
    BookingWithEventListResponse,
    BookingWithUserListResponse,
)
from event_service.services.bookings import (
    build_booking_with_event_response,
    build_booking_with_user_response,
    build_enhanced_booking_response,
    check_existing_booking,
    create_booking,
    get_booking_by_id,
    get_booking_stats_for_event,
    get_booking_stats_for_user,
    get_event_bookings,
    get_organizer_bookings,
    get_user_bookings,
    mark_booking_as_paid,
    update_booking_status,
    verify_booking_constraints,
)
from event_service.utils.paypal_client import paypal_client
from shared.core.api_response import api_response
from shared.db.models.events import BookingStatus
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from paypalcheckoutsdk.orders import OrdersCaptureRequest , OrdersCreateRequest
from fastapi.responses import RedirectResponse


router = APIRouter()


def convert_status_filter(
    status_filter: Optional[Union[str, BookingStatus]],
) -> Optional[BookingStatus]:
    """Convert string status filter to BookingStatus enum"""
    if status_filter is None:
        return None

    if isinstance(status_filter, BookingStatus):
        return status_filter

    if isinstance(status_filter, str):
        status_map = {
            "failed": BookingStatus.FAILED,
            "processing": BookingStatus.PROCESSING,
            "approved": BookingStatus.APPROVED,
            "cancelled": BookingStatus.CANCELLED,
        }
        status_lower = status_filter.lower()
        if status_lower not in status_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid booking status. Must be one of: {', '.join(status_map.keys())}",
            )
        return status_map[status_lower]

    return status_filter


# @router.post(
#     "/", status_code=status.HTTP_201_CREATED, response_model=BookingResponse
# )
# @exception_handler
# async def create_event_booking(
#     booking_data: BookingCreateRequest,
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Create a new event booking

#     - **user_id**: ID of the user making the booking
#     - **event_id**: ID of the event to book
#     - **num_seats**: Number of seats to book (1-50)
#     - **price_per_seat**: Price per seat (rounded to 2 decimals)
#     - **total_price**: Total price for all seats (must match num_seats * price_per_seat)
#     - **slot**: Time slot for the booking
#     - **booking_date**: Date of booking in YYYY-MM-DD format (optional, defaults to today)
#     """

#     # Check for existing bookings with same details
#     can_book_duplicate, duplicate_message, existing_booking = (
#         await check_existing_booking(
#             db,
#             booking_data.user_id,
#             booking_data.event_id,
#             booking_data.num_seats,
#         )
#     )

#     if not can_book_duplicate:
#         return api_response(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             message=duplicate_message,
#             log_error=True,
#         )


#     # Verify booking constraints (event availability, capacity, etc.)
#     can_book, constraint_message = await verify_booking_constraints(
#         db, booking_data.event_id, booking_data.num_seats, booking_data.slot
#     )

#     if not can_book:
#         return api_response(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             message=constraint_message,
#             log_error=True,
#         )

#     # Create the booking
#     booking = await create_booking(db, booking_data)

#     # Load relations for enhanced response
#     booking_with_relations = await get_booking_by_id(
#         db, booking.booking_id, load_relations=True
#     )

#     if not booking_with_relations:
#         # This should not happen since we just created the booking, but handle it for type safety
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to retrieve created booking",
#         )

#     return api_response(
#         status_code=status.HTTP_201_CREATED,
#         message="Booking created successfully",
#         data=build_enhanced_booking_response(booking_with_relations),
#     )

# @router.post("/", status_code=status.HTTP_201_CREATED)
# @exception_handler
# async def create_event_booking(
#     booking_data: BookingCreateRequest,
#     db: AsyncSession = Depends(get_db),
# ):
#     # Validate input as usual
#     can_book_duplicate, duplicate_message, _ = await check_existing_booking(
#         db,
#         booking_data.user_id,
#         booking_data.event_id,
#         booking_data.num_seats,
#     )

#     if not can_book_duplicate:
#         return api_response(status.HTTP_400_BAD_REQUEST, message=duplicate_message)

#     can_book, constraint_message = await verify_booking_constraints(
#         db, booking_data.event_id, booking_data.num_seats, booking_data.slot
#     )

#     if not can_book:
#         return api_response(status.HTTP_400_BAD_REQUEST, message=constraint_message)

#     # ✅ Create PayPal Order
#     request = OrdersCreateRequest()
#     request.headers["prefer"] = "return=representation"
#     total_price = round(booking_data.total_price, 2)

#     request.request_body({
#         "intent": "CAPTURE",
#         "purchase_units": [{
#             "amount": {
#                 "currency_code": "USD",
#                 "value": str(total_price)
#             }
#         }],
#         "application_context": {
#             "brand_name": "YourEventPlatform",
#             "landing_page": "LOGIN",
#             "user_action": "PAY_NOW",
#             "return_url": f"http://localhost:8000/api/v1/bookings/confirm?event_id={booking_data.event_id}&user_id={booking_data.user_id}&slot={booking_data.slot}&seats={booking_data.num_seats}&price={booking_data.price_per_seat}&date={booking_data.booking_date}",
#             "cancel_url": "http://localhost:8000/api/v1/bookings/cancel"
#         }
#     })

#     try:
#         response = paypal_client.client.execute(request)
#         approval_url = next((link.href for link in response.result.links if link.rel == "approve"), None)
        
#         if not approval_url:
#             return api_response(status.HTTP_500_INTERNAL_SERVER_ERROR, message="Unable to generate PayPal URL")

#         return api_response(
#             status_code=status.HTTP_200_OK,
#             message="Redirect to PayPal for payment",
#             data={"approval_url": approval_url}
#         )
#     except Exception as e:
#         return api_response(status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

@router.post("/", status_code=status.HTTP_201_CREATED)
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
        str(booking_data.slot),  # Fix: Pass slot, not num_seats
    )

    if not can_book_duplicate:
        return api_response(status.HTTP_400_BAD_REQUEST, message=duplicate_message)

    # Step 2: Verify booking constraints
    can_book, constraint_message = await verify_booking_constraints(
        db, booking_data.event_id, booking_data.num_seats, str(booking_data.slot)
    )

    if not can_book:
        return api_response(status.HTTP_400_BAD_REQUEST, message=constraint_message)

    # Step 3: Create booking
    booking = await create_booking(db, booking_data)

    # Step 4: Generate PayPal Order
    request = OrdersCreateRequest()
    request.headers["prefer"] = "return=representation"

    request.request_body({
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "AUD",
                "value": str(round(booking_data.total_price, 2))
            }
        }],
        "application_context": {
            "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
            "brand_name": "YourEventPlatform",
            "landing_page": "LOGIN",
            "locale": "en-AU",
            "user_action": "PAY_NOW",
            "return_url": f"http://localhost:8000/api/v1/bookings/confirm?booking_id={booking.booking_id}",
            "cancel_url": f"http://localhost:8000/api/v1/bookings/cancel?booking_id={booking.booking_id}"
        }
    })

    try:
        response = paypal_client.client.execute(request)
        approval_url = next((link.href for link in response.result.links if link.rel == "approve"), None)

        if not approval_url:
            return api_response(status.HTTP_500_INTERNAL_SERVER_ERROR, message="Unable to generate PayPal URL")

        return api_response(
            status_code=status.HTTP_200_OK,
            message="Redirect to PayPal for payment",
            data={"approval_url": approval_url}
        )
    except Exception as e:
        return api_response(status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

@router.get("/confirm")
async def confirm_booking(
    token: str,
    booking_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Capture the payment
    request = OrdersCaptureRequest(token)
    try:
        response = paypal_client.client.execute(request)

        if response.result.status == "COMPLETED":
            await mark_booking_as_paid(db, booking_id)

            # ✅ Redirect to frontend success page
            return RedirectResponse(
                # url=f"https://your-frontend-domain.com/booking/success?booking_id={booking_id}",
                url=f"http://localhost:3000/Profile",
                status_code=302
            )
        else:
            # ❌ Redirect to frontend failure page
            return RedirectResponse(
                url="https://your-frontend-domain.com/booking/failure",
                status_code=302
            )

    except Exception as e:
        # ⚠️ Redirect to error page with optional message
        return RedirectResponse(
            url=f"https://your-frontend-domain.com/booking/error?message={str(e)}",
            status_code=302
        )


@router.get("/cancel")
async def cancel_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db)
):
    update_data = BookingStatusUpdateRequest(booking_status=BookingStatus.CANCELLED)
    booking = await update_booking_status(db, booking_id, update_data)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Booking cancelled by user",
        data={"booking_id": booking_id}
    )

@router.patch(
    "/status/{booking_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingResponse,
)
@exception_handler
async def update_booking_status_endpoint(
    booking_id: int,
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
    "/{booking_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingResponse,
)
@exception_handler
async def get_booking_details(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get booking details by ID

    - **booking_id**: ID of the booking to retrieve
    """

    booking = await get_booking_by_id(db, booking_id, load_relations=True)

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
        )

    return api_response(
        message="Booking retrieved successfully",
        data=build_enhanced_booking_response(booking),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/user/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingWithEventListResponse,
)
@exception_handler
async def get_user_bookings_endpoint(
    user_id: str,
    status_filter: Optional[str] = Query(
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

    # Convert string status to enum
    converted_status = convert_status_filter(status_filter)

    bookings, total = await get_user_bookings(
        db, user_id, converted_status, page, per_page
    )

    # Build response with event details
    booking_responses = [
        build_booking_with_event_response(booking) for booking in bookings
    ]

    total_pages = (total + per_page - 1) // per_page

    response_data = BookingWithEventListResponse(
        bookings=booking_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )

    return api_response(
        message=f"Retrieved {len(bookings)} bookings for user",
        data=response_data,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/event/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingWithUserListResponse,
)
@exception_handler
async def get_event_bookings_endpoint(
    event_id: str,
    status_filter: Optional[str] = Query(
        None,
        description="Filter by booking status (failed, processing, approved, cancelled)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bookings for a specific event (for organizers)

    - **event_id**: ID of the event
    - **status_filter**: Optional filter by booking status (failed, processing, approved, cancelled)
    - **page**: Page number for pagination
    - **per_page**: Number of items per page (max 100)
    """

    # Convert string status to enum
    converted_status = convert_status_filter(status_filter)

    bookings, total = await get_event_bookings(
        db, event_id, converted_status, page, per_page
    )

    # Build response with user details
    booking_responses = [
        build_booking_with_user_response(booking) for booking in bookings
    ]

    total_pages = (total + per_page - 1) // per_page

    response_data = BookingWithUserListResponse(
        bookings=booking_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )

    return api_response(
        message=f"Retrieved {len(bookings)} bookings for event",
        data=response_data,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/organizer/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingWithUserListResponse,
)
@exception_handler
async def get_organizer_bookings_endpoint(
    organizer_id: str,
    status_filter: Optional[str] = Query(
        None,
        description="Filter by booking status (failed, processing, approved, cancelled)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bookings for events organized by a specific organizer

    - **organizer_id**: ID of the organizer
    - **status_filter**: Optional filter by booking status (failed, processing, approved, cancelled)
    - **page**: Page number for pagination
    - **per_page**: Number of items per page (max 100)
    """

    # Convert string status to enum
    converted_status = convert_status_filter(status_filter)

    bookings, total = await get_organizer_bookings(
        db, organizer_id, converted_status, page, per_page
    )

    # Build response with user details
    booking_responses = [
        build_booking_with_user_response(booking) for booking in bookings
    ]

    total_pages = (total + per_page - 1) // per_page

    response_data = BookingWithUserListResponse(
        bookings=booking_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )

    return api_response(
        message=f"Retrieved {len(bookings)} bookings for organizer",
        data=response_data,
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/stats/user/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingStatsResponse,
)
@exception_handler
async def get_user_booking_stats(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get booking statistics for a specific user

    - **user_id**: ID of the user
    """

    stats = await get_booking_stats_for_user(db, user_id)

    return api_response(
        message="User booking statistics retrieved successfully",
        data=BookingStatsResponse(**stats),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/stats/event/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingStatsResponse,
)
@exception_handler
async def get_event_booking_stats(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get booking statistics for a specific event

    - **event_id**: ID of the event
    """

    stats = await get_booking_stats_for_event(db, event_id)

    return api_response(
        message="Event booking statistics retrieved successfully",
        data=BookingStatsResponse(**stats),
        status_code=status.HTTP_200_OK,
    )
