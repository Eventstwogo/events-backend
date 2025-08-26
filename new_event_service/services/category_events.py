from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_event_service.services.event_fetcher import EventTypeStatus, get_event_conditions
from shared.db.models import Category, EventStatus, NewEvent, SubCategory


async def fetch_categories_with_all_events(
    db: AsyncSession,
    event_type: EventTypeStatus = EventTypeStatus.ALL,
) -> List[Dict]:
    """Fetch all categories with their latest 5 events each, including events from subcategories

    This function groups all events under their parent categories, regardless of whether
    they have subcategories or not. Events from subcategories are included under their
    parent category.

    Args:
        db: Database session
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date
    """

    # Get current date for filtering
    current_date = date.today()

    # Base filter: only ACTIVE events
    base_conditions = [NewEvent.event_status == EventStatus.ACTIVE]

    # Unpack conditions + alias from helper
    base_conditions.extend(get_event_conditions(event_type))

    # Get all categories that have events (either directly or through subcategories)
    categories_query = (
        select(Category)
        .join(NewEvent, Category.category_id == NewEvent.category_id)
        .where(and_(*base_conditions))
        .distinct()
        .order_by(Category.category_name)
    )

    result = await db.execute(categories_query)
    categories = list(result.scalars().all())

    categories_data = []

    for category in categories:
        # Get latest 5 events for this category (including events from subcategories)
        # Apply the same filtering conditions
        events_conditions = [
            NewEvent.category_id == category.category_id,
            *base_conditions,
        ]

        events_query = (
            select(NewEvent)
            .where(and_(*events_conditions))
            .order_by(desc(NewEvent.created_at))
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
                    "event_type": event.event_type,
                    "event_dates": event.event_dates,
                    "location": event.location,
                    "is_online": event.is_online,
                    "card_image": event.card_image,
                    "event_status": event.event_status,
                    "featured_event": event.featured_event,
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


async def fetch_events_by_category_slug_unified(
    db: AsyncSession,
    slug: str,
    page: int = 1,
    limit: int = 10,
    event_type: EventTypeStatus = EventTypeStatus.ALL,
) -> Tuple[List[Dict], Optional[int], Optional[Dict]]:
    """Fetch paginated events by category slug or subcategory slug,
    always returning under category context

    This function unifies the response to always show events under their parent category:
    - If slug matches a category: returns all events from that category
      (including subcategory events)
    - If slug matches a subcategory: returns events from that subcategory
      under parent category context

    Args:
        db: Database session
        slug: Category slug or subcategory slug
        page: Page number (1-based)
        limit: Number of events per page
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date

    Returns:
        Tuple containing:
        - List of events data
        - Total count of events
        - Category data (always returned, never None if events found)
    """

    offset = (page - 1) * limit

    # Base filter: only ACTIVE events
    base_conditions = [NewEvent.event_status == EventStatus.ACTIVE]

    # Unpack conditions + alias from helper
    base_conditions.extend(get_event_conditions(event_type))

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

    if category:
        # Fetch all events by category (including events from subcategories)
        # Apply the same filtering conditions
        events_conditions = [
            NewEvent.category_id == category.category_id,
            *base_conditions,
        ]

        events_query = (
            select(NewEvent)
            .where(and_(*events_conditions))
            .order_by(desc(NewEvent.created_at))
            .offset(offset)
            .limit(limit)
        )

        # Count query for all category events (including subcategory events)
        count_query = select(func.count(NewEvent.event_id)).where(
            and_(*events_conditions)
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
        # Fetch events by subcategory but present under parent category context
        # Apply the same filtering conditions
        events_conditions = [
            NewEvent.subcategory_id == subcategory.subcategory_id,
            *base_conditions,
        ]

        events_query = (
            select(NewEvent)
            .where(and_(*events_conditions))
            .order_by(desc(NewEvent.created_at))
            .offset(offset)
            .limit(limit)
        )

        # Count query for subcategory events
        count_query = select(func.count(NewEvent.event_id)).where(
            and_(*events_conditions)
        )

        events_result = await db.execute(events_query)
        events = list(events_result.scalars().all())

        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        # Prepare parent category data (not subcategory data)
        category_data = {
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
                "event_dates": event.event_dates,
                "location": event.location,
                "is_online": event.is_online,
                "event_status": event.event_status,
                "featured_event": event.featured_event,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
            }
        )

    return events_data, total_count, category_data
