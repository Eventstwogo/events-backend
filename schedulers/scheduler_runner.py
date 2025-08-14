from apscheduler.schedulers.asyncio import AsyncIOScheduler

from schedulers.expired_event_updater_scheduler import cleanup_expired_events
from schedulers.release_expired_holds_scheduler import cleanup_job

BOOKING_SEATS_CLEANUP_INTERVAL_MINUTES = 10
EXPIRED_EVENTS_CHECK_INTERVAL_HOURS = 1

scheduler = AsyncIOScheduler()


def start_schedulers():
    if not scheduler.get_jobs():
        # Booking seat release
        scheduler.add_job(
            cleanup_job,
            "interval",
            minutes=BOOKING_SEATS_CLEANUP_INTERVAL_MINUTES,
            id="booking_seats_cleanup",
            replace_existing=True,
        )

        # Expired event updater
        scheduler.add_job(
            cleanup_expired_events,
            "interval",
            hours=EXPIRED_EVENTS_CHECK_INTERVAL_HOURS,
            id="expired_events_updater",
            replace_existing=True,
        )

        scheduler.start()
