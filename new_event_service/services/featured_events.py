from typing import List, Optional

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from new_event_service.schemas.featured_events import FeaturedEventResponse
from shared.db.models import NewEvent
from shared.db.models.featured_events import FeaturedEvents
from shared.utils.id_generators import generate_lower_uppercase


async def fetch_featured_events(
    db: AsyncSession, limit: int = 6
) -> List[NewEvent]:
    """
    Fetch featured events in descending order with specified limit

    Args:
        db: Database session
        limit: Maximum number of events to return (default: 6)

    Returns:
        List of featured events with category and subcategory relationships
    """
    query = (
        select(NewEvent)
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
        )
        .where(NewEvent.featured_event == True)
        .order_by(desc(NewEvent.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    events = result.scalars().all()
    return list(events)


async def update_event_featured_status(
    db: AsyncSession, event_id: str, featured_status: bool
) -> Optional[NewEvent]:
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
    query = select(NewEvent).where(NewEvent.event_id == event_id)
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
    query = select(NewEvent).where(NewEvent.featured_event == True)
    result = await db.execute(query)
    events = result.scalars().all()
    return len(list(events))


async def create_featured_event(db: AsyncSession, event_data) -> FeaturedEvents:
    feature_id = generate_lower_uppercase()

    new_event = FeaturedEvents(feature_id=feature_id, **event_data.dict())
    db.add(new_event)

    await db.execute(
        update(NewEvent)
        .where(NewEvent.event_id == event_data.event_ref_id)
        .values(featured_event=True)
    )

    await db.commit()
    await db.refresh(new_event)

    return new_event


async def list_featured_events(db: AsyncSession) -> list[FeaturedEventResponse]:
    query = select(FeaturedEvents).options(
        joinedload(FeaturedEvents.new_event).joinedload(
            NewEvent.new_organizer
        ),  # event + organizer
        joinedload(FeaturedEvents.user_ref),  # user_ref from admin users
    )
    result = await db.execute(query)
    featured_events = result.scalars().all()

    response: list[FeaturedEventResponse] = []
    for fe in featured_events:
        response.append(
            FeaturedEventResponse(
                feature_id=fe.feature_id,
                id=fe.id,
                user_ref_id=fe.user_ref_id,
                event_ref_id=fe.event_ref_id,
                start_date=fe.start_date,
                end_date=fe.end_date,
                total_weeks=fe.total_weeks,
                price=float(fe.price),
                feature_status=fe.feature_status,
                event_slug=fe.new_event.event_slug if fe.new_event else None,
                event_title=fe.new_event.event_title if fe.new_event else None,
                organizer_name=(
                    fe.new_event.new_organizer.username
                    if fe.new_event and fe.new_event.new_organizer
                    else None
                ),
                # if you want to also include the user_ref name:
                # user_ref_name=fe.user_ref.username_encrypted if fe.user_ref else None
            )
        )
    return response
