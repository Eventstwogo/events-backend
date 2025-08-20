from fastapi import APIRouter

from organizer_service.api.v1.endpoints import (
    abn_check,
    analytics,
    approval,
    business_profile,
    fetch_organizers,
    onboarding,
    organizer_card_analytics,
    password,
    queries,
    registration,
    store,
    users_management,
    verify,
)

organizer_router = APIRouter(prefix="/api/v1/organizers")

# Add all endpoint routers
organizer_router.include_router(
    registration.router, prefix="/auth", tags=["Organizer Registration"]
)
organizer_router.include_router(
    password.router, tags=["Organizer Password Management"]
)
organizer_router.include_router(
    approval.router, prefix="/approval", tags=["Organizer Approval"]
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
organizer_router.include_router(store.router, tags=["Organizer Store"])
organizer_router.include_router(
    business_profile.router,
    prefix="/business",
    tags=["Organizer Business Profile"],
)
organizer_router.include_router(fetch_organizers.router, tags=["Organizers"])
organizer_router.include_router(
    analytics.router, prefix="/new-analytics", tags=["Organizer Analytics"]
)
organizer_router.include_router(
    users_management.router,
    prefix="/users",
    tags=["Organizer Users Management"],
)
organizer_router.include_router(
    queries.router,
    prefix="/queries",
    tags=["Organizer Queries"],
)
organizer_router.include_router(
    organizer_card_analytics.router,
    prefix="/card-analytics",
    tags=["Organizer Card Analytics"],
)
