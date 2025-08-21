from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.logging_config import get_logger
from shared.db.models.coupons import Coupon
from shared.db.sessions.database import AsyncSessionLocal

logger = get_logger(__name__)

# Configurable hold duration for coupons
COUPON_HOLD_MINUTES = 15


async def release_expired_coupons(db: AsyncSession) -> int:
    """
    Release applied coupons that have not been converted to sold
    within COUPON_HOLD_MINUTES.
    Returns: number of coupons released.
    """
    now = datetime.now(timezone.utc)
    expiry_time = now - timedelta(minutes=COUPON_HOLD_MINUTES)

    # Fetch coupons that have applied > sold (means some are still on hold)
    result = await db.execute(
        select(Coupon).where(
            Coupon.applied_coupons > Coupon.sold_coupons,
            Coupon.updated_at <= expiry_time,
        )
    )
    coupons = result.scalars().all()

    if not coupons:
        return 0

    released_count = 0

    for coupon in coupons:
        # Reset applied_coupons back to sold_coupons count
        # (meaning, only finalized sales remain)
        released = coupon.applied_coupons - coupon.sold_coupons
        coupon.applied_coupons = coupon.sold_coupons
        released_count += released

    await db.commit()
    return released_count


async def cleanup_expired_coupons():
    async with AsyncSessionLocal() as db:
        released = await release_expired_coupons(db)
        if released:
            logger.info(
                f"[Coupon Cleanup] Released {released} expired applied coupons."
            )
