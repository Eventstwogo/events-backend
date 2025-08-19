from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from new_event_service.schemas.analytics import (
    NewEventFullDetailsApiResponse,
    NewEventSummaryApiResponse,
)
from new_event_service.services.analytics import (
    get_organizer_full_details,
    get_organizer_summary,
)
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
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch full details of an organizer including associated new events and event slots.

    This endpoint:
    1. Fetches user from AdminUser table
    2. Checks if business profile exists using business_id from admin user table
    3. Fetches any new events associated with the user and their event slots
    """

    result = await get_organizer_full_details(user_id, db)

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
