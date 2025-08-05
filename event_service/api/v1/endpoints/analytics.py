from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.analytics import (
    AdminAnalyticsResponse,
    EventStatsResponse,
    OrganizerAnalyticsResponse,
)
from event_service.services.analytics import (
    fetch_admin_events_analytics,
    fetch_event_statistics,
    fetch_organizer_events_analytics,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "/organizer-events",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerAnalyticsResponse,
)
@exception_handler
async def get_organizer_events_analytics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics for all organizer-created events in the system.

    This endpoint is designed for the organizer Next.js app.
    No authentication required - returns system-wide organizer analytics.

    Returns:
    - Events analytics for all organizer-created events
    - Slots analytics for all organizer-created events
    - Organizer statistics (total organizers, top organizers)
    """

    # Fetch organizer events analytics
    analytics_data = await fetch_organizer_events_analytics(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Organizer events analytics retrieved successfully",
        data=analytics_data,
    )


@router.get(
    "/admin-events",
    status_code=status.HTTP_200_OK,
    response_model=AdminAnalyticsResponse,
)
@exception_handler
async def get_admin_events_analytics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive analytics for all events in the system.

    This endpoint is designed for the admin Next.js app.
    No authentication required - returns system-wide analytics.

    Returns:
    - Overall system analytics (all events and slots)
    - Organizer-created events analytics (separated)
    - Admin-created events analytics (separated)
    - User statistics (users by role, top organizers, top admins)
    """

    # Fetch admin events analytics
    analytics_data = await fetch_admin_events_analytics(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin events analytics retrieved successfully",
        data=analytics_data,
    )


@router.get(
    "/event-stats",
    status_code=status.HTTP_200_OK,
    response_model=EventStatsResponse,
)
@exception_handler
async def get_event_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get simple event statistics for dashboard.

    Returns:
    - Active events count
    - Upcoming events count
    - Monthly growth percentage (current month vs previous month)
    - Current month events count
    - Previous month events count
    """

    # Fetch event statistics
    stats_data = await fetch_event_statistics(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event statistics retrieved successfully",
        data=stats_data,
    )
