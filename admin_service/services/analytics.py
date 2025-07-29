from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Sequence, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import AdminUser, Category, Config, Event, User


async def get_admin_user_analytics(
    db: AsyncSession,
) -> Row[Tuple[int, Any, Any, Any, Any, Any, Any, datetime, datetime]]:
    now = datetime.now(timezone.utc)
    threshold_180 = now - timedelta(days=180)

    results = await db.execute(
        select(
            func.count().label("total_users"),
            func.sum(case((AdminUser.is_deleted.is_(False), 1), else_=0)).label(
                "active_users"
            ),
            func.sum(case((AdminUser.is_deleted.is_(True), 1), else_=0)).label(
                "inactive_users"
            ),
            func.sum(case((AdminUser.login_status == 1, 1), else_=0)).label(
                "locked_users"
            ),
            func.sum(
                case((AdminUser.days_180_flag.is_(True), 1), else_=0)
            ).label("with_expiry_flag"),
            func.sum(
                case(
                    (
                        AdminUser.days_180_flag.is_(True),
                        case(
                            (AdminUser.days_180_timestamp < threshold_180, 1),
                            else_=0,
                        ),
                    ),
                    else_=0,
                )
            ).label("expired_passwords"),
            func.sum(
                case((AdminUser.failure_login_attempts >= 3, 1), else_=0)
            ).label("high_failed_attempts"),
            func.min(AdminUser.created_at).label("earliest_user"),
            func.max(AdminUser.created_at).label("latest_user"),
        )
    )
    return results.one()


async def get_daily_registrations(
    db: AsyncSession, days: int = 30
) -> Sequence[Row[Tuple[Any, int]]]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    results = await db.execute(
        select(
            func.date(AdminUser.created_at).label("date"),
            func.count().label("count"),
        )
        .where(AdminUser.created_at >= start)
        .group_by(func.date(AdminUser.created_at))
        .order_by(func.date(AdminUser.created_at))
    )
    return results.all()


async def get_dashboard_analytics(db: AsyncSession) -> Dict[str, Any]:
    """
    Get comprehensive dashboard analytics including categories, users, revenue, and settings.

    Returns:
        Dict containing analytics data for dashboard display
    """
    now = datetime.now(timezone.utc)

    # Calculate time periods
    current_month_start = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    current_week_start = now - timedelta(days=now.weekday())
    last_week_start = current_week_start - timedelta(days=7)

    # Get categories analytics
    categories_data = await _get_categories_analytics(
        db, current_month_start, last_month_start
    )

    # Get admin users analytics
    admin_users_data = await _get_admin_users_analytics(
        db, current_week_start, last_week_start
    )

    # Get users analytics
    users_data = await _get_users_analytics(
        db, current_week_start, last_week_start
    )

    # Get revenue analytics (placeholder - implement when payment system is added)
    revenue_data = await _get_revenue_analytics(
        db, current_month_start, last_month_start
    )

    # Get settings analytics
    settings_data = await _get_settings_analytics(
        db, current_week_start, last_week_start
    )

    return {
        "categories": categories_data,
        "admin_users": admin_users_data,
        "users": users_data,
        "revenue": revenue_data,
        "settings": settings_data,
        "generated_at": now.isoformat(),
    }


async def _get_categories_analytics(
    db: AsyncSession, current_month_start: datetime, last_month_start: datetime
) -> Dict[str, Any]:
    """Get categories analytics data."""

    # Get total categories count
    total_result = await db.execute(
        select(func.count(Category.category_id)).where(
            Category.category_status.is_(False)
        )
    )
    total_categories = total_result.scalar() or 0

    # Get categories added this month
    current_month_result = await db.execute(
        select(func.count(Category.category_id)).where(
            Category.category_tstamp >= current_month_start,
            Category.category_status.is_(False),
        )
    )
    current_month_count = current_month_result.scalar() or 0

    # Get categories added last month
    last_month_result = await db.execute(
        select(func.count(Category.category_id)).where(
            Category.category_tstamp >= last_month_start,
            Category.category_tstamp < current_month_start,
            Category.category_status.is_(False),
        )
    )
    last_month_count = last_month_result.scalar() or 0

    # Calculate percentage change
    if last_month_count > 0:
        percentage_change = (
            (current_month_count - last_month_count) / last_month_count
        ) * 100
    else:
        percentage_change = 100.0 if current_month_count > 0 else 0.0

    return {
        "total": total_categories,
        "added_this_month": current_month_count,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }


