
# from collections import defaultdict
# from decimal import Decimal

# from fastapi import APIRouter, Depends, HTTPException, Path, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from sqlalchemy.orm import selectinload
# from typing import Optional

# from shared.db.sessions.database import get_db
# from shared.db.models.new_events import (
#     EventStatus,
#     NewEvent,
#     NewEventBookingOrder,
#     NewEventSlot,
# )
# from shared.utils.file_uploads import get_media_url

# router = APIRouter()


# @router.get("/settlement/{event_id}", summary="Get Event with Organizer and Settlement Summary")
# async def get_event_settlement(
#     event_id: str = Path(..., min_length=6, max_length=6, description="Event ID"),
#     db: AsyncSession = Depends(get_db),
# ):
#     # --------------------------
#     # Fetch event with relationships
#     # --------------------------
#     stmt = (
#         select(NewEvent)
#         .where(NewEvent.event_id == event_id) # NewEvent.event_status == EventStatus.INACTIVE
#         .options(
#             selectinload(NewEvent.new_category),
#             selectinload(NewEvent.new_subcategory),
#             selectinload(NewEvent.new_organizer),
#             selectinload(NewEvent.new_slots).selectinload(
#                 NewEventSlot.new_seat_categories
#             ),
#             selectinload(NewEvent.coupons),
#             selectinload(NewEvent.new_booking_orders).selectinload(
#                 NewEventBookingOrder.line_items
#             ),
#         )
#     )
#     result = await db.execute(stmt)
#     event: Optional[NewEvent] = result.scalar_one_or_none()

#     if not event:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Event with ID {event_id} not found",
#         )

#     # --------------------------
#     # Daily + Overall Aggregation
#     # --------------------------
#     daily_summary: dict[str, dict] = defaultdict(
#         lambda: {
#             "slots_count": 0,
#             "seat_categories": defaultdict(
#                 lambda: {"price": 0, "total_tickets": 0, "booked": 0, "total_price": 0}
#             ),
#             "total_tickets_booked": 0,
#             "overall_total_tickets": 0,
#         }
#     )

#     overall = {
#         "slots_count": 0,
#         "seat_categories": defaultdict(
#             lambda: {"price": 0, "total_tickets": 0, "booked": 0, "total_price": 0}
#         ),
#         "total_tickets_booked": 0,
#         "overall_total_tickets": 0,
#     }

#     gross_amount = Decimal("0.00")
#     net_amount = Decimal("0.00")

#     # --------------------------
#     # Slot + Seat Aggregation
#     # --------------------------
#     for slot in event.new_slots:
#         day_key = str(slot.slot_date)
#         daily_summary[day_key]["slots_count"] += 1
#         overall["slots_count"] += 1

#         for seat in slot.new_seat_categories:
#             price = float(seat.price)
#             booked = seat.booked
#             total_tickets = seat.total_tickets

#             # Update daily
#             seat_daily = daily_summary[day_key]["seat_categories"][seat.category_label]
#             seat_daily["price"] = price
#             seat_daily["total_tickets"] += total_tickets
#             seat_daily["booked"] += booked
#             seat_daily["total_price"] = seat_daily["booked"] * price

#             # Update overall
#             seat_overall = overall["seat_categories"][seat.category_label]
#             seat_overall["price"] = price
#             seat_overall["total_tickets"] += total_tickets
#             seat_overall["booked"] += booked
#             seat_overall["total_price"] = seat_overall["booked"] * price

#             # Counters
#             daily_summary[day_key]["total_tickets_booked"] += booked
#             daily_summary[day_key]["overall_total_tickets"] += total_tickets
#             overall["total_tickets_booked"] += booked
#             overall["overall_total_tickets"] += total_tickets

#     # --------------------------
#     # Orders → Revenue Calculation
#     # --------------------------
#     for order in event.new_booking_orders:
#         net_amount += Decimal(order.total_amount)
#         for line in order.line_items:
#             gross_amount += Decimal(line.total_price)

#     discount_amount = gross_amount - net_amount

#     # --------------------------
#     # Final Settlement Summary
#     # --------------------------
#     extra_data = event.extra_data or {}
#     featured_amount = getattr(event, "featured_amount", None) or extra_data.get("featured_amount")

#     formatted_daily = {
#         day: {
#             "slots_count": data["slots_count"],
#             "total_tickets_booked": data["total_tickets_booked"],
#             "overall_total_tickets": data["overall_total_tickets"],
#             "seat_categories": dict(data["seat_categories"]),
#         }
#         for day, data in daily_summary.items()
#     }

