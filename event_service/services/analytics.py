from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, Event, EventSlot, Role

logger = get_logger(__name__)


async def fetch_organizer_events_analytics(db: AsyncSession) -> Dict:
    """
    Fetch analytics for all organizer-created events.
    No user authentication required - returns system-wide organizer analytics.
    """

    # Get all events created by organizers
    events_query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer).selectinload(AdminUser.role),
            selectinload(Event.slots),
        )
        .join(AdminUser, Event.organizer_id == AdminUser.user_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
        .order_by(desc(Event.created_at))
    )
    events_result = await db.execute(events_query)
    events = list(events_result.scalars().all())

    # Calculate analytics for all organizer events
    analytics = calculate_events_analytics(events)

    # Get organizer statistics
    organizer_stats_query = (
        select(
            AdminUser.user_id,
            AdminUser.username_hash,
            func.count(Event.event_id).label("event_count"),
        )
        .join(Event, AdminUser.user_id == Event.organizer_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
        .group_by(AdminUser.user_id, AdminUser.username_hash)
        .order_by(desc("event_count"))
        .limit(10)
    )
    organizer_stats_result = await db.execute(organizer_stats_query)
    top_organizers = [
        {
            "organizer_id": row.user_id,
            "username_hash": row.username_hash,
            "event_count": row.event_count,
        }
        for row in organizer_stats_result
    ]

    # Get total organizers count
    total_organizers_query = (
        select(func.count(AdminUser.user_id))
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
    )
    total_organizers_result = await db.execute(total_organizers_query)
    total_organizers = total_organizers_result.scalar() or 0

    return {
        "events_analytics": analytics["events_analytics"],
        "slots_analytics": analytics["slots_analytics"],
        "organizer_statistics": {
            "total_organizers": total_organizers,
            "top_organizers": top_organizers,
        },
    }


async def fetch_admin_events_analytics(db: AsyncSession) -> Dict:
    """
    Fetch comprehensive analytics for all events in the system.
    No user authentication required - returns system-wide analytics.
    Separates organizer-created and admin-created events.
    """

    # Get all events with organizer and role information
    all_events_query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer).selectinload(AdminUser.role),
            selectinload(Event.slots),
        )
        .order_by(desc(Event.created_at))
    )
    all_events_result = await db.execute(all_events_query)
    all_events = list(all_events_result.scalars().all())

    # Separate events by creator role
    organizer_events = []
    admin_events = []

    for event in all_events:
        if (
            event.organizer
            and event.organizer.role.role_name.lower() == "organizer"
        ):
            organizer_events.append(event)
        else:
            admin_events.append(event)

    # Calculate analytics for different categories
    organizer_analytics = calculate_events_analytics(organizer_events)
    admin_analytics = calculate_events_analytics(admin_events)
    overall_analytics = calculate_events_analytics(all_events)

    # Get comprehensive user statistics
    # Total users by role
    user_stats_query = (
        select(
            Role.role_name, func.count(AdminUser.user_id).label("user_count")
        )
        .join(AdminUser, Role.role_id == AdminUser.role_id)
        .group_by(Role.role_name)
    )
    user_stats_result = await db.execute(user_stats_query)
    users_by_role = {row.role_name: row.user_count for row in user_stats_result}

    # Top organizers by event count
    top_organizers_query = (
        select(
            AdminUser.user_id,
            AdminUser.username_hash,
            func.count(Event.event_id).label("event_count"),
        )
        .join(Event, AdminUser.user_id == Event.organizer_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
        .group_by(AdminUser.user_id, AdminUser.username_hash)
        .order_by(desc("event_count"))
        .limit(10)
    )
    top_organizers_result = await db.execute(top_organizers_query)
    top_organizers = [
        {
            "organizer_id": row.user_id,
            "username_hash": row.username_hash,
            "event_count": row.event_count,
        }
        for row in top_organizers_result
    ]

    # Top admins by event count
    top_admins_query = (
        select(
            AdminUser.user_id,
            AdminUser.username_hash,
            func.count(Event.event_id).label("event_count"),
        )
        .join(Event, AdminUser.user_id == Event.organizer_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("admin"))
        .group_by(AdminUser.user_id, AdminUser.username_hash)
        .order_by(desc("event_count"))
        .limit(10)
    )
    top_admins_result = await db.execute(top_admins_query)
    top_admins = [
        {
            "admin_id": row.user_id,
            "username_hash": row.username_hash,
            "event_count": row.event_count,
        }
        for row in top_admins_result
    ]

    return {
        "overall_analytics": {
            "events_analytics": overall_analytics["events_analytics"],
            "slots_analytics": overall_analytics["slots_analytics"],
        },
        "organizer_created_analytics": {
            "events_analytics": organizer_analytics["events_analytics"],
            "slots_analytics": organizer_analytics["slots_analytics"],
        },
        "admin_created_analytics": {
            "events_analytics": admin_analytics["events_analytics"],
            "slots_analytics": admin_analytics["slots_analytics"],
        },
        "user_statistics": {
            "users_by_role": users_by_role,
            "top_organizers": top_organizers,
            "top_admins": top_admins,
        },
    }


def calculate_events_analytics(events: List[Event]) -> Dict:
    """
    Helper function to calculate analytics for a list of events.
    """
    total_events = len(events)
    active_events = len([e for e in events if not e.event_status])
    draft_events = len([e for e in events if e.event_status])

    # Calculate upcoming and past events
    today = date.today()
    upcoming_events = len(
        [
            e
            for e in events
            if not e.event_status
            and (e.start_date >= today or e.end_date >= today)
        ]
    )

    past_events = len(
        [e for e in events if not e.event_status and e.end_date < today]
    )

    # Calculate slots analytics
    total_slots = 0
    active_slots = 0
    draft_slots = 0

    for event in events:
        for slot in event.slots:
            total_slots += 1
            if slot.slot_status:
                draft_slots += 1
            else:
                active_slots += 1

    # Get events by category
    events_by_category = {}
    for event in events:
        if event.category:
            category_name = event.category.category_name
            if category_name not in events_by_category:
                events_by_category[category_name] = {
                    "total": 0,
                    "active": 0,
                    "draft": 0,
                }
            events_by_category[category_name]["total"] += 1
            if event.event_status:
                events_by_category[category_name]["draft"] += 1
            else:
                events_by_category[category_name]["active"] += 1

    # Get events by month (last 12 months)
    events_by_month = {}
    for event in events:
        month_key = event.created_at.strftime("%Y-%m")
        if month_key not in events_by_month:
            events_by_month[month_key] = 0
        events_by_month[month_key] += 1

    return {
        "events_analytics": {
            "total_events": total_events,
            "active_events": active_events,
            "draft_events": draft_events,
            "upcoming_events": upcoming_events,
            "past_events": past_events,
            "events_by_category": events_by_category,
            "events_by_month": events_by_month,
        },
        "slots_analytics": {
            "total_slots": total_slots,
            "active_slots": active_slots,
            "draft_slots": draft_slots,
        },
    }


async def fetch_event_statistics(db: AsyncSession) -> Dict:
    """
    Fetch simple event statistics including active events, upcoming events,
    and monthly growth percentage.
    """
    logger.info("Fetching event statistics")

    # Get current date and calculate date ranges
    today = date.today()
    current_month_start = today.replace(day=1)

    # Calculate previous month start and end
    if current_month_start.month == 1:
        previous_month_start = current_month_start.replace(
            year=current_month_start.year - 1, month=12
        )
    else:
        previous_month_start = current_month_start.replace(
            month=current_month_start.month - 1
        )

    # Get active events count (event_status = False means active)
    active_events_query = select(func.count(Event.event_id)).filter(
        Event.event_status == False
    )
    active_events_result = await db.execute(active_events_query)
    active_events_count = active_events_result.scalar() or 0

    # Get upcoming events count (active events with start_date >= today)
    upcoming_events_query = select(func.count(Event.event_id)).filter(
        and_(Event.event_status == False, Event.start_date >= today)
    )
    upcoming_events_result = await db.execute(upcoming_events_query)
    upcoming_events_count = upcoming_events_result.scalar() or 0

    # Get current month events count
    current_month_events_query = select(func.count(Event.event_id)).filter(
        Event.created_at >= current_month_start
    )
    current_month_events_result = await db.execute(current_month_events_query)
    current_month_events = current_month_events_result.scalar() or 0

    # Get previous month events count
    previous_month_events_query = select(func.count(Event.event_id)).filter(
        and_(
            Event.created_at >= previous_month_start,
            Event.created_at < current_month_start,
        )
    )
    previous_month_events_result = await db.execute(previous_month_events_query)
    previous_month_events = previous_month_events_result.scalar() or 0

    # Calculate monthly growth percentage
    if previous_month_events > 0:
        monthly_growth_percentage = round(
            (
                (current_month_events - previous_month_events)
                / previous_month_events
            )
            * 100,
            2,
        )
    else:
        # If no events in previous month, show 100% if current month has events, else 0%
        monthly_growth_percentage = 100.0 if current_month_events > 0 else 0.0

    logger.info(
        f"Event statistics calculated: active={active_events_count}, upcoming={upcoming_events_count}, growth={monthly_growth_percentage}%"
    )

    return {
        "active_events_count": active_events_count,
        "upcoming_events_count": upcoming_events_count,
        "monthly_growth_percentage": monthly_growth_percentage,
        "current_month_events": current_month_events,
        "previous_month_events": previous_month_events,
    }
