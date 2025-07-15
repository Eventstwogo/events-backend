from datetime import datetime, timedelta, timezone
from typing import Any, Sequence, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import User


async def get_admin_user_analytics(
    db: AsyncSession,
) -> Row[Tuple[int, Any, Any, Any, Any, Any, Any, datetime, datetime]]:
    now = datetime.now(timezone.utc)
    threshold_180 = now - timedelta(days=180)

    results = await db.execute(
        select(
            func.count().label("total_users"),
            func.sum(case((User.is_deleted.is_(False), 1), else_=0)).label("active_users"),
            func.sum(case((User.is_deleted.is_(True), 1), else_=0)).label("inactive_users"),
            func.sum(case((User.login_status == 1, 1), else_=0)).label("locked_users"),
            func.sum(case((User.days_180_flag.is_(True), 1), else_=0)).label(
                "with_expiry_flag"
            ),
            func.sum(
                case(
                    (
                        User.days_180_flag.is_(True),
                        case(
                            (User.days_180_timestamp < threshold_180, 1),
                            else_=0,
                        ),
                    ),
                    else_=0,
                )
            ).label("expired_passwords"),
            func.sum(case((User.failure_login_attempts >= 3, 1), else_=0)).label(
                "high_failed_attempts"
            ),
            func.min(User.created_at).label("earliest_user"),
            func.max(User.created_at).label("latest_user"),
        )
    )
    return results.one()


async def get_daily_registrations(
    db: AsyncSession, days: int = 30
) -> Sequence[Row[Tuple[Any, int]]]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    results = await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count().label("count"),
        )
        .where(User.created_at >= start)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    return results.all()
