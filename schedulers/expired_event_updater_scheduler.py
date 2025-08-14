from schedulers.expired_event_updater import update_expired_events
from shared.db.sessions.database import AsyncSessionLocal


async def cleanup_expired_events():
    async with AsyncSessionLocal() as db:
        updated_count = await update_expired_events(db)
        if updated_count:
            print(f"Updated {updated_count} expired events to INACTIVE.")
