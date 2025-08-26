from fastapi import APIRouter, Depends, Path, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import Annotated, Literal

from new_event_service.schemas.analytics import (
    AdminAnalyticsResponse,
    BookingAnalyticsResponse,
    EventBookingStatsResponse,
    EventStatsResponse,
    NewEventFullDetailsApiResponse,
    NewEventSummaryApiResponse,
    OrganizerAnalyticsResponse,
)
from new_event_service.services.analytics import (
    fetch_admin_events_analytics,
    fetch_booking_analytics,
    fetch_event_booking_stats_by_time_range,
    fetch_event_statistics,
    fetch_organizer_events_analytics,
    get_organizer_full_details,
    get_organizer_summary,
)
from new_event_service.services.event_fetcher import EventTypeStatus
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "/organizer-details/{user_id}",
    status_code=200,
    response_model=NewEventFullDetailsApiResponse,
    summary="Get Full New Event Organizer Details",
    description="Fetch complete organizer details including business profile, new events, and event slots",
)
@exception_handler
async def get_new_event_organizer_full_details(
    user_id: str = Path(
        ..., min_length=6, max_length=12, description="User ID of the organizer"
    ),
    event_type: Annotated[
        Literal[EventTypeStatus.COMPLETED, EventTypeStatus.UPCOMING],
        Query(
            description="Filter events by type: past or active (present + upcoming)",
            example=EventTypeStatus.UPCOMING,
        ),
    ] = EventTypeStatus.UPCOMING,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch full details of an organizer including associated new events and event slots.
    Supports filters for past and present+future events.

    This endpoint:
    1. Fetches user from AdminUser table
    2. Checks if business profile exists using business_id from admin user table
    3. Fetches any new events associated with the user and their event slots
    """

    result = await get_organizer_full_details(user_id, db, event_type)

    return api_response(
        status_code=result["status_code"],
        message=result["message"],
        data=result["data"],
    )


@router.get(
    "/organizer-summary/{user_id}",
    status_code=200,
    response_model=NewEventSummaryApiResponse,
    summary="Get New Event Organizer Summary",
    description="Fetch a lightweight summary of organizer details with new events statistics",
)
@exception_handler
async def get_new_event_organizer_summary(
    user_id: str = Path(
        ..., min_length=6, max_length=12, description="User ID of the organizer"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch a summary of organizer details without full new event data.

    This is a lighter version that provides basic organizer info,
    business profile status, and new event statistics.
    """

    result = await get_organizer_summary(user_id, db)

    return api_response(
        status_code=result["status_code"],
        message=result["message"],
        data=result["data"],
    )


@router.get(
    "/organizer-events",
    status_code=status.HTTP_200_OK,
    response_model=OrganizerAnalyticsResponse,
    summary="Not integrated in any frontend",
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
    summary="Not integrated in any frontend",
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
    summary="Not integrated in any frontend",
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


@router.get(
    "/booking-analytics",
    status_code=status.HTTP_200_OK,
    response_model=BookingAnalyticsResponse,
    summary="Integrated in Admin frontend",
)
@exception_handler
async def get_booking_analytics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive booking analytics from EventBookings table.

    This endpoint provides booking analytics for dashboard cards including:
    - Total bookings (total number of seats booked)
    - Total revenue (sum of booking prices)
    - Approved bookings (count of bookings with status "approved")
    - Average booking value (average price per booking)

    Returns:
    - Comprehensive booking analytics data
    """

    # Fetch booking analytics
    analytics_data = await fetch_booking_analytics(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Booking analytics retrieved successfully",
        data=analytics_data,
    )


@router.get(
    "/event-booking-stats",
    status_code=status.HTTP_200_OK,
    response_model=EventBookingStatsResponse,
    summary="Not integrated in any frontend",
)
@exception_handler
async def get_event_booking_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get event booking statistics for different time ranges.

    This endpoint provides event-specific booking statistics for:
    - Daily (today)
    - Weekly (last 7 days)
    - Monthly (current month)
    - Yearly (current year)
    - All-time

    For each event, returns:
    - Total seats booked
    - Total revenue

    Returns:
    - Event booking statistics grouped by time ranges
    """

    # Fetch event booking statistics
    stats_data = await fetch_event_booking_stats_by_time_range(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event booking statistics retrieved successfully",
        data=stats_data,
    )
