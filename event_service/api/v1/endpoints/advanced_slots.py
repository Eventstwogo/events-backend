from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from event_service.schemas.slots import (
    EventSlotListResponse,
    EventSlotResponse,
    SlotAnalyticsResponse,
    SlotAvailabilityResponse,
    SlotStatisticsResponse,
)
from event_service.services.response_builder import (
    event_not_found_response,
    slot_not_found_response,
)
from event_service.services.slots import (
    check_event_exists_by_slot_id,
    get_detailed_slot_analytics,
    get_slot_availability_info,
    get_slot_statistics,
    get_slots_by_event_id,
    get_slots_with_pagination,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get("/list", status_code=status.HTTP_200_OK)
@exception_handler
async def list_slots_endpoint(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of items per page"
    ),
    slot_status: bool = Query(
        default=None,
        description="Filter by slot status (True for active, False for inactive)",
    ),
    event_id: str = Query(default=None, description="Filter by event ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    List event slots with pagination and optional filtering.

    This endpoint retrieves a paginated list of event slots with optional
    filtering by status and event ID.

    Args:
        page: Page number (1-based, default: 1)
        limit: Number of items per page (1-100, default: 10)
        status: Optional status filter (True for active, False for inactive)
        event_id: Optional event ID filter
        db: Database session

    Returns:
        JSONResponse: Paginated list of slots with metadata

    Raises:
        400: If pagination parameters are invalid
        404: If filtered event doesn't exist
    """

    # Validate pagination parameters
    if page < 1:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Page number must be greater than 0",
            log_error=True,
        )

    if limit < 1 or limit > 100:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Limit must be between 1 and 100",
            log_error=True,
        )

    # If event_id is provided, validate that the event exists
    if event_id:
        event = await check_event_exists_by_slot_id(db, event_id)
        if not event:
            return event_not_found_response()

    # Get slots with pagination
    slots, total_count = await get_slots_with_pagination(
        db=db,
        page=page,
        limit=limit,
        status=slot_status,
        event_id=event_id,
    )

    # Convert to response format
    slot_responses = [
        EventSlotResponse(
            id=slot.id,
            slot_id=slot.slot_id,
            slot_data=slot.slot_data,
            slot_status=slot.slot_status,
            created_at=slot.created_at,
            updated_at=slot.updated_at,
        )
        for slot in slots
    ]

    # Calculate pagination metadata
    total_pages = (total_count + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1

    pagination_info = {
        "current_page": page,
        "per_page": limit,
        "total_pages": total_pages,
        "total_items": total_count,
        "has_next": has_next,
        "has_prev": has_prev,
        "next_page": page + 1 if has_next else None,
        "prev_page": page - 1 if has_prev else None,
    }

    response_data = EventSlotListResponse(
        slots=slot_responses,
        pagination=pagination_info,
        total_count=total_count,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Retrieved {len(slots)} slots successfully",
        data=response_data.model_dump(),
    )


@router.get("/statistics/{event_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def get_slot_statistics_endpoint(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get comprehensive statistics for all slots of an event.

    This endpoint provides detailed statistics including total slots,
    active/inactive counts, capacity, revenue potential, and averages.

    Args:
        event_id: The event ID
        db: Database session

    Returns:
        JSONResponse: Comprehensive slot statistics

    Raises:
        404: If the event doesn't exist
    """

    # Get slot statistics
    statistics = await get_slot_statistics(db, event_id)

    if statistics["total_slots"] == 0:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No slots found for this event or event doesn't exist",
            log_error=True,
        )

    response_data = SlotStatisticsResponse(**statistics)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot statistics retrieved successfully",
        data=response_data.model_dump(),
    )


@router.get("/availability/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def check_slot_availability_endpoint(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Check availability information for a specific slot.

    This endpoint provides detailed availability information including
    slot status, capacity details, and date-wise breakdown.

    Args:
        slot_id: The event's slot ID
        db: Database session

    Returns:
        JSONResponse: Detailed availability information

    Raises:
        404: If the event or slot doesn't exist
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    # Get availability information
    availability_info = await get_slot_availability_info(db, slot_id)

    response_data = SlotAvailabilityResponse(**availability_info)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot availability information retrieved successfully",
        data=response_data.model_dump(),
    )


@router.get("/analytics/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def get_slot_analytics_endpoint(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get detailed analytics for a specific slot.

    This endpoint provides comprehensive analytics including date-wise
    analysis, pricing information, capacity utilization, and summary statistics.

    Args:
        slot_id: The event's slot ID
        db: Database session

    Returns:
        JSONResponse: Detailed slot analytics

    Raises:
        404: If the event or slot doesn't exist
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    # Get detailed analytics
    analytics = await get_detailed_slot_analytics(db, slot_id)

    if "error" in analytics:
        return slot_not_found_response()

    response_data = SlotAnalyticsResponse(**analytics)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot analytics retrieved successfully",
        data=response_data.model_dump(),
    )


@router.get("/by-event/{event_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def get_slots_by_event_endpoint(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all slots for a specific event.

    This endpoint retrieves all slots associated with a specific event,
    providing a complete view of the event's slot configuration.

    Args:
        event_id: The event ID
        db: Database session

    Returns:
        JSONResponse: List of all slots for the event

    Raises:
        404: If the event doesn't exist
    """

    # Get all slots for the event
    slots = await get_slots_by_event_id(db, event_id)

    if not slots:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No slots found for this event or event doesn't exist",
            log_error=True,
        )

    # Convert to response format
    slot_responses = [
        EventSlotResponse(
            id=slot.id,
            slot_id=slot.slot_id,
            slot_data=slot.slot_data,
            slot_status=slot.slot_status,
            created_at=slot.created_at,
            updated_at=slot.updated_at,
        )
        for slot in slots
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Retrieved {len(slots)} slots for event {event_id}",
        data={"slots": [slot.model_dump() for slot in slot_responses]},
    )
