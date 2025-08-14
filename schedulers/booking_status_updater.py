from datetime import datetime, timedelta, timezone

from sqlalchemy import not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db.models.events import BookingStatus, EventBooking, EventSlot

HOLD_DURATION_MINUTES = 15  # change as needed


async def release_expired_holds(db: AsyncSession):
    """Release held seats for bookings that are still in processing beyond hold duration."""
    now = datetime.now(timezone.utc)
    expiry_time = now - timedelta(minutes=HOLD_DURATION_MINUTES)

    # Step 1: Get all processing bookings older than expiry time
    result = await db.execute(
        select(EventBooking)
        .where(
            EventBooking.booking_status == BookingStatus.PROCESSING,
            not_(EventBooking.payment_status.in_(["COMPLETED", "FAILED"])),
            EventBooking.created_at <= expiry_time,
        )
        .options(selectinload(EventBooking.booked_event))  # load event relation
        .order_by(EventBooking.created_at.desc())
    )
    bookings = result.scalars().all()

    if not bookings:
        return 0  # No expired bookings

    released_count = 0

    # Step 2: Loop and release seats
    for booking in bookings:
        if not booking.booked_event:
            continue

        await release_event_slot_on_cancel(
            db=db,
            slot_id=booking.booked_event.slot_id,
            booking_date=str(booking.booking_date),
            slot_key=booking.slot,
            num_seats=booking.num_seats,
        )

        # Step 3: Update booking status & payment status
        booking.booking_status = BookingStatus.CANCELLED
        booking.payment_status = "FAILED"

        released_count += 1

    await db.commit()
    return released_count


async def release_event_slot_on_cancel(
    db: AsyncSession,
    slot_id: str,
    booking_date: str,
    slot_key: str,
    num_seats: int,
):
    """Release held seats for a given event slot."""
    result = await db.execute(
        select(EventSlot).where(EventSlot.slot_id == slot_id)
    )
    slot_row = result.scalar_one_or_none()

    if not slot_row:
        return  # Slot not found, skip

    slot_data = slot_row.slot_data or {}

    if booking_date not in slot_data or slot_key not in slot_data[booking_date]:
        return  # Slot key/date mismatch, skip

    slot_info = slot_data[booking_date][slot_key]
    slot_info.setdefault("held", 0)
    slot_info["held"] = max(0, slot_info["held"] - num_seats)

    slot_data[booking_date][slot_key] = slot_info
    slot_row.slot_data = slot_data

    await db.commit()
    await db.refresh(slot_row)
