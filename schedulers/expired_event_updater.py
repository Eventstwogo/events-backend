from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.new_events import EventStatus, NewEvent
from shared.db.sessions.database import AsyncSessionLocal


async def update_expired_events(db: AsyncSession) -> int:
    """
    Finds events where the latest event_date has passed
    and status is ACTIVE or PENDING, then updates them to INACTIVE.

    Returns: number of events updated.
    """
    today = date.today()

    # Step 1: Get candidate events
    result = await db.execute(
        select(NewEvent).where(
            NewEvent.event_status.in_([EventStatus.ACTIVE, EventStatus.PENDING])
        )
    )
    candidate_events = result.scalars().all()

    if not candidate_events:
        return 0

    updated_count = 0

    # Step 2: Check if the latest event date is < today
    for event in candidate_events:
        if not event.event_dates:
            continue  # skip malformed data

        latest_date = max(event.event_dates)
        if latest_date < today:
            event.event_status = EventStatus.INACTIVE
            updated_count += 1

    # Step 3: Commit updates
    if updated_count > 0:
        await db.commit()

    return updated_count


async def cleanup_expired_events():
    async with AsyncSessionLocal() as db:
        updated_count = await update_expired_events(db)
        if updated_count:
            print(f"Updated {updated_count} expired events to INACTIVE.")
