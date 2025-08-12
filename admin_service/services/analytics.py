from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import case, desc, func, select
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import (
    AdminUser,
    BusinessProfile,
    Category,
    Config,
    ContactUs,
    ContactUsStatus,
    Event,
    EventBooking,
    OrganizerQuery,
    QueryStatus,
    User,
)
from shared.db.models.events import BookingStatus


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

    # Get events analytics
    events_data = await _get_events_analytics(
        db, current_month_start, last_month_start
    )

    # Get organizer analytics
    organizers_data = await _get_organizers_analytics(
        db, current_month_start, last_month_start
    )

    # Get queries analytics
    queries_data = await _get_queries_analytics(
        db, current_week_start, last_week_start
    )

    # Get contact us analytics
    contact_us_data = await _get_contact_us_analytics(
        db, current_week_start, last_week_start
    )

    return {
        "categories": categories_data,
        "admin_users": admin_users_data,
        "users": users_data,
        "events": events_data,
        "organizers": organizers_data,
        "revenue": revenue_data,
        "queries": queries_data,
        "contact_us": contact_us_data,
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
    Get revenue analytics data based on approved bookings with completed payments.

    Filters bookings by:
    - booking_status = APPROVED
    - payment_status = APPROVED (completed payments)
    """

    # Get current month revenue from approved bookings with completed payments
    current_month_result = await db.execute(
        select(func.coalesce(func.sum(EventBooking.total_price), 0)).where(
            EventBooking.created_at >= current_month_start,
            EventBooking.booking_status == BookingStatus.APPROVED,
            EventBooking.payment_status == "COMPLETED",
        )
    )
    current_month_revenue = float(current_month_result.scalar() or 0)

    # Get last month revenue from approved bookings with completed payments
    last_month_result = await db.execute(
        select(func.coalesce(func.sum(EventBooking.total_price), 0)).where(
            EventBooking.created_at >= last_month_start,
            EventBooking.created_at < current_month_start,
            EventBooking.booking_status == BookingStatus.APPROVED,
            EventBooking.payment_status == "COMPLETED",
        )
    )
    last_month_revenue = float(last_month_result.scalar() or 0)

    # Calculate percentage change
    if last_month_revenue > 0:
        percentage_change = (
            (current_month_revenue - last_month_revenue) / last_month_revenue
        ) * 100
    else:
        percentage_change = 100.0 if current_month_revenue > 0 else 0.0

    # Calculate revenue difference
    revenue_difference = current_month_revenue - last_month_revenue

    # Determine trend
    if percentage_change > 0:
        trend = "up"
    elif percentage_change < 0:
        trend = "down"
    else:
        trend = "stable"

    return {
        "current_month": round(current_month_revenue, 2),
        "last_month": round(last_month_revenue, 2),
        "difference": round(revenue_difference, 2),
        "percentage_change": round(percentage_change, 1),
        "trend": trend,
        "note": "Revenue from approved bookings with completed payments.",
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


async def _get_events_analytics(
    db: AsyncSession, current_month_start: datetime, last_month_start: datetime
) -> Dict[str, Any]:
    """Get events analytics data."""

    # Get total active events count
    total_result = await db.execute(
        select(func.count(Event.event_id)).where(Event.event_status.is_(False))
    )
    total_events = total_result.scalar() or 0

    # Get events created this month
    current_month_result = await db.execute(
        select(func.count(Event.event_id)).where(
            Event.created_at >= current_month_start,
            Event.event_status.is_(False),
        )
    )
    current_month_count = current_month_result.scalar() or 0

    # Get events created last month
    last_month_result = await db.execute(
        select(func.count(Event.event_id)).where(
            Event.created_at >= last_month_start,
            Event.created_at < current_month_start,
            Event.event_status.is_(False),
        )
    )
    last_month_count = last_month_result.scalar() or 0

    # Get total bookings
    total_bookings_result = await db.execute(
        select(func.count(EventBooking.booking_id))
    )
    total_bookings = total_bookings_result.scalar() or 0

    # Calculate percentage change
    if last_month_count > 0:
        percentage_change = (
            (current_month_count - last_month_count) / last_month_count
        ) * 100
    else:
        percentage_change = 100.0 if current_month_count > 0 else 0.0

    return {
        "total": total_events,
        "total_bookings": total_bookings,
        "added_this_month": current_month_count,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }


async def _get_organizers_analytics(
    db: AsyncSession, current_month_start: datetime, last_month_start: datetime
) -> Dict[str, Any]:
    """Get organizers analytics data."""

    # Get total business profiles
    total_result = await db.execute(select(func.count(BusinessProfile.sno)))
    total_organizers = total_result.scalar() or 0

    # Get approved organizers
    approved_result = await db.execute(
        select(func.count(BusinessProfile.sno)).where(
            BusinessProfile.is_approved == 1
        )
    )
    approved_organizers = approved_result.scalar() or 0

    # Get pending organizers
    pending_result = await db.execute(
        select(func.count(BusinessProfile.sno)).where(
            BusinessProfile.is_approved == 0
        )
    )
    pending_organizers = pending_result.scalar() or 0

    # Get organizers registered this month
    current_month_result = await db.execute(
        select(func.count(BusinessProfile.sno)).where(
            BusinessProfile.timestamp >= current_month_start
        )
    )
    current_month_count = current_month_result.scalar() or 0

    # Get organizers registered last month
    last_month_result = await db.execute(
        select(func.count(BusinessProfile.sno)).where(
            BusinessProfile.timestamp >= last_month_start,
            BusinessProfile.timestamp < current_month_start,
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
        "total": total_organizers,
        "approved": approved_organizers,
        "pending": pending_organizers,
        "registered_this_month": current_month_count,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }


async def _get_queries_analytics(
    db: AsyncSession, current_week_start: datetime, last_week_start: datetime
) -> Dict[str, Any]:
    """Get queries analytics data."""

    # Get total queries count
    total_result = await db.execute(select(func.count(OrganizerQuery.id)))
    total_queries = total_result.scalar() or 0

    # Get resolved queries
    resolved_result = await db.execute(
        select(func.count(OrganizerQuery.id)).where(
            OrganizerQuery.query_status == QueryStatus.QUERY_ANSWERED
        )
    )
    resolved_queries = resolved_result.scalar() or 0

    # Get pending queries
    pending_result = await db.execute(
        select(func.count(OrganizerQuery.id)).where(
            OrganizerQuery.query_status.in_(
                [QueryStatus.QUERY_OPEN, QueryStatus.QUERY_IN_PROGRESS]
            )
        )
    )
    pending_queries = pending_result.scalar() or 0

    # Get queries created this week
    current_week_result = await db.execute(
        select(func.count(OrganizerQuery.id)).where(
            OrganizerQuery.created_at >= current_week_start
        )
    )
    current_week_count = current_week_result.scalar() or 0

    # Get queries created last week
    last_week_result = await db.execute(
        select(func.count(OrganizerQuery.id)).where(
            OrganizerQuery.created_at >= last_week_start,
            OrganizerQuery.created_at < current_week_start,
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
        "total": total_queries,
        "resolved": resolved_queries,
        "pending": pending_queries,
        "created_this_week": current_week_count,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }


async def _get_contact_us_analytics(
    db: AsyncSession, current_week_start: datetime, last_week_start: datetime
) -> Dict[str, Any]:
    """Get contact us analytics data."""

    # Get total contact us submissions
    total_result = await db.execute(select(func.count(ContactUs.contact_us_id)))
    total_contacts = total_result.scalar() or 0

    # Get resolved contact us submissions
    resolved_result = await db.execute(
        select(func.count(ContactUs.contact_us_id)).where(
            ContactUs.contact_us_status == ContactUsStatus.RESOLVED
        )
    )
    resolved_contacts = resolved_result.scalar() or 0

    # Get pending contact us submissions
    pending_result = await db.execute(
        select(func.count(ContactUs.contact_us_id)).where(
            ContactUs.contact_us_status.in_(
                [ContactUsStatus.PENDING, ContactUsStatus.IN_PROGRESS]
            )
        )
    )
    pending_contacts = pending_result.scalar() or 0

    # Get contact us submissions this week
    current_week_result = await db.execute(
        select(func.count(ContactUs.contact_us_id)).where(
            ContactUs.created_at >= current_week_start
        )
    )
    current_week_count = current_week_result.scalar() or 0

    # Get contact us submissions last week
    last_week_result = await db.execute(
        select(func.count(ContactUs.contact_us_id)).where(
            ContactUs.created_at >= last_week_start,
            ContactUs.created_at < current_week_start,
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
        "total": total_contacts,
        "resolved": resolved_contacts,
        "pending": pending_contacts,
        "submitted_this_week": current_week_count,
        "percentage_change": round(percentage_change, 1),
        "trend": (
            "up"
            if percentage_change > 0
            else "down" if percentage_change < 0 else "stable"
        ),
    }


async def get_recent_queries(
    db: AsyncSession, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent queries for dashboard display."""

    result = await db.execute(
        select(
            OrganizerQuery.id,
            OrganizerQuery.title,
            OrganizerQuery.category,
            OrganizerQuery.query_status,
            OrganizerQuery.created_at,
            OrganizerQuery.updated_at,
        )
        .order_by(desc(OrganizerQuery.created_at))
        .limit(limit)
    )

    queries = result.all()

    return [
        {
            "id": query.id,
            "title": query.title,
            "category": query.category,
            "status": (
                query.query_status.value if query.query_status else "unknown"
            ),
            "created_at": (
                query.created_at.isoformat() if query.created_at else None
            ),
            "updated_at": (
                query.updated_at.isoformat() if query.updated_at else None
            ),
        }
        for query in queries
    ]


async def get_recent_contact_us(
    db: AsyncSession, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent contact us submissions for dashboard display."""

    result = await db.execute(
        select(
            ContactUs.contact_us_id,
            ContactUs.firstname,
            ContactUs.lastname,
            ContactUs.email,
            ContactUs.contact_us_status,
            ContactUs.created_at,
        )
        .order_by(desc(ContactUs.created_at))
        .limit(limit)
    )

    contacts = result.all()

    return [
        {
            "id": contact.contact_us_id,
            "name": f"{contact.firstname} {contact.lastname}",
            "email": contact.email,
            "status": (
                contact.contact_us_status.value
                if contact.contact_us_status
                else "unknown"
            ),
            "created_at": (
                contact.created_at.isoformat() if contact.created_at else None
            ),
        }
        for contact in contacts
    ]


async def get_system_health(db: AsyncSession) -> Dict[str, Any]:
    """Get system health status."""

    try:
        # Test database connection
        await db.execute(select(1))
        database_status = "connected"
    except Exception:
        database_status = "disconnected"

    # Get latest backup info (placeholder - implement based on your backup strategy)
    # This could query a backup_logs table or check file system
    last_backup = "Not configured"  # Replace with actual backup check

    # API services status (always running if this function executes)
    api_status = "running"

    # Overall status
    overall_status = "online" if database_status == "connected" else "degraded"

    return {
        "database": database_status,
        "api_services": api_status,
        "last_backup": last_backup,
        "overall_status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
