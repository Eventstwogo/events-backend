from fastapi import APIRouter

from rbac_service.api.v1.endpoints import permissions, role_permissions, roles

rbac_api_router = APIRouter(prefix="/api/v1")

# Role and Permission Endpoints
rbac_api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
rbac_api_router.include_router(
    permissions.router, prefix="/permissions", tags=["Permissions"]
)
rbac_api_router.include_router(
    role_permissions.router,
    prefix="/role-permissions",
    tags=["Role Permissions"],
)
