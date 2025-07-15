from fastapi import APIRouter

from user_service.api.v1.endpoints import (
    analytics,
    login,
    password,
    profile,
    register,
    session,
    my_session,
    token,
    user_management,
    verify,
)

user_router = APIRouter(prefix="/api/v1")

user_router.include_router(register.router, prefix="/users", tags=["User Registration"])
user_router.include_router(login.router, prefix="/users", tags=["User Authentication"])
user_router.include_router(
    password.router, prefix="/users", tags=["User Password Management"]
)
user_router.include_router(token.router, prefix="/users/token", tags=["User Token Management"])
user_router.include_router(session.router, prefix="/users/sessions", tags=["User Session Management"])
user_router.include_router(my_session.router, prefix="/users/me/sessions", tags=["My User Session"])
user_router.include_router(profile.router, prefix="/users/profile", tags=["User Profile Management"])
user_router.include_router(
    user_management.router, prefix="/users", tags=["User User Management"]
)
user_router.include_router(analytics.router, prefix="/users", tags=["User Analytics"])
user_router.include_router(verify.router, prefix="/users", tags=["User Verification"])
