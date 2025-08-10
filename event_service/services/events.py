from datetime import date, datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, Category, Event, EventSlot, SubCategory

logger = get_logger(__name__)


async def check_event_exists_with_slug(
    db: AsyncSession, event_slug: str
) -> bool:
    query = select(Event).filter(Event.event_slug == event_slug)
    result = await db.execute(query)
    return result.scalars().first() is not None


async def check_event_exists_with_title(
    db: AsyncSession, event_title: str
) -> bool:
    query = select(Event).filter(
        func.lower(Event.event_title) == event_title.lower()
    )
    result = await db.execute(query)
    return result.scalars().first() is not None


async def check_event_exists(db: AsyncSession, event_id: str) -> Event | None:
    query = select(Event).filter(Event.event_id == event_id)
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_event_by_id(db: AsyncSession, event_id: str) -> Event | None:
    query = select(Event).filter(Event.event_id == event_id)
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_event_by_slug(
    db: AsyncSession, event_slug: str
) -> Event | None:
    query = select(Event).filter(Event.event_slug == event_slug)
    result = await db.execute(query)
    return result.scalars().first()


async def check_organizer_exists(
    db: AsyncSession, organizer_id: str
) -> AdminUser | None:
    query = select(AdminUser).filter(AdminUser.user_id == organizer_id)
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_organizer_by_id(
    db: AsyncSession, organizer_id: str
) -> AdminUser | None:
    query = select(AdminUser).filter(AdminUser.user_id == organizer_id)
    result = await db.execute(query)
    return result.scalars().first()


async def check_category_exists(
    db: AsyncSession, category_id: str
) -> Category | None:
    query = select(Category).filter(Category.category_id == category_id)
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_category_by_id(
    db: AsyncSession, category_id: str
) -> Category | None:
    query = select(Category).filter(Category.category_id == category_id)
    result = await db.execute(query)
    return result.scalars().first()


async def check_subcategory_exists(
    db: AsyncSession, subcategory_id: str
) -> SubCategory | None:
    query = select(SubCategory).filter(
        SubCategory.subcategory_id == subcategory_id
    )
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_subcategory_by_id(
    db: AsyncSession, subcategory_id: str
) -> SubCategory | None:
    query = select(SubCategory).filter(
        SubCategory.subcategory_id == subcategory_id
    )
    result = await db.execute(query)
    return result.scalars().first()


async def check_category_and_subcategory_exists_using_joins(
    db: AsyncSession, category_id: str, subcategory_id: str
) -> Tuple[Category, SubCategory] | None:
    query = (
        select(Category, SubCategory)
        .select_from(Category)
        .join(SubCategory, Category.category_id == SubCategory.category_id)
        .where(
            and_(
                Category.category_id == category_id,
                SubCategory.subcategory_id == subcategory_id,
            )
        )
    )
    result = await db.execute(query)
    row = result.first()
    return tuple(row) if row else None


async def fetch_category_or_subcategory_data(
    db: AsyncSession,
    category_id: Optional[str] = None,
    subcategory_id: Optional[str] = None,
) -> Tuple[Optional[Category], Optional[SubCategory]] | None:
    if not category_id and not subcategory_id:
        return None

    category = None
    subcategory = None

    # Fetch category if category_id is provided
    if category_id:
        category_query = select(Category).where(
            Category.category_id == category_id
        )
        category_result = await db.execute(category_query)
        category = category_result.scalars().first()

    # Fetch subcategory if subcategory_id is provided
    if subcategory_id:
        subcategory_query = select(SubCategory).where(
            SubCategory.subcategory_id == subcategory_id
        )
        subcategory_result = await db.execute(subcategory_query)
        subcategory = subcategory_result.scalars().first()

    # Return tuple even if one or both are None
    return (category, subcategory)


