from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.schemas.analytics import (
    DashboardAnalytics,
    RecentContactsResponse,
    RecentQueriesResponse,
    SystemHealth,
    UserAnalyticsResponse,
)
from admin_service.services.analytics import (
    get_admin_user_analytics,
    get_daily_registrations,
    get_dashboard_analytics,
    get_recent_contact_us,
    get_recent_queries,
    get_system_health,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser
from shared.db.sessions.database import get_db
from shared.dependencies.admin import get_current_active_user
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get("/analytics", summary="Get admin-user analytics")
@exception_handler
async def user_analytics(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get analytics data for admin users including summary statistics and daily registrations.

    Returns:
        JSONResponse: Analytics data with summary and daily registration counts
    """
    # Fetch analytics data
    summary_data = await get_admin_user_analytics(db)

    # Fetch daily registration counts
    daily_data_result = await get_daily_registrations(db, days=30)

    # Format results
    summary_dict = dict(
        summary_data._mapping
    )  # pylint: disable=protected-access

    daily_data = [
        {"date": str(r.date), "count": r.count} for r in daily_data_result
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="User analytics fetched successfully.",
        data={"summary": summary_dict, "daily_registrations": daily_data},
    )


@router.get(
    "/dashboard",
    summary="Get dashboard analytics",
    response_model=DashboardAnalytics,
)
@exception_handler
async def dashboard_analytics(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get comprehensive dashboard analytics including categories, users, revenue, and settings.

    This endpoint provides analytics data for the admin dashboard with the following metrics:

    - **Categories**: Current total count, categories added this month, and percentage change
    - **Users**: Current user count, users added this week, and percentage change
    - **Revenue**: Current month's revenue, increase from last month (estimated based on events)
    - **Settings**: Total system configurations, changes made this week, and percentage change

    Returns:
        JSONResponse: Comprehensive dashboard analytics data
    """
    # Fetch dashboard analytics data
    analytics_data = await get_dashboard_analytics(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Dashboard analytics fetched successfully.",
        data=analytics_data,
    )


@router.get(
    "/queries/recent",
    summary="Get recent queries",
    response_model=RecentQueriesResponse,
)
@exception_handler
async def recent_queries(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of queries to return"
    ),
) -> JSONResponse:
    """
    Get recent organizer queries for dashboard display.

    Args:
        limit: Maximum number of recent queries to return (default: 10)

    Returns:
        JSONResponse: List of recent queries with basic information
    """
    queries_data = await get_recent_queries(db, limit=limit)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Recent queries fetched successfully.",
        data={"queries": queries_data, "total": len(queries_data)},
    )


@router.get(
    "/contact-us/recent",
    summary="Get recent contact us submissions",
    response_model=RecentContactsResponse,
)
@exception_handler
async def recent_contact_us(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of submissions to return"
    ),
) -> JSONResponse:
    """
    Get recent contact us submissions for dashboard display.

    Args:
        limit: Maximum number of recent submissions to return (default: 10)

    Returns:
        JSONResponse: List of recent contact us submissions with basic information
    """
    contact_data = await get_recent_contact_us(db, limit=limit)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Recent contact us submissions fetched successfully.",
        data={"contacts": contact_data, "total": len(contact_data)},
    )


@router.get(
    "/system/health",
    summary="Get system health status",
    response_model=SystemHealth,
)
@exception_handler
async def system_health(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get system health status including database connectivity, API status, and backup information.

    Returns:
        JSONResponse: System health status information
    """
    health_data = await get_system_health(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="System health status fetched successfully.",
        data=health_data,
    )