#     formatted_overall = {
#         "slots_count": overall["slots_count"],
#         "total_tickets_booked": overall["total_tickets_booked"],
#         "overall_total_tickets": overall["overall_total_tickets"],
#         "seat_categories": dict(overall["seat_categories"]),
#         "gross_amount": float(gross_amount),
#         "discount_amount": float(discount_amount),
#         "ticket_net_amount": float(net_amount),
#         "featured_amount": float(featured_amount) if featured_amount else 0.0,
#         "grand_total_settlement": float(net_amount + (Decimal(featured_amount) if featured_amount else 0)),
#     }

#     response = {
#         "event": {
#             "event_id": event.event_id,
#             "title": event.event_title,
#             "slug": event.event_slug,
#             "type": event.event_type,
#             "status": getattr(event.event_status, "value", str(event.event_status)),
#             "location": event.location,
#             "dates": event.event_dates,
#             "featured": event.featured_event,
#             "featured_amount": featured_amount,
#             "created_at": event.created_at,
#             "card_image": get_media_url(event.card_image),
#             "organizer_name": extra_data.get("organizer_name"),
#             "organizer_email": extra_data.get("organizer_email"),
#             "organizer_contact": extra_data.get("organizer_contact"),
#             "address": extra_data.get("address"),
#             "category": event.new_category.category_name if event.new_category else None,
#             "subcategory": (
#                 event.new_subcategory.subcategory_name if event.new_subcategory else None
#             ),
#         },
#         "organizer": {
#             "user_id": event.new_organizer.user_id if event.new_organizer else None,
#             "name": event.new_organizer.username if event.new_organizer else None,
#             "email": event.new_organizer.email if event.new_organizer else None,
#             "profile_picture": get_media_url(event.new_organizer.profile_picture)
#             if event.new_organizer else None,
#         },
#         "settlement_summary": {
#             "total_slots": overall["slots_count"],
#             "daily": formatted_daily,
#             "overall": formatted_overall,
#         },
#     }

#     return response


from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List, Set

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# --- import your models and deps ---
# Adjust import paths as per your project structure
from shared.db.sessions.database import get_db
from shared.db.models.new_events import (
    NewEvent,
    NewEventSlot,
    NewEventSeatCategory,
    NewEventBookingOrder,
    NewEventBooking,
    PaymentStatus,
)
from shared.utils.file_uploads import get_media_url  # keep using your helper if present

router = APIRouter()

TWOPLACES = Decimal("0.01")


def D(x) -> Decimal:
    """Safely coerce to Decimal and quantize to 2dp."""
    if x is None:
        x = 0
    if isinstance(x, Decimal):
        val = x
    else:
        val = Decimal(str(x))
    return val.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@router.get("/settlement/{event_id}", summary="Organizer Settlement Invoice + Summary")
