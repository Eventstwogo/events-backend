from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db.models import Event


async def fetch_featured_events(
    db: AsyncSession, limit: int = 6
) -> List[Event]:
    """
    Fetch featured events in descending order with specified limit

    Args:
        db: Database session
        limit: Maximum number of events to return (default: 6)

    Returns:
        List of featured events with category and subcategory relationships
    """
    query = (
        select(Event)
        .options(selectinload(Event.category), selectinload(Event.subcategory))
        .where(Event.featured_event == True)
        .order_by(desc(Event.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    events = result.scalars().all()
    return list(events)


async def update_event_featured_status(
    db: AsyncSession, event_id: str, featured_status: bool
) -> Optional[Event]:
    """
    Update the featured status of an event

    Args:
        db: Database session
        event_id: ID of the event to update
        featured_status: New featured status

    Returns:
        Updated event object or None if event not found
    """
    # First, fetch the event
    query = select(Event).where(Event.event_id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        return None

    # Update the featured status
    event.featured_event = featured_status

    # Commit the changes
    await db.commit()
    await db.refresh(event)

    return event


async def get_featured_events_count(db: AsyncSession) -> int:
    """
    Get the total count of featured events

    Args:
        db: Database session

    Returns:
        Total number of featured events
    """
    query = select(Event).where(Event.featured_event == True)
    result = await db.execute(query)
    events = result.scalars().all()
    return len(list(events))
