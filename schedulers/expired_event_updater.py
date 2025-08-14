from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.events import Event, EventStatus


async def update_expired_events(db: AsyncSession) -> int:
    """
    Finds events whose end_date has passed and status is ACTIVE or PENDING,
    and updates them to INACTIVE.
    Returns: number of events updated.
    """

    today = date.today()

    # Find events that have expired
    result = await db.execute(
        select(Event).where(
            Event.end_date < today,
            Event.event_status.in_([EventStatus.ACTIVE, EventStatus.PENDING]),
        )
    )

    expired_events = result.scalars().all()
    if not expired_events:
        return 0

    # Update each event status
    for event in expired_events:
        event.event_status = EventStatus.INACTIVE

    await db.commit()
    return len(expired_events)
