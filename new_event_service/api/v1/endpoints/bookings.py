from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Query
from fastapi.responses import JSONResponse, RedirectResponse
from paypalcheckoutsdk.orders import OrdersCaptureRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_event_service.schemas.bookings import (
    BookingCreateRequest,
    BookingDetailsResponse,
    SeatCategoryItem,
)
from new_event_service.services.booking_helpers import (
    check_paypal_payment_status,
    create_paypal_order,
    extract_capture_id,
)
from new_event_service.services.events import check_event_exists
from new_event_service.services.response_builder import event_not_found_response
from new_event_service.utils.paypal_client import paypal_client
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.db.models import (
    EventStatus,
    NewEvent,
    NewEventBooking,
    NewEventSeatCategory,
    NewEventSlot,
)
from shared.db.models.new_events import (
    BookingStatus,
    NewEventBookingOrder,
    PaymentStatus,
)
from shared.db.sessions.database import get_db
from shared.utils.email_utils.admin_emails import send_booking_success_email
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url
from shared.utils.id_generators import generate_digits_letters

logger = get_logger(__name__)


def _extract_event_address(event: NewEvent) -> Optional[str]:
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


router = APIRouter()


@router.post(
    "/book",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new booking order for an event slot",
)
@exception_handler
async def create_event_booking_order(
    booking_req: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a booking order with one or more seat category line items.
    - Event must exist and be ACTIVE.
    - Slot must exist and be ACTIVE on the given date.
    - Seat categories must belong to that slot and have enough available seats.
    - Prevents duplicate/overlapping bookings for the same user (PROCESSING/APPROVED).
    - Places seats in HELD state until payment confirmation.
    - Integrates with PayPal to create an order and return approval URL.
    """

    # 1. Validate event
    event = await check_event_exists(db, booking_req.event_ref_id)
    if not event:
        return event_not_found_response()

    if event.event_status != EventStatus.ACTIVE:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Event '{booking_req.event_ref_id}' is not active",
            data={},
        )

    # 2. Validate event_date
    if booking_req.event_date not in event.event_dates:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid event date {booking_req.event_date} for event {booking_req.event_ref_id}",
            data={},
        )

    # 3. Validate slot
    query_slot = select(NewEventSlot).where(
        NewEventSlot.slot_id == booking_req.slot_ref_id,
        NewEventSlot.event_ref_id == booking_req.event_ref_id,
        NewEventSlot.slot_date == booking_req.event_date,
    )
    slot = (await db.execute(query_slot)).scalar_one_or_none()
    if not slot:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Slot not found for this event on the given date",
            data={},
        )

    if slot.slot_status:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Slot is not active",
            data={},
        )

    # 4. Validate seat categories
    seat_category_ids = [
        sc.seat_category_ref_id for sc in booking_req.seatCategories
    ]
    query_seats = select(NewEventSeatCategory).where(
        NewEventSeatCategory.slot_ref_id == slot.slot_id,
        NewEventSeatCategory.seat_category_id.in_(seat_category_ids),
    )
    db_seat_categories = {
        s.seat_category_id: s
        for s in (await db.execute(query_seats)).scalars().all()
    }

    if len(db_seat_categories) != len(seat_category_ids):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Some seat categories are invalid for this slot",
            data={},
        )

    # 5. Build line items with duplicate-check logic
    line_items: list[NewEventBooking] = []
    total_amount = 0

    for seat_req in booking_req.seatCategories:
        db_seat = db_seat_categories[seat_req.seat_category_ref_id]

        # 5.1 Duplicate booking check (PROCESSING or APPROVED)
        existing_order_query = (
            select(NewEventBookingOrder)
            .join(NewEventBookingOrder.line_items)
            .where(
                NewEventBookingOrder.user_ref_id == booking_req.user_ref_id,
                NewEventBookingOrder.event_ref_id == booking_req.event_ref_id,
                NewEventBookingOrder.slot_ref_id == booking_req.slot_ref_id,
                NewEventBookingOrder.booking_status.in_(
                    [BookingStatus.PROCESSING, BookingStatus.APPROVED]
                ),
                NewEventBooking.seat_category_ref_id
                == seat_req.seat_category_ref_id,
            )
        )
        existing_order = (
            await db.execute(existing_order_query)
        ).scalar_one_or_none()
        if existing_order:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="You already have a pending/approved booking for this seat category",
                data={
                    "order_id": existing_order.order_id,
                    "status": existing_order.booking_status.value,
                },
            )

        # 5.2 Availability check
        available = db_seat.total_tickets - (db_seat.booked + db_seat.held)
        if seat_req.num_seats > available:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Not enough seats available in category {db_seat.category_label}",
                data={"available": available},
            )

        # 5.3 Price validation (anti-fraud)
        if float(seat_req.price_per_seat) != float(db_seat.price):
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Price mismatch for category {db_seat.category_label}",
                data={},
            )

        # 5.4 Build line item
        total_price = seat_req.num_seats * seat_req.price_per_seat
        total_amount += total_price

        line_item = NewEventBooking(
            booking_id=generate_digits_letters(12),
            seat_category_ref_id=seat_req.seat_category_ref_id,
            num_seats=seat_req.num_seats,
            price_per_seat=seat_req.price_per_seat,
            total_price=total_price,
        )
        line_items.append(line_item)

        # Hold seats
        db_seat.held += seat_req.num_seats

    # 6. Create booking order
    order = NewEventBookingOrder(
        order_id=generate_digits_letters(12),
        user_ref_id=booking_req.user_ref_id,
        event_ref_id=booking_req.event_ref_id,
        slot_ref_id=booking_req.slot_ref_id,
        total_amount=total_amount,
        booking_status=BookingStatus.PROCESSING,
        payment_status=PaymentStatus.PENDING,
        line_items=line_items,
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)

    # 7. Create PayPal order
    try:
        approval_url = await create_paypal_order(
            order.total_amount, order.order_id
        )
        if not approval_url:
            # Rollback: release held seats & mark FAILED
            for li in line_items:
                db_seat_categories[li.seat_category_ref_id].held -= li.num_seats
            order.booking_status = BookingStatus.FAILED
            order.payment_status = PaymentStatus.FAILED
            await db.commit()

            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Unable to generate PayPal approval URL",
            )

        return api_response(
            status_code=status.HTTP_200_OK,
            message="Redirect to PayPal for payment",
            data={
                "approval_url": approval_url,
                "order_id": order.order_id,
                "total_amount": order.total_amount,
                "status": order.booking_status.value,
            },
        )

    except Exception as e:
        # Rollback: release held seats & mark FAILED
        for li in line_items:
            db_seat_categories[li.seat_category_ref_id].held -= li.num_seats
        order.booking_status = BookingStatus.FAILED
        order.payment_status = PaymentStatus.FAILED
        await db.commit()

        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"PayPal error: {str(e)}",
        )


@router.get(
    "/confirm",
    summary="Confirm booking after PayPal payment (frontend redirect)",
)
@exception_handler
async def confirm_booking(
    token: Annotated[str, Query(..., description="PayPal order token")],
    order_id: Annotated[str, Query(..., description="Booking order ID")],
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm booking after PayPal redirect.
    - Captures PayPal payment.
    - Updates booking order & line items.
    - Sends success email.
    - Redirects to frontend with status.
    """
    # 1. Fetch order
    order: NewEventBookingOrder | None = (
        await db.execute(
            select(NewEventBookingOrder).where(
                NewEventBookingOrder.order_id == order_id
            )
        )
    ).scalar_one_or_none()

    if not order:
        return RedirectResponse(
            url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking/error?message=Order not found",
            status_code=302,
        )

    if order.booking_status not in [BookingStatus.PROCESSING]:
        return RedirectResponse(
            url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking/error?message=Invalid order state",
            status_code=302,
        )

    # 2. Capture PayPal payment
    try:
        request = OrdersCaptureRequest(token)
        response = paypal_client.client.execute(request)
        payment_status = check_paypal_payment_status(response)

        if payment_status == "COMPLETED":
            # 3. Success: update booking order
            order.booking_status = BookingStatus.APPROVED
            order.payment_status = PaymentStatus.COMPLETED
            order.payment_reference = extract_capture_id(response)

            # 4. Update held → booked for all line items
            for li in order.line_items:
                seat_cat: NewEventSeatCategory = li.new_seat_category
                seat_cat.held -= li.num_seats
                seat_cat.booked += li.num_seats

            await db.commit()

            # 5. Send confirmation email
            try:
                user_name = (
                    order.new_user.username
                    or order.new_user.first_name
                    or "Valued Customer"
                )
                if order.new_user.last_name:
                    user_name += f" {order.new_user.last_name}"

                # Build seat categories list
                seat_categories = [
                    {
                        "label": li.new_seat_category.category_label,
                        "num_seats": li.num_seats,
                        "price_per_seat": float(li.price_per_seat),
                        "total_price": float(li.total_price),
                    }
                    for li in order.line_items
                ]

                # Send success email with full details
                send_booking_success_email(
                    email=order.new_user.email,
                    user_name=user_name,
                    order_id=order.order_id,
                    event_title=order.new_booked_event.event_title,
                    event_slug=order.new_booked_event.event_slug,
                    event_date=order.new_slot.slot_date.strftime("%B %d, %Y"),
                    event_time=(
                        order.new_slot.start_time
                        if order.new_slot.start_time
                        else "TBA"
                    ),
                    event_duration=(
                        f"{order.new_slot.duration_minutes} mins"
                        if order.new_slot.duration_minutes
                        else "N/A"
                    ),
                    event_location=order.new_booked_event.location or "",
                    event_category=order.new_booked_event.new_category.category_name,
                    booking_date=order.created_at.strftime("%B %d, %Y"),
                    total_amount=float(order.total_amount),
                    seat_categories=seat_categories,
                )
            except Exception as email_error:
                logger.warning(
                    "Failed to send booking confirmation email for order %s: %s",
                    order.order_id,
                    str(email_error),
                )

            # Redirect to success page
            return RedirectResponse(
                url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-success?order_id={order.order_id}",
                status_code=302,
            )

        else:
            # Payment not completed
            order.booking_status = BookingStatus.FAILED
            order.payment_status = PaymentStatus.FAILED

            # Release HELD seats
            for li in order.line_items:
                seat_cat: NewEventSeatCategory = li.new_seat_category
                seat_cat.held -= li.num_seats

            await db.commit()

            return RedirectResponse(
                url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-failure",
                status_code=302,
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error capturing PayPal payment: {str(e)}")
        logger.error(f"Error capturing PayPal payment: {str(e)}")
        # PayPal capture error → rollback
        order.booking_status = BookingStatus.FAILED
        order.payment_status = PaymentStatus.FAILED
        for li in order.line_items:
            li.new_seat_category.held -= li.num_seats
        await db.commit()

        return RedirectResponse(
            url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking/error?message={str(e)}",
            status_code=302,
        )


@router.get(
    "/cancel",
    summary="Cancel booking after PayPal user cancellation (frontend redirect)",
)
@exception_handler
async def cancel_booking(
    order_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a booking when the user cancels PayPal payment.
    - Frees held seats.
    - Marks order as CANCELLED.
    - Redirects to frontend failure page.
    """

    # 1. Fetch order
    order: NewEventBookingOrder | None = (
        await db.execute(
            select(NewEventBookingOrder).where(
                NewEventBookingOrder.order_id == order_id
            )
        )
    ).scalar_one_or_none()

    if not order:
        return RedirectResponse(
            url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking/error?message=Order not found",
            status_code=302,
        )

    # 2. Only cancel if still PROCESSING
    if order.booking_status == BookingStatus.PROCESSING:
        order.booking_status = BookingStatus.CANCELLED
        order.payment_status = PaymentStatus.CANCELLED

        # Release HELD seats
        for li in order.line_items:
            li.new_seat_category.held -= li.num_seats

        await db.commit()

    # 3. Redirect to frontend cancellation page
    return RedirectResponse(
        url=f"{settings.USERS_APPLICATION_FRONTEND_URL}/booking-cancelled?order_id={order_id}",
        status_code=302,
    )


@router.get(
    "/{order_id}",
    status_code=status.HTTP_200_OK,
    response_model=BookingDetailsResponse,
    summary="Fetch booking order details for a user",
)
@exception_handler
async def get_booking_order_details(
    order_id: str,
    db: AsyncSession = Depends(get_db),
):
    # 1️. Fetch order with relationships
    order: NewEventBookingOrder | None = (
        await db.execute(
            select(NewEventBookingOrder)
            .where(NewEventBookingOrder.order_id == order_id)
            .options(
                selectinload(NewEventBookingOrder.line_items).selectinload(
                    NewEventBooking.new_seat_category
                ),
                selectinload(
                    NewEventBookingOrder.new_booked_event
                ).selectinload(NewEvent.new_category),
                selectinload(
                    NewEventBookingOrder.new_booked_event
                ).selectinload(NewEvent.new_organizer),
                selectinload(NewEventBookingOrder.new_slot),
                selectinload(NewEventBookingOrder.new_user),
            )
        )
    ).scalar_one_or_none()

    if not order:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Booking order not found",
            data={},
        )

    # 2️. Build seat categories list
    seat_categories = [
        SeatCategoryItem(
            seat_category_id=li.seat_category_ref_id,
            label=li.new_seat_category.category_label,
            num_seats=li.num_seats,
            price_per_seat=float(li.price_per_seat),
            total_price=float(li.total_price),
        )
        for li in order.line_items
    ]

    # 3️. Build nested user info
    user_info = {
        "user_id": order.new_user.user_id,
        "email": order.new_user.email,
        "username": order.new_user.username,
    }

    # 4. Build nested event info
    event_address = _extract_event_address(order.new_booked_event)
    booked_event = order.new_booked_event
    event_info = {
        "event_id": booked_event.event_id,
        "title": booked_event.event_title,
        "slug": booked_event.event_slug,
        "organizer_name": (
            booked_event.new_organizer.username
            if booked_event.new_organizer
            else None
        ),
        "location": booked_event.location,
        "address": event_address or "",  # fallback if address is optional
        "event_date": (
            order.new_slot.slot_date.strftime("%Y-%m-%d")
            if order.new_slot
            else None
        ),
        "booking_date": order.created_at.strftime("%Y-%m-%d"),
        "card_image": get_media_url(booked_event.card_image),
    }

    # 5️. Build response
    response_data = {
        "order_id": order.order_id,
        "booking_status": order.booking_status.value,
        "payment_status": order.payment_status.value,
        "payment_reference": order.payment_reference,
        "total_amount": float(order.total_amount),
        "event": event_info,
        "user": user_info,
        "seat_categories": seat_categories,
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Booking order details fetched successfully",
        data=response_data,
    )
