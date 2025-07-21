from typing import List, Optional, Tuple

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.logging_config import get_logger
from shared.db.models import Event

logger = get_logger(__name__)


async def fetch_events_with_filters(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 10,
    status: Optional[bool] = None,
    category_id: Optional[str] = None,
    subcategory_id: Optional[str] = None,
    organizer_id: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[Event], int]:
    """Fetch events with filtering, pagination, and sorting"""

    # Build base query with relations
    query = select(Event).options(
        selectinload(Event.category),
        selectinload(Event.subcategory),
        selectinload(Event.organizer),
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

    if search:
        search_filter = or_(
            Event.event_title.ilike(f"%{search}%"),
            Event.event_slug.ilike(f"%{search}%"),
        )
        filters.append(search_filter)

    if filters:
        query = query.filter(and_(*filters))

    # Get total count
    count_query = select(func.count(Event.event_id))
    if filters:
        count_query = count_query.filter(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

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
    total = total if total is not None else 0

    return events, total
