from fastapi import APIRouter

from event_service.api.v1.endpoints import (
    analytics,
    bookings,
    category_events,
    coupons,
    event_creation_with_images,
    event_images,
    event_type,
    events,
    featured_events,
    slots,
)


event_router = APIRouter(prefix="/api/v1")
event_router.include_router(
    event_creation_with_images.router,
    prefix="/events",
    tags=["Event Creation with Images"],
)

event_router.include_router(
    event_type.router, prefix="/eventtype", tags=["Event Type"]
)

event_router.include_router(events.router, prefix="/events", tags=["Events"])
event_router.include_router(
    category_events.router, prefix="/category-events", tags=["Category Events"]
)
event_router.include_router(
    event_images.router, prefix="/events", tags=["Event Images"]
)
# event_router.include_router(
#     advanced_events.router, prefix="/advanced-events", tags=["Advanced Events"]
# )
# event_router.include_router(
#     utility_events.router, prefix="/utility-events", tags=["Utility Events"]
# )
event_router.include_router(slots.router, prefix="/slots", tags=["Event Slots"])
event_router.include_router(
    analytics.router, prefix="/analytics", tags=["Event Analytics"]
)
event_router.include_router(
    bookings.router, prefix="/bookings", tags=["Event Bookings"]
)
event_router.include_router(
    featured_events.router, prefix="/featured-events", tags=["Featured Events"]
)
event_router.include_router(
    coupons.router, prefix="/coupons", tags=["Coupons"]
)
# event_router.include_router(
#     advanced_slots.router, prefix="/advanced-slots", tags=["Advanced Slots"]
# )