async def _get_admin_users_analytics(
    db: AsyncSession, current_week_start: datetime, last_week_start: datetime
) -> Dict[str, Any]:
    """Get users analytics data."""

    # Get total active users count
    total_result = await db.execute(
        select(func.count(AdminUser.user_id)).where(
            AdminUser.is_deleted.is_(False)
        )
    )
    total_users = total_result.scalar() or 0

    # Get users added this week
    current_week_result = await db.execute(
        select(func.count(AdminUser.user_id)).where(
            AdminUser.created_at >= current_week_start,
            AdminUser.is_deleted.is_(False),
        )
    )
    current_week_count = current_week_result.scalar() or 0

    # Get users added last week
    last_week_result = await db.execute(
        select(func.count(AdminUser.user_id)).where(
            AdminUser.created_at >= last_week_start,
            AdminUser.created_at < current_week_start,
            AdminUser.is_deleted.is_(False),
        )
    )
    last_week_count = last_week_result.scalar() or 0

    # Calculate percentage change
    if last_week_count > 0:
        percentage_change = (
            (current_week_count - last_week_count) / last_week_count
        ) * 100
    else:
        percentage_change = 100.0 if current_week_count > 0 else 0.0

    return {
        "total": total_users,
        "added_this_week": current_week_count,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }


async def _get_users_analytics(
    db: AsyncSession, current_week_start: datetime, last_week_start: datetime
) -> Dict[str, Any]:
    """Get users analytics data."""

    # Get total active users count
    total_result = await db.execute(
        select(func.count(User.user_id)).where(User.is_deleted.is_(False))
    )
    total_users = total_result.scalar() or 0

    # Get users added this week
    current_week_result = await db.execute(
        select(func.count(User.user_id)).where(
            User.created_at >= current_week_start, User.is_deleted.is_(False)
        )
    )
    current_week_count = current_week_result.scalar() or 0

    # Get users added last week
    last_week_result = await db.execute(
        select(func.count(User.user_id)).where(
            User.created_at >= last_week_start,
            User.created_at < current_week_start,
            User.is_deleted.is_(False),
        )
    )
    last_week_count = last_week_result.scalar() or 0

    # Calculate percentage change
    if last_week_count > 0:
        percentage_change = (
            (current_week_count - last_week_count) / last_week_count
        ) * 100
    else:
        percentage_change = 100.0 if current_week_count > 0 else 0.0

    return {
        "total": total_users,
        "added_this_week": current_week_count,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }


async def _get_revenue_analytics(
    db: AsyncSession, current_month_start: datetime, last_month_start: datetime
) -> Dict[str, Any]:
    """
    Get revenue analytics data.

    Note: This is a placeholder implementation since no payment/revenue tables exist yet.
    When payment system is implemented, this should be updated to query actual revenue data.
    """

    # Placeholder implementation - calculate estimated revenue based on events
    # This assumes each event generates some revenue (replace with actual payment data)

    # Get events created this month (as proxy for revenue)
    current_month_events = await db.execute(
        select(func.count(Event.event_id)).where(
            Event.created_at >= current_month_start,
            Event.event_status.is_(False),
        )
    )
    current_month_count = current_month_events.scalar() or 0

    # Get events created last month
    last_month_events = await db.execute(
        select(func.count(Event.event_id)).where(
            Event.created_at >= last_month_start,
            Event.created_at < current_month_start,
            Event.event_status.is_(False),
        )
    )
    last_month_count = last_month_events.scalar() or 0

    # Placeholder revenue calculation (replace with actual revenue queries)
    estimated_revenue_per_event = 150.0  # Average revenue per event
    current_month_revenue = current_month_count * estimated_revenue_per_event
    last_month_revenue = last_month_count * estimated_revenue_per_event

    # Calculate percentage change
    if last_month_revenue > 0:
        percentage_change = (
            (current_month_revenue - last_month_revenue) / last_month_revenue
        ) * 100
    else:
        percentage_change = 100.0 if current_month_revenue > 0 else 0.0

    revenue_difference = current_month_revenue - last_month_revenue

    return {
        "current_month": current_month_revenue,
        "last_month": last_month_revenue,
        "difference": revenue_difference,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
        "note": "Estimated revenue based on events. "
        "Implement actual payment tracking for accurate data.",
    }


async def _get_settings_analytics(
    db: AsyncSession, current_week_start: datetime, last_week_start: datetime
) -> Dict[str, Any]:
    """Get system settings analytics data."""

    # Get total configurations count
    total_result = await db.execute(select(func.count(Config.id)))
    total_configs = total_result.scalar() or 0

    # Get configurations updated this week
    current_week_result = await db.execute(
        select(func.count(Config.id)).where(
            Config.updated_at >= current_week_start
        )
    )
    current_week_changes = current_week_result.scalar() or 0

    # Get configurations updated last week
    last_week_result = await db.execute(
        select(func.count(Config.id)).where(
            Config.updated_at >= last_week_start,
            Config.updated_at < current_week_start,
        )
    )
    last_week_changes = last_week_result.scalar() or 0

    # Calculate percentage change
    if last_week_changes > 0:
        percentage_change = (
            (current_week_changes - last_week_changes) / last_week_changes
        ) * 100
    else:
        percentage_change = 100.0 if current_week_changes > 0 else 0.0

    return {
        "total": total_configs,
        "changes_this_week": current_week_changes,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }
