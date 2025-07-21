from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, Category, Event, SubCategory

logger = get_logger(__name__)


def apply_active_events_filter(query):
    """
    Apply filtering to get only active events (event_status = false).
    Categories and subcategories are not filtered by status.
    """
    return query.filter(Event.event_status == False)


async def check_event_exists_with_slug(
    db: AsyncSession, event_slug: str
) -> bool:
    query = select(Event).filter(Event.event_slug == event_slug)
    result = await db.execute(query)
    return result.scalars().first() is not None


async def check_event_exists_with_title(
    db: AsyncSession, event_title: str
) -> bool:
    query = select(Event).filter(func.lower(Event.event_title) == event_title.lower())
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
    # Apply active events filtering
    query = apply_active_events_filter(query)
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
    # Apply active events filtering
    query = apply_active_events_filter(query)
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
    
    # Apply active events filtering
    query = apply_active_events_filter(query)

    # Get total count with same filters
    count_query = select(func.count(Event.event_id))
    count_query = apply_active_events_filter(count_query)

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
    
    # Apply active events filtering
    query = apply_active_events_filter(query)

    # Get total count with same filters
    count_query = select(func.count(Event.event_id))
    count_query = apply_active_events_filter(count_query)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute query
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
            func.lower(Event.event_title) == event_title.lower(), Event.event_id != event_id
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
    
    # Apply active events filtering
    base_query = apply_active_events_filter(base_query)

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

    # Note: status filter is now handled by hierarchical filtering
    # if status is not None:
    #     filters.append(Event.event_status == status)

    if category_id:
        filters.append(Event.category_id == category_id)

    if subcategory_id:
        filters.append(Event.subcategory_id == subcategory_id)

    if filters:
        base_query = base_query.filter(and_(*filters))

    # Get total count with active events filtering
    count_query = select(func.count(Event.event_id))
    count_query = apply_active_events_filter(count_query)
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


async def fetch_events_by_category_or_subcategory_slug(
    db: AsyncSession, slug: str, page: int = 1, per_page: int = 10
) -> Tuple[List[Event], int, Optional[List[SubCategory]], bool]:
    """Fetch events by category slug or subcategory slug with all related entities loaded
    
    Returns:
        - events: List of events
        - total: Total count of events
        - subcategories: List of subcategories (only for category slug)
        - is_category: Boolean indicating if the slug is a category slug
    """
    
    # Calculate offset for pagination
    offset = (page - 1) * per_page
    
    # First check if it's a category slug
    category_query = select(Category).filter(Category.category_slug == slug.lower())
    category_result = await db.execute(category_query)
    category = category_result.scalars().first()
    
    if category:  # Proceed regardless of category status
        # It's a category slug - get subcategories and events from all subcategories
        
        # Get subcategories in this category (all subcategories)
        subcategories_query = (
            select(SubCategory)
            .filter(SubCategory.category_id == category.category_id)
            .order_by(SubCategory.subcategory_name)
        )
        subcategories_result = await db.execute(subcategories_query)
        subcategories = list(subcategories_result.scalars().all())
        
        # Get events from all subcategories in this category with active events filtering
        events_query = (
            select(Event)
            .options(
                selectinload(Event.category),
                selectinload(Event.subcategory),
                selectinload(Event.organizer),
                selectinload(Event.slots),
            )
            .join(Category, Event.category_id == Category.category_id)
            .filter(Category.category_slug == slug.lower())
            .order_by(desc(Event.created_at))
            .offset(offset)
            .limit(per_page)
        )
        # Apply active events filtering
        events_query = apply_active_events_filter(events_query)
        
        events_result = await db.execute(events_query)
        events = list(events_result.scalars().all())
        
        # Get total count for category with active events filtering
        count_query = (
            select(func.count(Event.event_id))
            .join(Category, Event.category_id == Category.category_id)
            .filter(Category.category_slug == slug.lower())
        )
        count_query = apply_active_events_filter(count_query)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        return events, total, subcategories, True
    
    # If not a category slug, try subcategory slug
    subcategory_query = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.organizer),
            selectinload(Event.slots),
        )
        .join(SubCategory, Event.subcategory_id == SubCategory.subcategory_id)
        .filter(SubCategory.subcategory_slug == slug.lower())
        .order_by(desc(Event.created_at))
        .offset(offset)
        .limit(per_page)
    )
    # Apply active events filtering
    subcategory_query = apply_active_events_filter(subcategory_query)
    
    subcategory_result = await db.execute(subcategory_query)
    subcategory_events = list(subcategory_result.scalars().all())
    
    # Get total count for subcategory with active events filtering
    count_query = (
        select(func.count(Event.event_id))
        .join(SubCategory, Event.subcategory_id == SubCategory.subcategory_id)
        .filter(SubCategory.subcategory_slug == slug.lower())
    )
    count_query = apply_active_events_filter(count_query)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    return subcategory_events, total, None, False


async def fetch_events_grouped_by_subcategory(
    db: AsyncSession, slug: str, page: int = 1, per_page: int = 10
) -> Tuple[dict, int, int]:
    """Fetch events grouped by subcategory for a given category slug
    
    Returns:
        - subcategory_events: Dict mapping subcategory to its events
        - total_events: Total number of events across all subcategories
        - total_subcategories: Total number of subcategories
    """
    
    # First check if it's a category slug
    category_query = select(Category).filter(Category.category_slug == slug.lower())
    category_result = await db.execute(category_query)
    category = category_result.scalars().first()
    
    if not category:  # Return empty if category doesn't exist
        return {}, 0, 0
    
    # Get subcategories in this category (all subcategories)
    subcategories_query = (
        select(SubCategory)
        .filter(SubCategory.category_id == category.category_id)
        .order_by(SubCategory.subcategory_name)
    )
    subcategories_result = await db.execute(subcategories_query)
    subcategories = list(subcategories_result.scalars().all())
    
    if not subcategories:
        return {}, 0, 0
    
    # Get events for each subcategory
    subcategory_events = {}
    total_events = 0
    
    for subcategory in subcategories:
        # Get events for this subcategory with active events filtering
        events_query = (
            select(Event)
            .options(
                selectinload(Event.category),
                selectinload(Event.subcategory),
                selectinload(Event.organizer),
                selectinload(Event.slots),
            )
            .filter(Event.subcategory_id == subcategory.subcategory_id)
            .order_by(desc(Event.created_at))
        )
        # Apply active events filtering
        events_query = apply_active_events_filter(events_query)
        
        events_result = await db.execute(events_query)
        events = list(events_result.scalars().all())
        
        subcategory_events[subcategory] = events
        total_events += len(events)
    
    return subcategory_events, total_events, len(subcategories)


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
    
    # Apply active events filtering
    query = apply_active_events_filter(query)

    # Apply filters
    filters = []

    # Note: status filter is now handled by hierarchical filtering
    # if status is not None:
    #     filters.append(Event.event_status == status)

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
        from shared.db.models import EventSlot

        slot_count_subquery = (
            select(func.count(EventSlot.slot_ids))
            .filter(EventSlot.event_id == Event.event_id)
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

    # Get total count with active events filtering
    count_query = select(func.count(Event.event_id))
    count_query = apply_active_events_filter(count_query)
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

    # Build base query with active events filtering
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
    
    # Apply active events filtering
    query = apply_active_events_filter(query)

    # Apply additional filters if provided
    filters = []
    # Note: status filter is now handled by hierarchical filtering
    # if status is not None:
    #     filters.append(Event.event_status == status)

    if filters:
        query = query.filter(and_(*filters))

    # Get statistics with active events filtering
    total_query = select(func.count(Event.event_id)).filter(
        Event.organizer_id == organizer_id
    )
    total_query = apply_active_events_filter(total_query)
    
    # For active events, we use the same active events filtering (all returned events are active)
    active_query = total_query

    total_result = await db.execute(total_query)
    active_result = await db.execute(active_query)

    total_events = total_result.scalar() or 0
    active_events = active_result.scalar() or 0  # Same as total since we only return active events
    inactive_events = 0  # No inactive events returned due to hierarchical filtering

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
        .filter(Event.event_status == True)
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
        Event.event_status == True
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
