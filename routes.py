from fastapi import APIRouter

from admin_service.api.routes import admin_router
from category_service.api.routes import category_router
from event_service.api.routes import event_router
from new_event_service.api.routes import new_event_router
from organizer_service.api.routes import organizer_router
from rbac_service.api.routes import rbac_api_router
from user_service.api.routes import user_router

api_router = APIRouter()

api_router.include_router(rbac_api_router)
api_router.include_router(category_router)
api_router.include_router(admin_router)
api_router.include_router(user_router)
api_router.include_router(event_router)
api_router.include_router(new_event_router)
api_router.include_router(organizer_router)
