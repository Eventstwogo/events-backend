from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException
from paypalcheckoutsdk.orders import OrdersCreateRequest
from sqlalchemy import Select, and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.services.bookings import (
    check_existing_booking,
    verify_booking_constraints,
)
from event_service.utils.paypal_client import paypal_client
from shared.core.config import settings
from shared.db.models.events import Event, EventSlot, EventStatus


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


async def validate_booking(
    db: AsyncSession,
    user_id: str,
    event_id: str,
    slot: str,
    booking_date: date,
    num_seats: int,
) -> Tuple[bool, str]:
    """Run all booking validations once."""
    # Check duplicate booking
    can_book_duplicate, duplicate_message, _ = await check_existing_booking(
        db, user_id, event_id, slot, booking_date
    )
    if not can_book_duplicate:
        return False, duplicate_message

    # Check booking constraints
    can_book, constraint_message = await verify_booking_constraints(
        db, event_id, num_seats, slot
    )
    if not can_book:
        return False, constraint_message

    return True, "Booking can be made"


async def create_paypal_order(
    total_price: float, booking_id: str
) -> Optional[str]:
    """Create PayPal order and return approval URL."""
    request = OrdersCreateRequest()
    request.headers["prefer"] = "return=representation"
    request.request_body(
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "AUD",
                        "value": str(round(total_price, 2)),
                    }
                }
            ],
            "application_context": {
                "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                "brand_name": "Events2Go",
                "landing_page": "LOGIN",
                "locale": "en-AU",
                "user_action": "PAY_NOW",
                "return_url": f"{settings.API_BACKEND_URL}/api/v1/bookings/confirm?booking_id={booking_id}",
                "cancel_url": f"{settings.API_BACKEND_URL}/api/v1/bookings/cancel?booking_id={booking_id}",
            },
        }
    )
    response = paypal_client.client.execute(request)
    return extract_approval_url_from_paypal_response(response)


def _json_path(date_key: str, slot_key: str, leaf: str) -> list[str]:
    # e.g. ["2025-08-14", "slot_1", "held"]
    return [date_key, slot_key, leaf]


async def _read_slot_numbers(
    event_slot: "EventSlot", date_key: str, slot_key: str
) -> Tuple[int, int, int]:
    """
    Returns (capacity, booked, held) from event_slot.slot_data for given date & slot.
    Missing values are treated as 0 for booked/held.
    Raises ValueError if date/slot not found or capacity missing.
    """
    sd: Dict[str, Any] = event_slot.slot_data or {}
    if date_key not in sd:
        raise ValueError(
            f"Selected date {date_key} not available for this event."
        )
    day = sd[date_key]
    if slot_key not in day:
        raise ValueError(
            f"Selected slot {slot_key} not available for date {date_key}."
        )
    slot = day[slot_key] or {}

    capacity = int(slot.get("capacity", 0))
    if capacity <= 0:
        raise ValueError("Slot capacity is not configured.")

    booked = int(slot.get("booked", 0))
    held = int(slot.get("held", 0))
    return capacity, booked, held


async def _increment_jsonb_int_field(
    db: AsyncSession,
    slot_id: str,
    date_key: str,
    slot_key: str,
    field: str,
    delta: int,
) -> None:
    """
    Atomically increments a JSONB integer field: slot_data->{date}->{slot}->{field} by delta.
    Creates the field if missing. Uses PostgreSQL jsonb_set for atomicity.
    """
    # Build SQL using jsonb_set and #>> to read existing leaf as text, cast to int, coalesce to 0
    # Example:
    # slot_data = jsonb_set(
    #   slot_data,
    #   '{2025-08-14,slot_1,held}',
    #   to_jsonb( COALESCE( (slot_data #>> '{2025-08-14,slot_1,held}')::int, 0 ) + :delta ),
    #   true
    # )
    held_path = _json_path(date_key, slot_key, field)
    stmt = text(
        f"""
        UPDATE e2geventslots
        SET slot_data = jsonb_set(
            slot_data,
            :path,
            to_jsonb( COALESCE( (slot_data #>> :path)::int, 0 ) + :delta ),
            true
        ),
        updated_at = NOW()
        WHERE slot_id = :slot_id
    """
    )
    await db.execute(
        stmt, {"path": held_path, "delta": delta, "slot_id": slot_id}
    )


# --- Fetch/lock helpers ------------------------------------------------------
async def _get_active_event_and_lock_slot(
    db: AsyncSession, event_id: str
) -> Tuple[Event, EventSlot]:
    """
    Fetch ACTIVE event and its associated EventSlot, locking only the slot row FOR UPDATE
    to safely update seats in concurrent bookings.
    """

    # 1) Fetch ACTIVE event first — no joins
    event_q: Select = select(Event).where(
        and_(
            Event.event_id == event_id,
            Event.event_status == EventStatus.ACTIVE,
        )
    )
    event = (await db.execute(event_q)).scalar_one_or_none()
    if not event:
        raise ValueError("Event not found or not active.")

    # 2) Check event date
    if event.end_date and event.end_date < datetime.now(timezone.utc).date():
        raise ValueError("Event has already ended.")

    if not event.slot_id:
        raise ValueError("Event has no associated slot ID.")

    # 3) Lock only the EventSlot row
    slot_q: Select = (
        select(EventSlot)
        .where(EventSlot.slot_id == event.slot_id)
        .with_for_update(
            of=EventSlot
        )  # lock only this table, avoids nullable join issues
    )
    event_slot = (await db.execute(slot_q)).scalar_one_or_none()
    if not event_slot:
        raise ValueError("Event slot configuration not found.")

    if event_slot.slot_status:  # Assuming True means inactive
        raise ValueError("Event slot is inactive.")

    return event, event_slot


