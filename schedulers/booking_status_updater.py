from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db.models.new_events import (
    BookingStatus,
    NewEventBookingOrder,
    NewEventSeatCategory,
    PaymentStatus,
)
from shared.db.sessions.database import AsyncSessionLocal

HOLD_DURATION_MINUTES = 15  # configurable


async def release_expired_holds(db: AsyncSession):
    """
    Release held seats for orders that are still PROCESSING beyond hold duration.
    Moves them to CANCELLED/FAILED and frees seat_category.held counts.
    """
    now = datetime.now(timezone.utc)
    expiry_time = now - timedelta(minutes=HOLD_DURATION_MINUTES)

    # Step 1: Find expired orders in PROCESSING
    result = await db.execute(
        select(NewEventBookingOrder)
        .where(
            NewEventBookingOrder.booking_status == BookingStatus.PROCESSING,
            NewEventBookingOrder.payment_status.notin_(
                [PaymentStatus.COMPLETED, PaymentStatus.FAILED]
            ),
            NewEventBookingOrder.created_at <= expiry_time,
        )
        .options(selectinload(NewEventBookingOrder.line_items))
    )
    expired_orders = result.scalars().all()

    if not expired_orders:
        return 0

    released_count = 0

    # Step 2: Loop through orders & line items
    for order in expired_orders:
        for line_item in order.line_items:
            await release_seat_category_hold(
                db=db,
                seat_category_id=line_item.seat_category_ref_id,
                num_seats=line_item.num_seats,
            )
            released_count += 1

        # Step 3: Mark order as cancelled/failed
        order.booking_status = BookingStatus.CANCELLED
        order.payment_status = PaymentStatus.FAILED

    await db.commit()
    return released_count


async def release_seat_category_hold(
    db: AsyncSession,
    seat_category_id: str,
    num_seats: int,
):
    """Decrement held seats for a specific seat category when a booking expires."""
    result = await db.execute(
        select(NewEventSeatCategory).where(
            NewEventSeatCategory.seat_category_id == seat_category_id
        )
    )
    seat_category = result.scalar_one_or_none()

    if not seat_category:
        return  # Invalid reference, skip

    # Safely decrement held count
    seat_category.held = max(0, seat_category.held - num_seats)

    db.add(seat_category)  # mark as dirty for update
    await db.flush()


async def cleanup_job():
    async with AsyncSessionLocal() as db:
        released = await release_expired_holds(db)
        if released:
            print(f"Released {released} expired holds.")
