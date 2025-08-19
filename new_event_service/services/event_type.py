from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_event_service.schemas.event_type import EventTypeCreateRequest
from shared.db.models.featured_events import EventType
from shared.utils.id_generators import generate_lower_uppercase


async def create_event_type_service(
    db: AsyncSession, request: EventTypeCreateRequest
) -> EventType:
    """Create a new event type if event_type is unique."""
    existing = await db.execute(
        select(EventType).where(EventType.event_type == request.event_type)
    )
    if existing.scalar_one_or_none():
        raise ValueError(
            f"Event type with event_type '{request.event_type}' already exists"
        )

    new_type = EventType(
        type_id=generate_lower_uppercase(6),
        event_type=request.event_type,
    )
    db.add(new_type)
    await db.commit()
    await db.refresh(new_type)
    return new_type


async def list_event_types_service(db: AsyncSession) -> list[EventType]:
    """Return all event types."""
    result = await db.execute(select(EventType))
    return list(result.scalars().all())


async def list_active_event_types_service(db: AsyncSession):
    result = await db.execute(
        select(EventType).where(EventType.type_status == False)
    )
    return result.scalars().all()


async def update_event_type_service(
    db: AsyncSession, type_id: str, new_name: str
) -> EventType:
    """Update the event_type field for a given type_id."""
    result = await db.execute(
        select(EventType).where(EventType.type_id == type_id)
    )
    event_type = result.scalar_one_or_none()

    if not event_type:
        raise ValueError(f"Event type with id '{type_id}' not found")

    # Check for duplicate names
    existing = await db.execute(
        select(EventType).where(
            EventType.event_type == new_name, EventType.type_id != type_id
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Event type '{new_name}' already exists")

    event_type.event_type = new_name
    db.add(event_type)
    await db.commit()
    await db.refresh(event_type)
    return event_type


async def update_event_type_status_service(
    db: AsyncSession, type_id: str, new_status: bool
) -> EventType:
    """Update the type_status field for a given type_id."""
    result = await db.execute(
        select(EventType).where(EventType.type_id == type_id)
    )
    event_type = result.scalar_one_or_none()

    if not event_type:
        raise ValueError(f"Event type with id '{type_id}' not found")

    event_type.type_status = new_status
    db.add(event_type)
    await db.commit()
    await db.refresh(event_type)
    return event_type
