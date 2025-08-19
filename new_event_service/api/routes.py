from fastapi import APIRouter

from new_event_service.api.v1.endpoints import (
    analytics,
    bookings,
    category_events,
    coupons,
    event_creation_with_images,
    event_type,
    events,
    featured_events,
    slots,
    slug_events,
)

new_event_router = APIRouter(prefix="/api/v1")

new_event_router.include_router(
    event_type.router, prefix="/eventtype", tags=["Event Type"]
)
new_event_router.include_router(
    event_creation_with_images.router,
    prefix="/new-events",
    tags=["New Event Creation with Images"],
)
new_event_router.include_router(
    slots.router, prefix="/new-slots", tags=["New Event Slots"]
)
new_event_router.include_router(
    events.router, prefix="/new-events", tags=["New Events"]
)
new_event_router.include_router(
    slug_events.router, prefix="/new-events", tags=["New Slug Events"]
)
new_event_router.include_router(
    category_events.router,
    prefix="/new-category-events",
    tags=["New Category Events"],
)
new_event_router.include_router(
    analytics.router,
    prefix="/new-events/new-analytics",
    tags=["New Event Analytics"],
)
new_event_router.include_router(
    bookings.router, prefix="/new-bookings", tags=["New Event Bookings"]
)
new_event_router.include_router(
    featured_events.router, prefix="/featured-events", tags=["Featured Events"]
)
new_event_router.include_router(
    coupons.router, prefix="/coupons", tags=["Coupons"]
)
