from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from event_service.schemas.slots import (
    EventSlotCreateRequest,
    EventSlotCreateResponse,
    EventSlotResponse,
)
from event_service.services.response_builder import (
    event_not_found_response,
    invalid_slot_data_response,
    slot_already_exists_response,
    slot_created_successfully_response,
)
from event_service.services.slots import (
    check_event_exists_by_slot_id,
    check_slot_exists_for_event,
    count_event_slots,
    create_event_slot,
    get_event_slot,
    update_event_slot,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post("/create", status_code=status.HTTP_201_CREATED)
@exception_handler
async def create_event_slot_endpoint(
    slot_request: EventSlotCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new event slot with nested date/slot structure.

    This endpoint creates a new slot for an existing event. The slot contains
    scheduling and configuration data organized by dates and individual slots.

    Args:
        slot_request: Event slot creation request data
        db: Database session

    Returns:
        JSONResponse: Success message with created slot data

    Raises:
        400: If validation fails or slot already exists
        404: If the referenced event doesn't exist
        500: If slot creation fails
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_request.slot_id)
    if not event:
        return event_not_found_response()

    # Check if slot already exists for this event
    existing_slot = await check_slot_exists_for_event(db, slot_request.slot_id)
    if existing_slot:
        return slot_already_exists_response()

    # Validate slot data structure (basic validation)
    if not slot_request.slot_data:
        return invalid_slot_data_response("Slot data cannot be empty")

    # Validate that slot_data has the correct nested structure
    total_slots_count = 0
    for date_key, date_slots in slot_request.slot_data.items():
        if not isinstance(date_slots, dict):
            return invalid_slot_data_response(
                f"Invalid slot structure for date {date_key}"
            )
        total_slots_count += len(date_slots)

    # Check reasonable slot limits (max 100 individual slots across all dates)
    if total_slots_count > 100:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Maximum number of individual slots (100) exceeded across all dates",
            log_error=True,
        )

    # Create the event slot
    new_slot = await create_event_slot(
        db=db,
        slot_id=slot_request.slot_id,
        slot_data=slot_request.slot_data,
    )

    # Prepare response data
    slot_response = EventSlotResponse(
        id=new_slot.id,
        slot_id=new_slot.slot_id,
        slot_data=new_slot.slot_data,
        slot_status=new_slot.slot_status,
        created_at=new_slot.created_at,
        updated_at=new_slot.updated_at,
    )

    response_data = EventSlotCreateResponse(
        slot=slot_response, message="Event slot created successfully"
    )

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Event slot created successfully",
        data=response_data.model_dump(),
    )


@router.put("/update/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def update_event_slot_endpoint(
    slot_id: str,
    slot_request: EventSlotCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an existing event slot with new nested date/slot structure.

    This endpoint updates an existing slot for an event. The slot contains
    scheduling and configuration data organized by dates and individual slots.

    Args:
        slot_id: The event's slot ID
        slot_request: Event slot update request data
        db: Database session

    Returns:
        JSONResponse: Success message with updated slot data

    Raises:
        400: If validation fails
        404: If the referenced event or slot doesn't exist
        500: If slot update fails
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    # Validate slot data structure (basic validation)
    if not slot_request.slot_data:
        return invalid_slot_data_response("Slot data cannot be empty")

    # Validate that slot_data has the correct nested structure
    total_slots_count = 0
    for date_key, date_slots in slot_request.slot_data.items():
        if not isinstance(date_slots, dict):
            return invalid_slot_data_response(
                f"Invalid slot structure for date {date_key}"
            )
        total_slots_count += len(date_slots)

    # Check reasonable slot limits (max 100 individual slots across all dates)
    if total_slots_count > 100:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Maximum number of individual slots (100) exceeded across all dates",
            log_error=True,
        )

    # Update the event slot
    updated_slot = await update_event_slot(
        db=db,
        slot_id=slot_id,
        slot_data=slot_request.slot_data,
    )

    if not updated_slot:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Event slot not found",
            log_error=True,
        )

    # Prepare response data
    slot_response = EventSlotResponse(
        id=updated_slot.id,
        slot_id=updated_slot.slot_id,
        slot_data=updated_slot.slot_data,
        slot_status=updated_slot.slot_status,
        created_at=updated_slot.created_at,
        updated_at=updated_slot.updated_at,
    )

    response_data = EventSlotCreateResponse(
        slot=slot_response, message="Event slot updated successfully"
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slot updated successfully",
        data=response_data.model_dump(),
    )


@router.get("/get/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def get_event_slot_endpoint(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get an existing event slot data.

    Args:
        slot_id: The event's slot ID
        db: Database session

    Returns:
        JSONResponse: Event slot data

    Raises:
        404: If the referenced event or slot doesn't exist
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    # Get the event slot
    slot = await get_event_slot(db, slot_id)
    if not slot:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Event slot not found",
            log_error=True,
        )

    # Prepare response data
    slot_response = EventSlotResponse(
        id=slot.id,
        slot_id=slot.slot_id,
        slot_data=slot.slot_data,
        slot_status=slot.slot_status,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slot retrieved successfully",
        data=slot_response.model_dump(),
    )
