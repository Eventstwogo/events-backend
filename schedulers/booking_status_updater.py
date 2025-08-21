from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.logging_config import get_logger
from shared.db.models.new_events import (
    BookingStatus,
    NewEventBooking,
    NewEventBookingOrder,
    NewEventSeatCategory,
    PaymentStatus,
)
from shared.db.sessions.database import AsyncSessionLocal

logger = get_logger(__name__)

HOLD_DURATION_MINUTES = 15  # configurable


async def backfill_held_counts(db: AsyncSession):
    """
    Recalculate 'held' seats for all seat categories based on active PROCESSING orders.
    Fixes pre-existing inconsistencies.
    """
    result = await db.execute(select(NewEventSeatCategory))
    seat_categories = result.scalars().all()

    for cat in seat_categories:
        # Sum all seats currently held in active PROCESSING orders
        held_result = await db.execute(
            select(func.sum(NewEventBooking.num_seats))
            .join(
                NewEventBookingOrder,
                NewEventBooking.order_id == NewEventBookingOrder.order_id,
            )
            .where(
                NewEventBooking.seat_category_ref_id == cat.seat_category_id,
                NewEventBookingOrder.booking_status == BookingStatus.PROCESSING,
            )
        )
        total_held = held_result.scalar() or 0
        cat.held = total_held
        db.add(cat)

    await db.commit()
    logger.info("Backfilled seat category held counts successfully.")


async def release_expired_holds(db: AsyncSession) -> int:
    """
    Release seats for orders that are still PROCESSING beyond the hold duration.
    Updates order status to CANCELLED/FAILED and decrements seat_category.held counts.
    Returns: number of line items released.
    """
    now = datetime.now(timezone.utc)
    expiry_time = now - timedelta(minutes=HOLD_DURATION_MINUTES)

    # Step 1: Find expired orders
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

    # Step 2: Release seats for each line item
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
        db.add(order)

    await db.commit()
    return released_count


async def release_seat_category_hold(
    db: AsyncSession,
    seat_category_id: str,
    num_seats: int,
):
    """
    Decrement held seats for a specific seat category when a booking expires.
    Ensures held does not go below 0.
    """
    result = await db.execute(
        select(NewEventSeatCategory).where(
            NewEventSeatCategory.seat_category_id == seat_category_id
        )
    )
    seat_category = result.scalar_one_or_none()

    if not seat_category:
        return  # Invalid reference, skip

    seat_category.held = max(0, seat_category.held - num_seats)
    db.add(seat_category)
    await db.flush()


async def cleanup_job():
    async with AsyncSessionLocal() as db:
        # Step 0: Backfill existing data to fix inconsistencies
        await backfill_held_counts(db)

        # Step 1: Release expired holds
        released = await release_expired_holds(db)
        if released:
            logger.info(f"Released {released} expired holds.")
