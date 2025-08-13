"""
Background task for cleaning up expired seat holds.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from event_service.services.seat_holding import cleanup_all_expired_holds
from shared.db.sessions.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def cleanup_expired_holds_task():
    """
    Background task to clean up expired seat holds.
    This should be run periodically (e.g., every 5 minutes).
    """
    try:
        async with AsyncSessionLocal() as db:
            cleaned_count = await cleanup_all_expired_holds(db)
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired seat holds")

    except Exception as e:
        logger.error(f"Error in cleanup_expired_holds_task: {str(e)}")


async def start_seat_cleanup_scheduler():
    """
    Start the periodic seat cleanup scheduler.
    This runs every 5 minutes to clean up expired holds.
    """
    logger.info("Starting seat cleanup scheduler...")

    while True:
        try:
            await cleanup_expired_holds_task()
            # Wait 5 minutes before next cleanup
            await asyncio.sleep(300)  # 300 seconds = 5 minutes

        except Exception as e:
            logger.error(f"Error in seat cleanup scheduler: {str(e)}")
            # Wait 1 minute before retrying on error
            await asyncio.sleep(60)


def schedule_seat_cleanup():
    """
    Schedule the seat cleanup task to run in the background.
    Call this function when starting the application.
    """
    try:
        # Create and schedule the background task
        task = asyncio.create_task(start_seat_cleanup_scheduler())
        logger.info("Seat cleanup scheduler started successfully")
        return task
    except Exception as e:
        logger.error(f"Failed to start seat cleanup scheduler: {str(e)}")
        return None
