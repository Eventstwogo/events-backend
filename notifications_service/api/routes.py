from fastapi import APIRouter

from .v1.endpoints import notifications

notifications_router = APIRouter(prefix="/api/v1")
notifications_router.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"]
)