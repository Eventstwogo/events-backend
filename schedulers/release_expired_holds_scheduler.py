from schedulers.booking_status_updater import release_expired_holds
from shared.db.sessions.database import AsyncSessionLocal


async def cleanup_job():
    async with AsyncSessionLocal() as db:
        released = await release_expired_holds(db)
        if released:
            print(f"Released {released} expired holds.")
