
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from shared.db.sessions.database import get_db
from shared.db.models.new_events import (
    EventStatus,
    NewEvent,
    NewEventBookingOrder,
    NewEventSlot,
)
from shared.utils.file_uploads import get_media_url

router = APIRouter()


@router.get("/settlement/{event_id}", summary="Get Event with Organizer and Settlement Summary")
async def get_event_settlement(
    event_id: str = Path(..., min_length=6, max_length=6, description="Event ID"),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch event with relationships
    # --------------------------
    stmt = (
        select(NewEvent)
        .where(NewEvent.event_id == event_id) # NewEvent.event_status == EventStatus.INACTIVE
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
            selectinload(NewEvent.new_organizer),
            selectinload(NewEvent.new_slots).selectinload(
                NewEventSlot.new_seat_categories
            ),
            selectinload(NewEvent.coupons),
            selectinload(NewEvent.new_booking_orders).selectinload(
                NewEventBookingOrder.line_items
            ),
        )
    )
    result = await db.execute(stmt)
    event: Optional[NewEvent] = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found",
        )

    # --------------------------
    # Daily + Overall Aggregation
    # --------------------------
    daily_summary: dict[str, dict] = defaultdict(
        lambda: {
            "slots_count": 0,
            "seat_categories": defaultdict(
                lambda: {"price": 0, "total_tickets": 0, "booked": 0, "total_price": 0}
            ),
            "total_tickets_booked": 0,
            "overall_total_tickets": 0,
        }
    )

    overall = {
        "slots_count": 0,
        "seat_categories": defaultdict(
            lambda: {"price": 0, "total_tickets": 0, "booked": 0, "total_price": 0}
        ),
        "total_tickets_booked": 0,
        "overall_total_tickets": 0,
    }

    gross_amount = Decimal("0.00")
    net_amount = Decimal("0.00")

    # --------------------------
    # Slot + Seat Aggregation
    # --------------------------
    for slot in event.new_slots:
        day_key = str(slot.slot_date)
        daily_summary[day_key]["slots_count"] += 1
        overall["slots_count"] += 1

        for seat in slot.new_seat_categories:
            price = float(seat.price)
            booked = seat.booked
            total_tickets = seat.total_tickets

            # Update daily
            seat_daily = daily_summary[day_key]["seat_categories"][seat.category_label]
            seat_daily["price"] = price
            seat_daily["total_tickets"] += total_tickets
            seat_daily["booked"] += booked
            seat_daily["total_price"] = seat_daily["booked"] * price

            # Update overall
            seat_overall = overall["seat_categories"][seat.category_label]
            seat_overall["price"] = price
            seat_overall["total_tickets"] += total_tickets
            seat_overall["booked"] += booked
            seat_overall["total_price"] = seat_overall["booked"] * price

            # Counters
            daily_summary[day_key]["total_tickets_booked"] += booked
            daily_summary[day_key]["overall_total_tickets"] += total_tickets
            overall["total_tickets_booked"] += booked
            overall["overall_total_tickets"] += total_tickets

    # --------------------------
    # Orders → Revenue Calculation
    # --------------------------
    for order in event.new_booking_orders:
        net_amount += Decimal(order.total_amount)
        for line in order.line_items:
            gross_amount += Decimal(line.total_price)

    discount_amount = gross_amount - net_amount

    # --------------------------
    # Final Settlement Summary
    # --------------------------
    extra_data = event.extra_data or {}
    featured_amount = getattr(event, "featured_amount", None) or extra_data.get("featured_amount")

    formatted_daily = {
        day: {
            "slots_count": data["slots_count"],
            "total_tickets_booked": data["total_tickets_booked"],
            "overall_total_tickets": data["overall_total_tickets"],
            "seat_categories": dict(data["seat_categories"]),
        }
        for day, data in daily_summary.items()
    }

    formatted_overall = {
        "slots_count": overall["slots_count"],
        "total_tickets_booked": overall["total_tickets_booked"],
        "overall_total_tickets": overall["overall_total_tickets"],
        "seat_categories": dict(overall["seat_categories"]),
        "gross_amount": float(gross_amount),
        "discount_amount": float(discount_amount),
        "ticket_net_amount": float(net_amount),
        "featured_amount": float(featured_amount) if featured_amount else 0.0,
        "grand_total_settlement": float(net_amount + (Decimal(featured_amount) if featured_amount else 0)),
    }

    response = {
        "event": {
            "event_id": event.event_id,
            "title": event.event_title,
            "slug": event.event_slug,
            "type": event.event_type,
            "status": getattr(event.event_status, "value", str(event.event_status)),
            "location": event.location,
            "dates": event.event_dates,
            "featured": event.featured_event,
            "featured_amount": featured_amount,
            "created_at": event.created_at,
            "card_image": get_media_url(event.card_image),
            "organizer_name": extra_data.get("organizer_name"),
            "organizer_email": extra_data.get("organizer_email"),
            "organizer_contact": extra_data.get("organizer_contact"),
            "address": extra_data.get("address"),
            "category": event.new_category.category_name if event.new_category else None,
            "subcategory": (
                event.new_subcategory.subcategory_name if event.new_subcategory else None
            ),
        },
        "organizer": {
            "user_id": event.new_organizer.user_id if event.new_organizer else None,
            "name": event.new_organizer.username if event.new_organizer else None,
            "email": event.new_organizer.email if event.new_organizer else None,
            "profile_picture": get_media_url(event.new_organizer.profile_picture)
            if event.new_organizer else None,
        },
        "settlement_summary": {
            "total_slots": overall["slots_count"],
            "daily": formatted_daily,
            "overall": formatted_overall,
        },
    }

    return response