async def fetch_event_by_id_using_joins(
    db: AsyncSession, event_id: str
) -> Event | None:
    query = (
        select(Event)
        .join(AdminUser, Event.organizer_id == AdminUser.user_id)
        .join(Category, Event.category_id == Category.category_id)
        .join(SubCategory, Event.subcategory_id == SubCategory.subcategory_id)
        .filter(Event.event_id == event_id)
    )
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_event_by_slug_with_relations(
    db: AsyncSession, event_slug: str
) -> Event | None:
    """Fetch event by slug with all related entities loaded"""
    query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
            selectinload(Event.slots),
        )
        .filter(Event.event_slug == event_slug)
    )
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_event_by_id_with_relations(
    db: AsyncSession, event_id: str
) -> Event | None:
    """Fetch event by ID with all related entities loaded"""
    query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
            selectinload(Event.slots),
        )
        .filter(Event.event_id == event_id)
    )
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_events_without_filters(
    db: AsyncSession,
) -> Tuple[List[Event], int]:
    """Fetch events with filtering, pagination, and sorting"""

    # Build base query with relations
    query = select(Event).options(
        selectinload(Event.category),
        selectinload(Event.subcategory),
        selectinload(Event.organizer),
    )

    # Get total count
    count_query = select(func.count(Event.event_id))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())
    total = total if total is not None else 0

    return events, total


async def fetch_limited_events_without_filters(
    db: AsyncSession,
) -> Tuple[List[Event], int]:
    """Fetch events with filtering, pagination, and sorting"""

    # Build base query with relations
    query = select(Event).options(
        selectinload(Event.category),
        selectinload(Event.subcategory),
        selectinload(Event.organizer),
    )

    # Get total count
    count_query = select(func.count(Event.event_id))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())
    total = total if total is not None else 0

    return events, total


async def fetch_upcoming_events(
    db: AsyncSession,
) -> Tuple[List[Event], int]:
    """
    Fetch upcoming events based on start_date and end_date.
    Returns events where:
    - start_date >= today (events starting today or in the future)
    - OR end_date >= today (events that are still ongoing)
    - Only active events (event_status = false)
    """
    today = date.today()

    # Build base query with relations
    query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
        )
        .filter(
            and_(
                # Only active events (event_status = false means published/active)
                Event.event_status == False,
                # Events that are upcoming or ongoing
                or_(
                    Event.start_date >= today,  # Events starting today or later
                    Event.end_date >= today,  # Events that are still ongoing
                ),
            )
        )
        .order_by(asc(Event.start_date))
    )  # Order by start date ascending

    # Get total count with same filters
    count_query = select(func.count(Event.event_id)).filter(
        and_(
            Event.event_status == False,
            or_(Event.start_date >= today, Event.end_date >= today),
        )
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())
    total = total if total is not None else 0

    return events, total


async def fetch_limited_events_with_filter(
    db: AsyncSession, event_type: str = "all"
) -> Tuple[List[Event], int]:
    """
    Fetch limited events based on event_type filter.

    Args:
        db: Database session
        event_type: "all" for all events, "upcoming" for upcoming events only

    Returns:
        Tuple of (events_list, total_count)
    """
    today = date.today()

    # Build base query with relations
    query = select(Event).options(
        selectinload(Event.category),
        selectinload(Event.subcategory),
        selectinload(Event.organizer),
    )

    # Build count query
    count_query = select(func.count(Event.event_id))

    # Apply filters based on event_type
    if event_type == "upcoming":
        # Filter for upcoming events only
        filters = and_(
            # Only active events (event_status = false means published/active)
            Event.event_status == False,
            # Events that are upcoming or ongoing
            or_(
                Event.start_date >= today,  # Events starting today or later
                Event.end_date >= today,  # Events that are still ongoing
            ),
        )
        query = query.filter(filters).order_by(asc(Event.start_date))
        count_query = count_query.filter(filters)
    else:
        # For "all" or any other value, return all events
        query = query.order_by(desc(Event.created_at))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute main query
    result = await db.execute(query)
    events = list(result.scalars().all())
    total = total if total is not None else 0

    return events, total


async def update_event(
    db: AsyncSession, event_id: str, update_data: dict
) -> Event | None:
    """Update event with provided data"""
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return None

    # Update only provided fields
    for field, value in update_data.items():
        if hasattr(event, field) and value is not None:
            setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return event


