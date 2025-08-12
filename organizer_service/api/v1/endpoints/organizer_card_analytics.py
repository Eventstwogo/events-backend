from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from organizer_service.schemas.new_analytics import (
    OrganizerCardStats,
    OrganizerCardStatsApiResponse,
)
from shared.constants import (
    ONBOARDING_APPROVED,
    ONBOARDING_REJECTED,
    ONBOARDING_SUBMITTED,
    ONBOARDING_UNDER_REVIEW,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser, BusinessProfile
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "/organizer-counts",
    status_code=200,
    response_model=OrganizerCardStatsApiResponse,
    summary="Get Organizer Counts for Dashboard Cards",
    description="Get organizer counts by status for admin panel dashboard cards: Total, Approved, Pending, Rejected, Under Review, Not Started",
)
@exception_handler
async def get_organizer_counts(
    db: AsyncSession = Depends(get_db),
):
    """
    Get organizer counts by status for admin panel dashboard cards.

    This endpoint provides simple counts for:
    - Total Organizers
    - Approved
    - Pending (Submitted)
    - Rejected
    - Under Review
    - Not Started (no business profile)

    Returns:
        Organizer counts by status
    """

    # Query to get all business profiles (these represent organizers)
    query = select(BusinessProfile)

    result = await db.execute(query)
    business_profiles = result.scalars().all()

    # Initialize counters
    total_organizers = len(business_profiles)
    approved = 0
    pending = 0
    rejected = 0
    under_review = 0
    not_started = 0

    # Count by status
    for business_profile in business_profiles:
        status = business_profile.is_approved
        if status == ONBOARDING_APPROVED:
            approved += 1
        elif status == ONBOARDING_SUBMITTED:
            pending += 1
        elif status == ONBOARDING_REJECTED:
            rejected += 1
        elif status == ONBOARDING_UNDER_REVIEW:
            under_review += 1
        else:
            not_started += 1

    # Create response
    card_stats = OrganizerCardStats(
        total_organizers=total_organizers,
        approved=approved,
        pending=pending,
        rejected=rejected,
        under_review=under_review,
        not_started=not_started,
    )

    return api_response(
        status_code=200,
        message="Organizer counts retrieved successfully",
        data=card_stats,
    )
