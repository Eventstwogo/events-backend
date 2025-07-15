from fastapi import APIRouter

from rbac_service.api.routes import rbac_api_router
from category_service.api.routes import category_router
from admin_service.api.routes import admin_router
from user_service.api.routes import user_router

api_router = APIRouter()

api_router.include_router(rbac_api_router)
api_router.include_router(category_router)
api_router.include_router(admin_router)
api_router.include_router(user_router)