async def update_event_status(
    db: AsyncSession, event_id: str, status: bool
) -> Event | None:
    """Update event status"""
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return None

    event.event_status = status
    await db.commit()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event_id: str) -> bool:
    """Delete event and cascade delete slots"""
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return False

    # Delete the event (slots will be cascade deleted due to relationship configuration)
    await db.delete(event)
    await db.commit()
    return True


async def check_event_title_unique_for_update(
    db: AsyncSession, event_id: str, event_title: str
) -> bool:
    """Check if event title is unique excluding the current event"""
    query = select(Event).filter(
        and_(
            func.lower(Event.event_title) == event_title.lower(),
            Event.event_id != event_id,
        )
    )
    result = await db.execute(query)
    return result.scalars().first() is None


async def check_event_slug_unique_for_update(
    db: AsyncSession, event_id: str, event_slug: str
) -> bool:
    """Check if event slug is unique excluding the current event"""
    query = select(Event).filter(
        and_(Event.event_slug == event_slug.lower(), Event.event_id != event_id)
    )
    result = await db.execute(query)
    return result.scalars().first() is None


async def search_events(
    db: AsyncSession,
    query: str,
    search_fields: List[str] = ["title", "slug", "hashtags"],
    page: int = 1,
    per_page: int = 10,
    status: Optional[bool] = None,
    category_id: Optional[str] = None,
    subcategory_id: Optional[str] = None,
) -> Tuple[List[Event], int]:
    """Advanced search for events across multiple fields"""

    # Build base query with relations
    base_query = select(Event).options(
        selectinload(Event.category),
        selectinload(Event.subcategory),
        selectinload(Event.organizer),
    )

    # Build search conditions
    search_conditions = []
    search_term = f"%{query.lower()}%"

    if "title" in search_fields:
        search_conditions.append(Event.event_title.ilike(search_term))

    if "slug" in search_fields:
        search_conditions.append(Event.event_slug.ilike(search_term))

    if "hashtags" in search_fields:
        # Search in hashtags JSON array
        search_conditions.append(
            func.jsonb_array_elements_text(Event.hash_tags).op("ILIKE")(
                search_term
            )
        )

    if "organizer" in search_fields:
        # Join with AdminUser table to search organizer name
        base_query = base_query.join(
            AdminUser, Event.organizer_id == AdminUser.user_id
        )
        search_conditions.extend(
            [
                AdminUser.username_hash.ilike(f"%{search_term}%"),
            ]
        )

    # Combine search conditions with OR
    if search_conditions:
        base_query = base_query.filter(or_(*search_conditions))

    # Apply additional filters
    filters = []

    if status is not None:
        filters.append(Event.event_status == status)

    if category_id:
        filters.append(Event.category_id == category_id)

    if subcategory_id:
        filters.append(Event.subcategory_id == subcategory_id)

    if filters:
        base_query = base_query.filter(and_(*filters))

    # Get total count
    count_query = select(func.count(Event.event_id))
    if search_conditions:
        count_query = count_query.filter(or_(*search_conditions))
    if filters:
        count_query = count_query.filter(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * per_page
    base_query = (
        base_query.order_by(desc(Event.created_at))
        .offset(offset)
        .limit(per_page)
    )

    # Execute query
    result = await db.execute(base_query)
    events = list(result.scalars().all())

    return events, total


async def fetch_events_by_slug_comprehensive(
    db: AsyncSession, slug: str, page: int = 1, per_page: int = 10
) -> Tuple[List[Event], dict, int, int, Optional[str], Optional[str]]:
    """
    Comprehensive slug-based event fetching that checks both category and subcategory tables.

    When searching by category slug, returns:
    - Category events (events with only category_id, no subcategory_id)
    - Subcategory events grouped by subcategory (events with subcategory_id under this category)

    Args:
        db: Database session
        slug: The slug to search for in both category and subcategory tables
        page: Page number for pagination
        per_page: Items per page

    Returns:
        Tuple containing:
        - List[Event]: Category events (events with only category_id, no subcategory_id)
        - dict: Subcategory events grouped by subcategory_id with subcategory info
        - int: Total category events count
        - int: Total subcategory events count
        - Optional[str]: Matched category_id (if slug found in category table)
        - Optional[str]: Matched subcategory_id (if slug found in subcategory table)
    """

    slug_lower = slug.lower()
    category_events = []
    subcategory_events_grouped = {}
    total_category_events = 0
    total_subcategory_events = 0
    matched_category_id = None
    matched_subcategory_id = None

    # Calculate offset for pagination
    offset = (page - 1) * per_page

    # Step 1: Check if slug exists in category table
    category_query = select(Category).filter(
        Category.category_slug == slug_lower
    )
    category_result = await db.execute(category_query)
    category = category_result.scalars().first()

    if category:
        matched_category_id = category.category_id

        # Get events that belong to this category but have NO subcategory (category_id only)
        category_events_query = (
            select(Event)
            .options(
                selectinload(Event.category),
                selectinload(Event.subcategory),
                selectinload(Event.organizer),
                selectinload(Event.slots),
            )
            .filter(Event.category_id == category.category_id)
            .filter(
                Event.subcategory_id.is_(None)
            )  # Only events without subcategory
            .filter(Event.event_status.is_(False))  # Only active events
            .order_by(desc(Event.created_at))
            .offset(offset)
            .limit(per_page)
        )

        category_events_result = await db.execute(category_events_query)
        category_events = list(category_events_result.scalars().all())

        # Get total count for category events (only those without subcategory)
        category_count_query = (
            select(func.count(Event.event_id))
            .filter(Event.category_id == category.category_id)
            .filter(
                Event.subcategory_id.is_(None)
            )  # Only events without subcategory
            .filter(Event.event_status.is_(False))
        )
        category_count_result = await db.execute(category_count_query)
        total_category_events = category_count_result.scalar() or 0

        # Get ALL subcategory events for this category, grouped by subcategory
        subcategory_events_query = (
            select(Event)
            .options(
                selectinload(Event.category),
                selectinload(Event.subcategory),
                selectinload(Event.organizer),
                selectinload(Event.slots),
            )
            .filter(Event.category_id == category.category_id)
            .filter(
                Event.subcategory_id.is_not(None)
            )  # Only events WITH subcategory
            .filter(Event.event_status.is_(False))  # Only active events
            .order_by(desc(Event.created_at))
        )

        subcategory_events_result = await db.execute(subcategory_events_query)
        all_subcategory_events = list(subcategory_events_result.scalars().all())

        # Group events by subcategory
        for event in all_subcategory_events:
            # Skip events without subcategory (shouldn't happen due to filter, but safety check)
            if not event.subcategory_id or not event.subcategory:
                continue

            if event.subcategory_id not in subcategory_events_grouped:
                subcategory_events_grouped[event.subcategory_id] = {
                    "subcategory_info": {
                        "subcategory_id": event.subcategory.subcategory_id,
                        "subcategory_slug": event.subcategory.subcategory_slug,
                        "subcategory_name": getattr(
                            event.subcategory, "subcategory_name", None
                        ),
                    },
                    "events": [],
                    "total": 0,
                }
            subcategory_events_grouped[event.subcategory_id]["events"].append(
                event
            )

        # Get total count for each subcategory
        for subcategory_id in subcategory_events_grouped.keys():
            subcategory_count_query = (
                select(func.count(Event.event_id))
                .filter(Event.subcategory_id == subcategory_id)
                .filter(Event.event_status.is_(False))
            )
            subcategory_count_result = await db.execute(subcategory_count_query)
            count = subcategory_count_result.scalar() or 0
            subcategory_events_grouped[subcategory_id]["total"] = count
            total_subcategory_events += count

    # Step 2: Check if slug exists in subcategory table
    subcategory_query = select(SubCategory).filter(
        SubCategory.subcategory_slug == slug_lower
    )
    subcategory_result = await db.execute(subcategory_query)
    subcategory = subcategory_result.scalars().first()

    if subcategory:
        matched_subcategory_id = subcategory.subcategory_id

        # Get all events for this specific subcategory
        subcategory_events_query = (
            select(Event)
            .options(
                selectinload(Event.category),
                selectinload(Event.subcategory),
                selectinload(Event.organizer),
                selectinload(Event.slots),
            )
            .filter(Event.subcategory_id == subcategory.subcategory_id)
            .filter(Event.event_status.is_(False))  # Only active events
            .order_by(desc(Event.created_at))
            .offset(offset)
            .limit(per_page)
        )

        subcategory_events_result = await db.execute(subcategory_events_query)
        events = list(subcategory_events_result.scalars().all())

        # Get total count for subcategory events
        subcategory_count_query = (
            select(func.count(Event.event_id))
            .filter(Event.subcategory_id == subcategory.subcategory_id)
            .filter(Event.event_status.is_(False))
        )
        subcategory_count_result = await db.execute(subcategory_count_query)
        total_subcategory_events = subcategory_count_result.scalar() or 0

        # Group this single subcategory's events
        subcategory_events_grouped[subcategory.subcategory_id] = {
            "subcategory_info": {
                "subcategory_id": subcategory.subcategory_id,
                "subcategory_slug": subcategory.subcategory_slug,
                "subcategory_name": getattr(
                    subcategory, "subcategory_name", None
                ),
            },
            "events": events,
            "total": total_subcategory_events,
        }

    return (
        category_events,
        subcategory_events_grouped,
        total_category_events,
        total_subcategory_events,
        matched_category_id,
        matched_subcategory_id,
    )


async def fetch_events_by_category_or_subcategory_slug(
    db: AsyncSession,
    slug: str,
    page: int = 1,
    per_page: int = 10,
    event_type: str = "all",
) -> Tuple[List[Event], int, Optional[str], bool]:
    """Fetch events by category slug or subcategory slug with all related entities loaded

    Args:
        db: Database session
        slug: Category slug or subcategory slug
        page: Page number (1-based)
        per_page: Number of events per page
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date
    """

    # Calculate offset for pagination
    offset = (page - 1) * per_page

    # Get current date for filtering
    current_date = date.today()

    # Build base event filter conditions
    base_conditions: List[Any] = [
        Event.event_status.is_(False)
    ]  # Only published events

    # Add date-based filtering conditions
    if event_type == "ongoing":
        # Events where current date is between start_date and end_date (inclusive)
        base_conditions.extend(
            [Event.start_date <= current_date, Event.end_date >= current_date]
        )
    elif event_type == "upcoming":
        # Events where end_date is greater than or equal to current date
        base_conditions.append(Event.end_date >= current_date)
    # For 'all', no additional date filtering is needed

    # First try to find events by category slug (active events only)
    category_conditions = [
        Category.category_slug == slug.lower(),
        *base_conditions,
    ]

    category_query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
            selectinload(Event.slots),
        )
        .join(Category, Event.category_id == Category.category_id)
        .filter(and_(*category_conditions))
        .order_by(desc(Event.created_at))
        .offset(offset)
        .limit(per_page)
    )

    category_result = await db.execute(category_query)
    category_events = list(category_result.scalars().all())

    if category_events:
        # Get total count for category (active events only)
        count_query = (
            select(func.count(Event.event_id))
            .join(Category, Event.category_id == Category.category_id)
            .filter(and_(*category_conditions))
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        return category_events, total, slug, True

    # If no events found by category slug, check if category exists at all
    category_exists_query = select(Category).filter(
        Category.category_slug == slug.lower()
    )
    category_exists_result = await db.execute(category_exists_query)
    category_exists = category_exists_result.scalars().first() is not None

    if category_exists:
        # Category exists but no active events, return empty result
        return [], 0, slug, True

    # If category doesn't exist, try subcategory slug (active events only)
    subcategory_conditions = [
        SubCategory.subcategory_slug == slug.lower(),
        *base_conditions,
    ]

    subcategory_query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
            selectinload(Event.slots),
        )
        .join(SubCategory, Event.subcategory_id == SubCategory.subcategory_id)
        .filter(and_(*subcategory_conditions))
        .order_by(desc(Event.created_at))
        .offset(offset)
        .limit(per_page)
    )

    subcategory_result = await db.execute(subcategory_query)
    subcategory_events = list(subcategory_result.scalars().all())

    # Get total count for subcategory (active events only)
    count_query = (
        select(func.count(Event.event_id))
        .join(SubCategory, Event.subcategory_id == SubCategory.subcategory_id)
        .filter(and_(*subcategory_conditions))
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return subcategory_events, total, slug, False


async def filter_events_advanced(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 10,
    status: Optional[bool] = None,
    category_id: Optional[str] = None,
    subcategory_id: Optional[str] = None,
    organizer_id: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    has_slots: Optional[bool] = None,
    min_slots: Optional[int] = None,
    max_slots: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[Event], int]:
    """Advanced filtering for events with date ranges and slot counts"""

    # Build base query with relations
    query = select(Event).options(
        selectinload(Event.category),
        selectinload(Event.subcategory),
        selectinload(Event.organizer),
        selectinload(Event.slots),
    )

    # Apply filters
    filters = []

    if status is not None:
        filters.append(Event.event_status == status)

    if category_id:
        filters.append(Event.category_id == category_id)

    if subcategory_id:
        filters.append(Event.subcategory_id == subcategory_id)

    if organizer_id:
        filters.append(Event.organizer_id == organizer_id)

    if created_after:
        filters.append(Event.created_at >= created_after)

    if created_before:
        filters.append(Event.created_at <= created_before)

    # Slot-based filters require subqueries
    if has_slots is not None or min_slots is not None or max_slots is not None:

        slot_count_subquery = (
            select(func.count(EventSlot.slot_id))
            .filter(EventSlot.slot_id == Event.slot_id)
            .scalar_subquery()
        )

        if has_slots is not None:
            if has_slots:
                filters.append(slot_count_subquery > 0)
            else:
                filters.append(slot_count_subquery == 0)

        if min_slots is not None:
            filters.append(slot_count_subquery >= min_slots)

        if max_slots is not None:
            filters.append(slot_count_subquery <= max_slots)

    if filters:
        query = query.filter(and_(*filters))

    # Get total count
    count_query = select(func.count(Event.event_id))
    if filters:
        count_query = count_query.filter(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(Event, sort_by, Event.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())

    return events, total


async def get_events_by_organizer(
    db: AsyncSession,
    organizer_id: str,
    page: int = 1,
    per_page: int = 10,
    status: Optional[bool] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[Event], int, dict]:
    """Get events by organizer with statistics"""

    # Build base query
    query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
            selectinload(Event.slots),
        )
        .filter(Event.organizer_id == organizer_id)
    )

    # Apply status filter if provided
    filters = []
    if status is not None:
        filters.append(Event.event_status == status)

    if filters:
        query = query.filter(and_(*filters))

    # Get statistics
    total_query = select(func.count(Event.event_id)).filter(
        Event.organizer_id == organizer_id
    )
    active_query = select(func.count(Event.event_id)).filter(
        and_(Event.organizer_id == organizer_id, Event.event_status.is_(True))
    )

    total_result = await db.execute(total_query)
    active_result = await db.execute(active_query)

    total_events = total_result.scalar() or 0
    active_events = active_result.scalar() or 0
    inactive_events = total_events - active_events

    stats = {
        "total_events": total_events,
        "active_events": active_events,
        "inactive_events": inactive_events,
    }

    # Apply sorting
    sort_column = getattr(Event, sort_by, Event.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())

    # Get filtered total for pagination
    filtered_total_query = select(func.count(Event.event_id)).filter(
        Event.organizer_id == organizer_id
    )
    if filters:
        filtered_total_query = filtered_total_query.filter(and_(*filters))

    filtered_total_result = await db.execute(filtered_total_query)
    filtered_total = filtered_total_result.scalar() or 0

    return events, filtered_total, stats


