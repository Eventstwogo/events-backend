from apscheduler.schedulers.asyncio import AsyncIOScheduler

from schedulers.booking_status_updater import cleanup_job
from schedulers.coupon_cleanup import cleanup_expired_coupons
from schedulers.expired_event_updater import cleanup_expired_events

BOOKING_SEATS_CLEANUP_INTERVAL_MINUTES = 15
EXPIRED_EVENTS_CHECK_INTERVAL_HOURS = 24
COUPON_CLEANUP_INTERVAL_MINUTES = 15

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

        # Coupon cleanup
        scheduler.add_job(
            cleanup_expired_coupons,
            "interval",
            minutes=COUPON_CLEANUP_INTERVAL_MINUTES,
            id="coupon_cleanup",
            replace_existing=True,
        )

        scheduler.start()
