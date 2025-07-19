from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.logging_config import get_logger
from shared.db.models import Category, Event, SubCategory, User

logger = get_logger(__name__)


# Utility functions for admin/DevOps
async def check_database_health(db: AsyncSession) -> bool:
    """Check database connectivity and health"""
    try:
        # Simple query to test database connection
        result = await db.execute(select(func.count(Event.event_id)))
        result.scalar()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def get_event_metrics(db: AsyncSession) -> dict:
    """Get comprehensive event metrics for admin dashboard"""

    # Basic event counts
    total_events_query = select(func.count(Event.event_id))
    published_events_query = select(func.count(Event.event_id)).filter(
        Event.event_status == True
    )
    draft_events_query = select(func.count(Event.event_id)).filter(
        Event.event_status == False
    )

    total_events_result = await db.execute(total_events_query)
    published_events_result = await db.execute(published_events_query)
    draft_events_result = await db.execute(draft_events_query)

    total_events = total_events_result.scalar() or 0
    published_events = published_events_result.scalar() or 0
    draft_events = draft_events_result.scalar() or 0

    # Slot metrics
    from shared.db.models import EventSlot

    total_slots_query = select(func.count(EventSlot.slot_ids))
    active_slots_query = select(func.count(EventSlot.slot_ids)).filter(
        EventSlot.slot_status == True
    )
    inactive_slots_query = select(func.count(EventSlot.slot_ids)).filter(
        EventSlot.slot_status == False
    )

    total_slots_result = await db.execute(total_slots_query)
    active_slots_result = await db.execute(active_slots_query)
    inactive_slots_result = await db.execute(inactive_slots_query)

    total_slots = total_slots_result.scalar() or 0
    active_slots = active_slots_result.scalar() or 0
    inactive_slots = inactive_slots_result.scalar() or 0

    # Category distribution
    category_query = (
        select(
            Category.category_name, func.count(Event.event_id).label("count")
        )
        .join(Event, Category.category_id == Event.category_id)
        .group_by(Category.category_name)
    )

    category_result = await db.execute(category_query)
    events_by_category = {
        row.category_name: row.count for row in category_result
    }

    # Subcategory distribution
    subcategory_query = (
        select(
            SubCategory.subcategory_name,
            func.count(Event.event_id).label("count"),
        )
        .join(Event, SubCategory.subcategory_id == Event.subcategory_id)
        .group_by(SubCategory.subcategory_name)
    )

    subcategory_result = await db.execute(subcategory_query)
    events_by_subcategory = {
        row.subcategory_name: row.count for row in subcategory_result
    }

    # Organizer metrics
    total_organizers_query = select(
        func.count(func.distinct(Event.organizer_id))
    )
    total_organizers_result = await db.execute(total_organizers_query)
    total_organizers = total_organizers_result.scalar() or 0

    # Fetch complete User objects
    top_organizers_query = (
        select(User, func.count(Event.event_id).label("event_count"))
        .join(Event, Event.organizer_id == User.user_id)
        .group_by(User.user_id)
        .order_by(func.count(Event.event_id).desc())
        .limit(10)
    )

    top_organizers_result = await db.execute(top_organizers_query)
    top_organizers = [
        {
            "organizer_id": row.User.user_id,
            "username": row.User.username,  # This uses the property to get decrypted value
            "first_name": row.User.first_name,  # This uses the property to get decrypted value
            "last_name": row.User.last_name,  # This uses the property to get decrypted value
            "event_count": row.event_count,
        }
        for row in top_organizers_result
    ]

    # Time-based metrics
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Events created today
    today_query = select(func.count(Event.event_id)).filter(
        Event.created_at >= today_start
    )
    today_result = await db.execute(today_query)
    events_created_today = today_result.scalar() or 0

    # Events created this week
    week_query = select(func.count(Event.event_id)).filter(
        Event.created_at >= week_start
    )
    week_result = await db.execute(week_query)
    events_created_this_week = week_result.scalar() or 0

    # Events created this month
    month_query = select(func.count(Event.event_id)).filter(
        Event.created_at >= month_start
    )
    month_result = await db.execute(month_query)
    events_created_this_month = month_result.scalar() or 0

    # Engagement metrics
    hashtags_query = select(func.count(Event.event_id)).filter(
        and_(
            Event.hash_tags.isnot(None),
            func.jsonb_array_length(Event.hash_tags) > 0,
        )
    )
    hashtags_result = await db.execute(hashtags_query)
    events_with_hashtags = hashtags_result.scalar() or 0

    images_query = select(func.count(Event.event_id)).filter(
        or_(Event.card_image.isnot(None), Event.banner_image.isnot(None))
    )
    images_result = await db.execute(images_query)
    events_with_images = images_result.scalar() or 0

    extra_data_query = select(func.count(Event.event_id)).filter(
        Event.extra_data.isnot(None)
    )
    extra_data_result = await db.execute(extra_data_query)
    events_with_extra_data = extra_data_result.scalar() or 0

    return {
        "total_events": total_events,
        "published_events": published_events,
        "draft_events": draft_events,
        "total_slots": total_slots,
        "active_slots": active_slots,
        "inactive_slots": inactive_slots,
        "events_by_category": events_by_category,
        "events_by_subcategory": events_by_subcategory,
        "total_organizers": total_organizers,
        "top_organizers": top_organizers,
        "events_created_today": events_created_today,
        "events_created_this_week": events_created_this_week,
        "events_created_this_month": events_created_this_month,
        "events_with_hashtags": events_with_hashtags,
        "events_with_images": events_with_images,
        "events_with_extra_data": events_with_extra_data,
        "generated_at": datetime.utcnow(),
    }