async def get_event_summary(db: AsyncSession, event_id: str) -> dict | None:
    """Get comprehensive event summary with analytics"""

    # Get event with all relations
    event = await fetch_event_by_id_with_relations(db, event_id)
    if not event:
        return None

    # Get slot statistics
    from event_service.services.slots import get_slot_statistics

    slot_stats = await get_slot_statistics(db, event_id)

    # Calculate engagement metrics
    hashtag_count = len(event.hash_tags) if event.hash_tags else 0
    has_card_image = bool(event.card_image)
    has_banner_image = bool(event.banner_image)
    has_extra_data = bool(event.extra_data)

    return {
        "event_id": event.event_id,
        "event_title": event.event_title,
        "event_status": event.event_status,
        "organizer_id": event.organizer_id,
        "category_id": event.category_id,
        "subcategory_id": event.subcategory_id,
        "total_slots": slot_stats["total_slots"],
        "active_slots": slot_stats["active_slots"],
        "inactive_slots": slot_stats["inactive_slots"],
        "hashtag_count": hashtag_count,
        "has_card_image": has_card_image,
        "has_banner_image": has_banner_image,
        "has_extra_data": has_extra_data,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


async def get_upcoming_events(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 10,
    category_id: Optional[str] = None,
    subcategory_id: Optional[str] = None,
) -> Tuple[List[Event], int]:
    """Get upcoming published events"""

    # Build query for published events only
    query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
        )
        .filter(Event.event_status.is_(True))
    )

    # Apply additional filters
    filters = []

    if category_id:
        filters.append(Event.category_id == category_id)

    if subcategory_id:
        filters.append(Event.subcategory_id == subcategory_id)

    if filters:
        query = query.filter(and_(*filters))

    # Get total count
    count_query = select(func.count(Event.event_id)).filter(
        Event.event_status.is_(True)
    )
    if filters:
        count_query = count_query.filter(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by creation date (most recent first)
    query = query.order_by(desc(Event.created_at))

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())

    return events, total


