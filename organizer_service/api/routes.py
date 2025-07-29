from fastapi import APIRouter

from organizer_service.api.v1.endpoints import (
    abn_check,
    business_profile,
    fetch_vendors,
    industries,
    onboarding,
    registration,
    store,
    verify,
)

organizer_router = APIRouter(prefix="/api/v1")

# Add all endpoint routers
organizer_router.include_router(
    registration.router, prefix="/auth", tags=["Organizer Registration"]
)
organizer_router.include_router(
    verify.router, prefix="/email", tags=["Organizer Email Verification"]
)
organizer_router.include_router(
    abn_check.router, prefix="/abn", tags=["Organizer ABN Check"]
)
organizer_router.include_router(
    onboarding.router, prefix="/onboarding", tags=["Organizer Onboarding"]
)
organizer_router.include_router(
    store.router, prefix="/store", tags=["Organizer Store"]
)
organizer_router.include_router(
    business_profile.router,
    prefix="/business",
    tags=["Organizer Business Profile"],
)
organizer_router.include_router(
    fetch_vendors.router, prefix="/vendors", tags=["Organizer Vendors"]
)
organizer_router.include_router(
    industries.router, prefix="/industries", tags=["Organizer Industries"]
)
