from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.services.analytics import (
    get_admin_user_analytics,
    get_daily_registrations,
    get_dashboard_analytics,
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
    "/dashboard", summary="Get dashboard analytics", response_model=None
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
