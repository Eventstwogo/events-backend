from fastapi import APIRouter

from admin_service.api.v1.endpoints import (
    analytics,
    config,
    enquiry,
    login,
    my_session,
    password,
    profile,
    register,
    session,
    token,
    user_management,
)

admin_router = APIRouter(prefix="/api/v1")

admin_router.include_router(
    config.router, prefix="/config", tags=["Admin Config Management"]
)
admin_router.include_router(
    register.router, prefix="/admin", tags=["Admin Registration"]
)
admin_router.include_router(
    login.router, prefix="/admin", tags=["Admin Authentication"]
)
admin_router.include_router(
    password.router, prefix="/admin", tags=["Admin Password Management"]
)
admin_router.include_router(
    profile.router, prefix="/admin/profile", tags=["Admin Profile Management"]
)
admin_router.include_router(
    user_management.router,
    prefix="/admin/users",
    tags=["Admin User Management"],
)
admin_router.include_router(
    analytics.router, prefix="/admin", tags=["Admin Analytics"]
)
admin_router.include_router(
    enquiry.router, prefix="/admin/enquiries", tags=["Admin Enquiry Management"]
)
admin_router.include_router(
    token.router, prefix="/admin/token", tags=["Admin Token Management"]
)
admin_router.include_router(
    session.router, prefix="/admin/sessions", tags=["Admin Session Management"]
)
admin_router.include_router(
    my_session.router, prefix="/admin/me/sessions", tags=["My Admin Session"]
)
