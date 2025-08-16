from fastapi import APIRouter

from new_event_service.api.v1.endpoints import event_creation_with_images, slots

new_event_router = APIRouter(prefix="/api/v1")
new_event_router.include_router(
    event_creation_with_images.router,
    prefix="/new-events",
    tags=["New Event Creation with Images"],
)
new_event_router.include_router(
    slots.router, prefix="/new-slots", tags=["New Event Slots"]
)