async def get_event_settlement(
    event_id: str = Path(..., min_length=6, max_length=6, description="Event ID"),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch event + deep relations
    # --------------------------
    stmt = (
        select(NewEvent)
        .where(NewEvent.event_id == event_id)
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
            selectinload(NewEvent.new_organizer),
            selectinload(NewEvent.coupons),
            selectinload(NewEvent.new_slots).selectinload(
                NewEventSlot.new_seat_categories
            ),
            # Orders & line items with coupon + seat -> slot for date
            selectinload(NewEvent.new_booking_orders)
            .selectinload(NewEventBookingOrder.line_items)
            .selectinload(NewEventBooking.coupon),
            selectinload(NewEvent.new_booking_orders)
            .selectinload(NewEventBookingOrder.line_items)
            .selectinload(NewEventBooking.new_seat_category)
            .selectinload(NewEventSeatCategory.new_slot),
        )
    )
    result = await db.execute(stmt)
    event: Optional[NewEvent] = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found",
        )

    extra: Dict[str, Any] = event.extra_data or {}
    currency = (extra.get("currency") or "INR").upper()

    # --------------------------
    # Configurable commercial terms (fallbacks)
    # --------------------------
    platform_name = extra.get("platform_name") or "Events2Go"
    platform_address = extra.get("platform_address") or "4th Floor Madhapur, Hyderabad, Telangana, India - 500081"
    platform_gstin = extra.get("platform_gstin") or "GSTIN-PLATFORM-0000"
    organizer_gstin = extra.get("organizer_gstin") or "GSTIN-ORGANIZER-0000"
    platform_fee_rate = D(extra.get("platform_fee_rate") or "0")  # % of recognized revenue
    processing_fee_rate = D(extra.get("processing_fee_rate") or "0")  # % of recognized revenue
    tax_rate = D(extra.get("tax_rate") or "0")  # GST/VAT % on fees
    featured_amount = D(extra.get("featured_amount") or "0")  # charged to organizer (adds to payable)
    manual_adjustments = D(extra.get("manual_adjustments") or "0")  # +/- adjustments
    payment_gateway = extra.get("payment_gateway") or "PayPal"

    # --------------------------
    # Helper maps (seat_id -> (label, price, slot_date))
    # --------------------------
    seat_meta: Dict[str, Dict[str, Any]] = {}
    for slot in event.new_slots:
        for seat in slot.new_seat_categories:
            seat_meta[seat.seat_category_id] = {
                "label": seat.category_label,
                "price": D(seat.price),
                "slot_date": slot.slot_date,
                "slot_id": slot.slot_id,
            }

    # --------------------------
    # Revenue & ticket sales from PAID orders only
    # --------------------------
    valid_payments = {PaymentStatus.APPROVED, PaymentStatus.COMPLETED}
    refunded_payments = {PaymentStatus.REFUNDED}
    partial_refunds = {PaymentStatus.PARTIALLY_REFUNDED}

    orders_paid: List[NewEventBookingOrder] = []
    orders_refunded_full: List[NewEventBookingOrder] = []
    orders_partial: List[NewEventBookingOrder] = []

    for order in event.new_booking_orders:
        if order.payment_status in valid_payments:
            orders_paid.append(order)
        elif order.payment_status in refunded_payments:
            orders_refunded_full.append(order)
        elif order.payment_status in partial_refunds:
            orders_partial.append(order)
        else:
            # ignore failed/cancelled/pending for settlement
            pass

    # Ticket counts & revenue strictly from line items of PAID orders
    gross_ticket = D(0)
    coupon_discount = D(0)
    net_ticket = D(0)
    orders_count = 0
    unique_buyers: Set[str] = set()
    total_tickets_sold = 0

    # Groupings for invoice lines:
    # 1) tiered: (date, label, price) -> aggregations
    by_date_label_price: Dict[tuple, Dict[str, Any]] = defaultdict(
        lambda: {"qty": 0, "subtotal": D(0), "discount": D(0), "net": D(0)}
    )

    # 2) roll-up: label -> {total_qty, total_subtotal, total_discount, total_net, tiers:{price->qty}}
    by_label_rollup: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"total_qty": 0, "total_subtotal": D(0), "total_discount": D(0), "total_net": D(0), "tiers": defaultdict(int)}
    )

    for order in orders_paid:
        orders_count += 1
        if order.user_ref_id:
            unique_buyers.add(order.user_ref_id)

        for li in order.line_items:
            # robustly use line item financials (most accurate)
            li_subtotal = D(li.subtotal)
            li_discount = D(li.discount_amount)
            li_net = D(li.total_amount)

            gross_ticket += li_subtotal
            coupon_discount += li_discount
            net_ticket += li_net

            qty = int(li.num_seats or 0)
            total_tickets_sold += qty

            meta = seat_meta.get(li.seat_category_ref_id)
            if not meta:
                # seat might have been deleted; still keep it under "Unknown"
                key = (order.slot_ref_id, "Unknown", D(li.price_per_seat))
                date_key = None
            else:
                key = (meta["slot_date"], meta["label"], meta["price"])
                date_key = meta["slot_date"]

            # Tiered grouping
            grp = by_date_label_price[key]
            grp["qty"] += qty
            grp["subtotal"] += li_subtotal
            grp["discount"] += li_discount
            grp["net"] += li_net

            # Label rollup
            lbl = key[1]
            by_label_rollup[lbl]["total_qty"] += qty
            by_label_rollup[lbl]["total_subtotal"] += li_subtotal
            by_label_rollup[lbl]["total_discount"] += li_discount
            by_label_rollup[lbl]["total_net"] += li_net
            by_label_rollup[lbl]["tiers"][str(key[2])] += qty  # price -> qty

    # Refunds (full) reduce recognized revenue
    refunds_full = sum(D(o.total_amount) for o in orders_refunded_full)

    # Partial refunds: we don't have a concrete amount in schema.
    # You can store it in `extra_data['partial_refunds_amount']`; default to 0 for now.
    partial_refunds_amount = D(extra.get("partial_refunds_amount") or "0")

    recognized_after_refunds = (net_ticket - refunds_full - partial_refunds_amount).quantize(TWOPLACES)

    # Fees & taxes (applied on recognized revenue)
    platform_fee = (recognized_after_refunds * platform_fee_rate / D(100)).quantize(TWOPLACES)
    processing_fee = (recognized_after_refunds * processing_fee_rate / D(100)).quantize(TWOPLACES)
    tax_on_fees = ((platform_fee + processing_fee) * tax_rate / D(100)).quantize(TWOPLACES)

    # Final settlement payable to organizer
    grand_total_settlement = (recognized_after_refunds - platform_fee - processing_fee - tax_on_fees + featured_amount + manual_adjustments).quantize(TWOPLACES)

    # --------------------------
    # Daily & overall capacity snapshot (optional, from seat definitions)
    # Note: for financial truth we used orders above; this section is just capacity context.
    # --------------------------
    daily_capacity: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"slots_count": 0, "overall_total_tickets": 0, "seat_categories": defaultdict(lambda: {"price_tiers": defaultdict(int), "total_tickets": 0})}
    )
    overall_capacity = {
        "slots_count": 0,
        "overall_total_tickets": 0,
        "seat_categories": defaultdict(lambda: {"price_tiers": defaultdict(int), "total_tickets": 0}),
    }

    for slot in event.new_slots:
        day_key = str(slot.slot_date)
        daily_capacity[day_key]["slots_count"] += 1
        overall_capacity["slots_count"] += 1

        for seat in slot.new_seat_categories:
            label = seat.category_label
            price = D(seat.price)
            total_tickets = int(seat.total_tickets or 0)

            daily_capacity[day_key]["seat_categories"][label]["price_tiers"][str(price)] += total_tickets
            daily_capacity[day_key]["seat_categories"][label]["total_tickets"] += total_tickets
            daily_capacity[day_key]["overall_total_tickets"] += total_tickets

            overall_capacity["seat_categories"][label]["price_tiers"][str(price)] += total_tickets
            overall_capacity["seat_categories"][label]["total_tickets"] += total_tickets
            overall_capacity["overall_total_tickets"] += total_tickets

    # --------------------------
    # Coupons snapshot
    # --------------------------
    coupons_snapshot = []
    for c in event.coupons:
        coupons_snapshot.append({
            "coupon_id": c.coupon_id,
            "coupon_code": c.coupon_code,
            "percentage": D(c.coupon_percentage),
            "issued": int(c.number_of_coupons or 0),
            "applied": int(c.applied_coupons or 0),
            "redeemed": int(c.sold_coupons or 0),
            "status": bool(c.coupon_status),
            "created_at": c.created_at,
        })

    # --------------------------
    # Invoice construction
    # --------------------------
    # Pick a sensible period: min/max slot_date if available, otherwise event_dates
    all_dates: List[date] = sorted([s["slot_date"] for s in seat_meta.values() if s.get("slot_date")])
    if not all_dates and event.event_dates:
        all_dates = sorted(event.event_dates or [])
    period_from = str(all_dates[0]) if all_dates else None
    period_to = str(all_dates[-1]) if all_dates else None

    invoice_no = f"INV-{event.event_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    invoice_date = datetime.utcnow()

    # Build invoice lines from tiered grouping (date, label, price)
    # Sort by date, then label, then price for readability
    def sort_key(k: tuple):
        d, lbl, pr = k
        # handle "Unknown" case
        dsort = d if isinstance(d, date) else date(1970, 1, 1)
        return (dsort, str(lbl), D(pr))

    invoice_lines = []
    for key in sorted(by_date_label_price.keys(), key=sort_key):
        k_date, k_label, k_price = key
        agg = by_date_label_price[key]
        line = {
            "date": str(k_date) if isinstance(k_date, date) else None,
            "category_label": k_label,
            "unit_price": float(D(k_price)),
            "quantity": int(agg["qty"]),
            "subtotal": float(D(agg["subtotal"])),
            "discount": float(D(agg["discount"])),
            "net": float(D(agg["net"])),
        }
        invoice_lines.append(line)

    # Roll-up by label
    by_label = []
    for label, agg in sorted(by_label_rollup.items(), key=lambda x: x[0]):
        tiers_list = [{"price": float(D(p)), "quantity": int(q)} for p, q in sorted(agg["tiers"].items(), key=lambda x: D(x[0]))]
        by_label.append({
            "category_label": label,
            "total_quantity": int(agg["total_qty"]),
            "total_subtotal": float(D(agg["total_subtotal"])),
            "total_discount": float(D(agg["total_discount"])),
            "total_net": float(D(agg["total_net"])),
            "price_tiers": tiers_list,
        })

    # Organizer canonical info (prefer relation; fall back to extra)
    organizer_block = {
        "user_id": event.new_organizer.user_id if event.new_organizer else None,
        "name": getattr(event.new_organizer, "username", None) if event.new_organizer else (extra.get("organizer") or None),
        "email": getattr(event.new_organizer, "email", None) if event.new_organizer else (extra.get("organizer_email") or None),
        "contact": extra.get("organizer_contact"),
        "gstin": organizer_gstin,
        "profile_picture": get_media_url(event.new_organizer.profile_picture) if getattr(event.new_organizer, "profile_picture", None) else None,
        "address": extra.get("address"),
    }

    invoice = {
        "invoice_no": invoice_no,
        "invoice_date": invoice_date,
        "currency": currency,
        "billing_from": {
            "name": platform_name,
            "address": platform_address,
            "gstin": platform_gstin,
        },
        "billing_to": organizer_block,
        "event": {
            "event_id": event.event_id,
            "title": event.event_title,
            "slug": event.event_slug,
            "type": event.event_type,
            "status": getattr(event.event_status, "value", str(event.event_status)),
            "period_from": period_from,
            "period_to": period_to,
            "location": event.location,
            "category": event.new_category.category_name if event.new_category else None,
            "subcategory": event.new_subcategory.subcategory_name if event.new_subcategory else None,
            "card_image": get_media_url(event.card_image) if event.card_image else None,
            "featured": event.featured_event,
        },
        "lines": invoice_lines,  # (date, label, unit_price) tiers separated
        "summary": {
            "orders_count": orders_count,
            "unique_buyers": len(unique_buyers),
            "tickets_sold": total_tickets_sold,
            "gross_ticket_revenue": float(gross_ticket),
            "coupon_discount": float(coupon_discount),
            "net_ticket_revenue": float(net_ticket),
            "refunds_full": float(refunds_full),
            "refunds_partial": float(partial_refunds_amount),
            "recognized_after_refunds": float(recognized_after_refunds),
            "platform_fee_rate_percent": float(platform_fee_rate),
            "processing_fee_rate_percent": float(processing_fee_rate),
            "tax_rate_percent": float(tax_rate),
            "platform_fee": float(platform_fee),
            "processing_fee": float(processing_fee),
            "tax_on_fees": float(tax_on_fees),
            "featured_amount": float(featured_amount),
            "manual_adjustments": float(manual_adjustments),
            "grand_total_settlement": float(grand_total_settlement),
            "payment_gateway": payment_gateway,
        },
        "notes": [
            "Ticket revenue is recognized only for APPROVED/COMPLETED payments.",
            "Full refunds fully reverse recognized revenue; partial refunds require explicit amount (see extra_data.partial_refunds_amount).",
            "Each price tier for the same category label is listed as a separate invoice line for auditability.",
        ],
    }

    # --------------------------
    # Final API response
    # --------------------------
    response = {
        "invoice": invoice,
        "organizer": organizer_block,
        "coupons": coupons_snapshot,
        "sales_rollup_by_label": by_label,  # single line per label (with tiers list)
        "capacity_snapshot": {
            "daily": {
                day: {
                    "slots_count": data["slots_count"],
                    "overall_total_tickets": data["overall_total_tickets"],
                    "seat_categories": {
                        lbl: {"total_tickets": sc["total_tickets"], "price_tiers": dict(sc["price_tiers"])}
                        for lbl, sc in data["seat_categories"].items()
                    },
                }
                for day, data in sorted(daily_capacity.items())
            },
            "overall": {
                "slots_count": overall_capacity["slots_count"],
                "overall_total_tickets": overall_capacity["overall_total_tickets"],
                "seat_categories": {
                    lbl: {"total_tickets": sc["total_tickets"], "price_tiers": dict(sc["price_tiers"])}
                    for lbl, sc in overall_capacity["seat_categories"].items()
                },
            },
        },
    }
    return response