async def get_events_by_hashtag(
    db: AsyncSession,
    hashtag: str,
    page: int = 1,
    per_page: int = 10,
    status: Optional[bool] = None,
) -> Tuple[List[Event], int]:
    """Find events by hashtag"""

    # Ensure hashtag starts with #
    if not hashtag.startswith("#"):
        hashtag = f"#{hashtag}"

    # Build query
    query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
        )
        .filter(
            Event.hash_tags.op("@>")([hashtag])
        )  # PostgreSQL JSONB contains operator
    )

    # Apply status filter if provided
    if status is not None:
        query = query.filter(Event.event_status == status)

    # Get total count
    count_query = select(func.count(Event.event_id)).filter(
        Event.hash_tags.op("@>")([hashtag])
    )
    if status is not None:
        count_query = count_query.filter(Event.event_status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by creation date (most recent first)
    query = query.order_by(desc(Event.created_at))

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())

    return events, total


async def fetch_latest_event_from_each_category(
    db: AsyncSession,
    event_type: str = "all",
) -> Tuple[List[Event], int]:
    """Fetch the latest event from each category

    Args:
        db: Database session
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date
    """

    # Get current date for filtering
    current_date = date.today()

    # Build base event filter conditions
    base_conditions: List[Any] = [
        Event.event_status.is_(False)
    ]  # Only published events

    # Add date-based filtering conditions
    if event_type == "ongoing":
        # Events where current date is between start_date and end_date (inclusive)
        base_conditions.extend(
            [Event.start_date <= current_date, Event.end_date >= current_date]
        )
    elif event_type == "upcoming":
        # Events where end_date is greater than or equal to current date
        base_conditions.append(Event.end_date >= current_date)
    # For 'all', no additional date filtering is needed

    # Subquery to get the latest event_id for each category
    latest_events_subquery = (
        select(
            Event.category_id,
            func.max(Event.created_at).label("max_created_at"),
        )
        .where(and_(*base_conditions))
        .group_by(Event.category_id)
        .subquery()
    )

    # Main query to get the actual events
    query = (
        select(Event)
        .join(
            latest_events_subquery,
            and_(
                Event.category_id == latest_events_subquery.c.category_id,
                Event.created_at == latest_events_subquery.c.max_created_at,
            ),
        )
        .where(and_(*base_conditions))  # Apply the same filtering conditions
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
        )
        .order_by(Event.created_at.desc())
    )

    # Execute query
    result = await db.execute(query)
    events = list(result.scalars().all())
    total = len(events)

    return events, total


async def update_event_slug(
    db: AsyncSession, event_id: str, new_slug: str
) -> Event | None:
    """Update event slug"""

    # Check if new slug is unique
    if not await check_event_slug_unique_for_update(db, event_id, new_slug):
        return None

    # Update the event
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return None

    event.event_slug = new_slug.lower()
    await db.commit()
    await db.refresh(event)
    return event
