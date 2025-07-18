from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.db.models import User
from shared.db.sessions.database import get_db
from shared.dependencies.user import get_current_active_user
from shared.utils.exception_handlers import exception_handler
from user_service.services.analytics import (
    get_admin_user_analytics,
    get_daily_registrations,
)

router = APIRouter()


@router.get("/analytics", summary="Get application user analytics")
@exception_handler
async def user_analytics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get analytics data for application users including summary statistics and daily registrations.

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