# --- Availability + hold -----------------------------------------------------
async def verify_and_hold_seats(
    db: AsyncSession,
    event_id: str,
    booking_date: date,
    slot_key: str,
    num_seats: int,
) -> Tuple["Event", "EventSlot"]:
    """
    Verifies availability (capacity - booked - held >= num_seats) and atomically increments 'held' by num_seats.
    Uses a single transaction with row lock for safety.
    """
    if num_seats <= 0:
        raise ValueError("Number of seats must be greater than 0.")

    date_key = booking_date.isoformat()

    # Lock the slot row to serialize concurrent updates
    event, event_slot = await _get_active_event_and_lock_slot(db, event_id)

    # Compute current numbers
    capacity, booked, held = await _read_slot_numbers(
        event_slot, date_key, slot_key
    )
    available = capacity - booked - held
    if available < num_seats:
        raise ValueError(f"Not enough seats available. Only {available} left.")

    # Increment held atomically
    await _increment_jsonb_int_field(
        db, event.slot_id, date_key, slot_key, "held", num_seats
    )

    return event, event_slot


# --- Confirm / Cancel helpers (for your next endpoints) ----------------------
async def move_held_to_booked(
    db: AsyncSession,
    slot_id: str,
    booking_date: date,
    slot_key: str,
    seats: int,
) -> None:
    # held -= seats; booked += seats
    date_key = booking_date.isoformat()
    await _increment_jsonb_int_field(
        db, slot_id, date_key, slot_key, "held", -seats
    )
    await _increment_jsonb_int_field(
        db, slot_id, date_key, slot_key, "booked", seats
    )


async def release_held(
    db: AsyncSession,
    slot_id: str,
    booking_date: date,
    slot_key: str,
    seats: int,
) -> None:
    # held -= seats
    date_key = booking_date.isoformat()
    await _increment_jsonb_int_field(
        db, slot_id, date_key, slot_key, "held", -seats
    )


async def update_event_slot_after_payment(
    db: AsyncSession,
    slot_id: str,
    booking_date: str,
    slot_key: str,
    num_seats: int,
):
    """Update JSONB slot_data after successful payment."""
    # Get event slot row
    result = await db.execute(
        select(EventSlot).where(EventSlot.slot_id == slot_id)
    )
    slot_row = result.scalar_one_or_none()

    if not slot_row:
        raise HTTPException(status_code=404, detail="Event slot not found.")

    slot_data = dict(slot_row.slot_data or {})

    if booking_date not in slot_data or slot_key not in slot_data[booking_date]:
        raise HTTPException(
            status_code=400, detail="Invalid booking date or slot key."
        )

    slot_info = dict(slot_data[booking_date][slot_key])

    # Ensure held/booked keys exist
    slot_info.setdefault("held", 0)
    slot_info.setdefault("booked", 0)

    if slot_info["held"] < num_seats:
        raise HTTPException(
            status_code=400, detail="Not enough held seats to confirm booking."
        )

    print("Before: ", slot_data)
    # Update values
    slot_info["held"] -= num_seats
    slot_info["booked"] += num_seats

    # Save back to DB
    slot_data[booking_date][slot_key] = slot_info
    slot_row.slot_data = slot_data

    print("After: ", slot_data)

    await db.commit()
    await db.refresh(slot_row)


async def release_event_slot_on_cancel(
    db: AsyncSession,
    slot_id: str,
    booking_date: str,
    slot_key: str,
    num_seats: int,
):
    """Release held seats when booking is cancelled or failed."""
    result = await db.execute(
        select(EventSlot).where(EventSlot.slot_id == slot_id)
    )
    slot_row = result.scalar_one_or_none()

    if not slot_row:
        raise HTTPException(status_code=404, detail="Event slot not found.")

    slot_data = slot_row.slot_data or {}

    if booking_date not in slot_data or slot_key not in slot_data[booking_date]:
        raise HTTPException(
            status_code=400, detail="Invalid booking date or slot key."
        )

    slot_info = slot_data[booking_date][slot_key]

    slot_info.setdefault("held", 0)

    # Reduce held seats but prevent negative values
    slot_info["held"] = max(0, slot_info["held"] - num_seats)

    slot_data[booking_date][slot_key] = slot_info
    slot_row.slot_data = slot_data

    await db.commit()
    await db.refresh(slot_row)
