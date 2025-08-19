from fastapi import APIRouter

from event_service.api.v1.endpoints import (
    bookings,
    category_events,
    event_creation_with_images,
    event_images,
    events,
    slots,
)

event_router = APIRouter(prefix="/api/v1")
event_router.include_router(
    event_creation_with_images.router,
    prefix="/events",
    tags=["Event Creation with Images"],
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
    bookings.router, prefix="/bookings", tags=["Event Bookings"]
)

# event_router.include_router(
#     advanced_slots.router, prefix="/advanced-slots", tags=["Advanced Slots"]
# )
