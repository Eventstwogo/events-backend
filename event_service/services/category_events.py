from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.logging_config import get_logger
from shared.db.models import Category, Event, SubCategory

logger = get_logger(__name__)


async def fetch_categories_with_latest_events(
    db: AsyncSession,
) -> List[Dict]:
    """Fetch all categories that have events, with their latest 5 events each

    Note: Only includes events that don't have a subcategory assigned.
    Events with subcategories will appear in the subcategories list instead.
    This prevents duplicate events in the response.
    """

    # First, get all categories that have at least one published event without subcategory
    categories_query = (
        select(Category)
        .join(Event, Category.category_id == Event.category_id)
        .where(
            and_(
                Event.event_status
                == False,  # Only published events (False = published)
                Event.subcategory_id.is_(
                    None
                ),  # Only events without subcategory
            )
        )
        .distinct()
        .order_by(Category.category_name)
    )

    result = await db.execute(categories_query)
    categories = list(result.scalars().all())

    categories_data = []

    for category in categories:
        # Get latest 5 events for this category that don't have a subcategory
        events_query = (
            select(Event)
            .where(
                and_(
                    Event.category_id == category.category_id,
                    Event.event_status
                    == False,  # Only published events (False = published)
                    Event.subcategory_id.is_(
                        None
                    ),  # Only events without subcategory
                )
            )
            .order_by(desc(Event.created_at))
            .limit(5)
        )

        events_result = await db.execute(events_query)
        events = list(events_result.scalars().all())

        # Convert events to the format expected by the schema
        events_data = []
        for event in events:
            events_data.append(
                {
                    "event_id": event.event_id,
                    "event_title": event.event_title,
                    "event_slug": event.event_slug,
                    "card_image": event.card_image,
                    "event_status": event.event_status,
                }
            )

        # Only include categories that have events
        if events_data:
            category_data = {
                "category_id": category.category_id,
                "category_name": category.category_name,
                "category_slug": category.category_slug,
                "events": events_data,
                "events_count": len(events_data),
            }
            categories_data.append(category_data)

    return categories_data


async def fetch_subcategories_with_latest_events(
    db: AsyncSession,
) -> List[Dict]:
    """Fetch all subcategories that have events, with their latest 5 events each

    Note: This includes all events that have a subcategory assigned, regardless of
    whether they also have a category. This ensures events with subcategories
    appear only in the subcategories list, not in both lists.
    """

    # First, get all subcategories that have at least one published event
    subcategories_query = (
        select(SubCategory)
        .join(Event, SubCategory.subcategory_id == Event.subcategory_id)
        .join(Category, SubCategory.category_id == Category.category_id)
        .where(
            Event.event_status == False
        )  # Only published events (False = published)
        .distinct()
        .order_by(SubCategory.subcategory_name)
        .options(selectinload(SubCategory.category))
    )

    result = await db.execute(subcategories_query)
    subcategories = list(result.scalars().all())

    subcategories_data = []

    for subcategory in subcategories:
        # Get latest 5 events for this subcategory
        events_query = (
            select(Event)
            .where(
                and_(
                    Event.subcategory_id == subcategory.subcategory_id,
                    Event.event_status
                    == False,  # Only published events (False = published)
                )
            )
            .order_by(desc(Event.created_at))
            .limit(5)
        )

        events_result = await db.execute(events_query)
        events = list(events_result.scalars().all())

        # Convert events to the format expected by the schema
        events_data = []
        for event in events:
            events_data.append(
                {
                    "event_id": event.event_id,
                    "event_title": event.event_title,
                    "event_slug": event.event_slug,
                    "card_image": event.card_image,
                    "event_status": event.event_status,
                }
            )

        # Only include subcategories that have events
        if events_data:
            subcategory_data = {
                "subcategory_id": subcategory.subcategory_id,
                "subcategory_name": subcategory.subcategory_name,
                "subcategory_slug": subcategory.subcategory_slug,
                "category_id": subcategory.category.category_id,
                "category_name": subcategory.category.category_name,
                "category_slug": subcategory.category.category_slug,
                "events": events_data,
                "events_count": len(events_data),
            }
            subcategories_data.append(subcategory_data)

    return subcategories_data


async def fetch_events_by_category_or_subcategory_slug(
    db: AsyncSession,
    slug: str,
    page: int = 1,
    limit: int = 10,
) -> Tuple[List[Dict], Optional[int], Optional[Dict], Optional[Dict]]:
    """Fetch paginated events by category slug or subcategory slug in descending order of created_at

    Args:
        db: Database session
        slug: Category slug or subcategory slug
        page: Page number (1-based)
        limit: Number of events per page

    Returns:
        Tuple containing:
        - List of events data
        - Total count of events
        - Category data (if found by category slug)
        - Subcategory data (if found by subcategory slug)
    """

    offset = (page - 1) * limit

    # First, try to find by category slug
    category_query = select(Category).where(Category.category_slug == slug)
    category_result = await db.execute(category_query)
    category = category_result.scalar_one_or_none()

    # Then, try to find by subcategory slug
    subcategory_query = (
        select(SubCategory)
        .where(SubCategory.subcategory_slug == slug)
        .options(selectinload(SubCategory.category))
    )
    subcategory_result = await db.execute(subcategory_query)
    subcategory = subcategory_result.scalar_one_or_none()

    events_data = []
    events = []
    total_count = 0
    category_data = None
    subcategory_data = None

    if category:
        # Fetch events by category (only events without subcategory to avoid duplicates)
        events_query = (
            select(Event)
            .where(
                and_(
                    Event.category_id == category.category_id,
                    Event.event_status
                    == False,  # Only published events (False = published)
                    Event.subcategory_id.is_(
                        None
                    ),  # Only events without subcategory
                )
            )
            .order_by(desc(Event.created_at))
            .offset(offset)
            .limit(limit)
        )

        # Count query for category events
        count_query = select(func.count(Event.event_id)).where(
            and_(
                Event.category_id == category.category_id,
                Event.event_status == False,
                Event.subcategory_id.is_(None),
            )
        )

        events_result = await db.execute(events_query)
        events = list(events_result.scalars().all())

        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        # Prepare category data
        category_data = {
            "category_id": category.category_id,
            "category_name": category.category_name,
            "category_slug": category.category_slug,
        }

    elif subcategory:
        # Fetch events by subcategory
        events_query = (
            select(Event)
            .where(
                and_(
                    Event.subcategory_id == subcategory.subcategory_id,
                    Event.event_status
                    == False,  # Only published events (False = published)
                )
            )
            .order_by(desc(Event.created_at))
            .offset(offset)
            .limit(limit)
        )

        # Count query for subcategory events
        count_query = select(func.count(Event.event_id)).where(
            and_(
                Event.subcategory_id == subcategory.subcategory_id,
                Event.event_status == False,
            )
        )

        events_result = await db.execute(events_query)
        events = list(events_result.scalars().all())

        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        # Prepare subcategory data
        subcategory_data = {
            "subcategory_id": subcategory.subcategory_id,
            "subcategory_name": subcategory.subcategory_name,
            "subcategory_slug": subcategory.subcategory_slug,
            "category_id": subcategory.category.category_id,
            "category_name": subcategory.category.category_name,
            "category_slug": subcategory.category.category_slug,
        }

    # Convert events to the format expected by the schema
    for event in events:
        events_data.append(
            {
                "event_id": event.event_id,
                "event_title": event.event_title,
                "event_slug": event.event_slug,
                "card_image": event.card_image,
                "event_status": event.event_status,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
            }
        )

    return events_data, total_count, category_data, subcategory_data
