from datetime import date, datetime
from typing import Tuple

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from event_service.schemas.slots import (
    EventSlotCreateRequest,
    EventSlotCreateResponse,
    EventSlotResponse,
    EventSlotUpdateRequest,
    SlotDateDetailsResponse,
    SlotStatusToggleResponse,
)
from event_service.services.response_builder import (
    event_not_found_response,
    invalid_slot_data_response,
    slot_already_exists_response,
    slot_not_found_response,
)
from event_service.services.slots import (
    check_event_exists_by_slot_id,
    check_slot_exists_for_event,
    create_event_slot,
    deep_merge_slot_data,
    delete_event_slot,
    get_event_slot,
    get_slot_date_details,
    toggle_slot_status,
    update_event_slot,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


def parse_slot_date(date_string: str) -> datetime:
    """
    Parse slot date string (YYYY-MM-DD format) to datetime object.

    Args:
        date_string: Date string in YYYY-MM-DD format

    Returns:
        datetime: Parsed datetime object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(
            f"Invalid date format '{date_string}'. Expected YYYY-MM-DD format: {str(e)}"
        )


def validate_slot_dates_against_event(
    slot_data: dict, event_start_date: date, event_end_date: date
) -> Tuple[bool, str]:
    """
    Validate that all slot dates fall within the event's date range.

    Args:
        slot_data: Dictionary containing slot data with date keys
        event_start_date: Event's start date
        event_end_date: Event's end date

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # event_start_date and event_end_date are already date objects, no need to call .date()
        for date_key in slot_data.keys():
            try:
                slot_date = parse_slot_date(date_key).date()

                # Check if slot date is within event date range
                if slot_date < event_start_date:
                    return (
                        False,
                        f"Slot date '{date_key}' is before event start date ({event_start_date})",
                    )

                if slot_date > event_end_date:
                    return (
                        False,
                        f"Slot date '{date_key}' is after event end date ({event_end_date})",
                    )

            except ValueError as e:
                return False, str(e)

        return True, ""

    except Exception as e:
        return False, f"Error validating slot dates: {str(e)}"


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

    # Validate slot dates against event date range
    is_valid, error_message = validate_slot_dates_against_event(
        slot_request.slot_data, event.start_date, event.end_date
    )
    if not is_valid:
        return invalid_slot_data_response(error_message)

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
    slot_request: EventSlotUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an existing event slot with proper JSONB merge logic.

    This endpoint performs a smart merge of the new slot data with existing data:
    - Merges new dates with existing dates (preserves untouched dates)
    - Merges slots within each date (preserves existing slots, adds new ones)
    - Merges slot properties when there are conflicts (combines old and new properties)

    Example: If existing data has date "2024-01-15" with "slot_1", and you send
    "2024-01-15" with "slot_2", the result will have both "slot_1" and "slot_2".
    If you send updates to "slot_1", only the specified properties will be updated.

    Args:
        slot_id: The event's slot ID
        slot_request: Event slot update request data (will be merged with existing data)
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

    # Validate slot dates against event date range
    is_valid, error_message = validate_slot_dates_against_event(
        slot_request.slot_data, event.start_date, event.end_date
    )
    if not is_valid:
        return invalid_slot_data_response(error_message)

    # Get existing slot to preview the merge result
    existing_slot = await get_event_slot(db, slot_id)
    if not existing_slot:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Event slot not found",
            log_error=True,
        )

    # Preview the merged data to validate total slot count
    merged_data = deep_merge_slot_data(
        existing_slot.slot_data or {}, slot_request.slot_data
    )

    # Validate merged data doesn't exceed slot limits
    total_merged_slots = 0
    for date_key, date_slots in merged_data.items():
        if isinstance(date_slots, dict):
            total_merged_slots += len(date_slots)

    if total_merged_slots > 100:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"After merging, total number of individual slots ({total_merged_slots}) would exceed maximum limit (100)",
            log_error=True,
        )

    # Validate all dates in merged data are within event date range
    is_merged_valid, merged_error = validate_slot_dates_against_event(
        merged_data, event.start_date, event.end_date
    )
    if not is_merged_valid:
        return invalid_slot_data_response(f"After merging: {merged_error}")

    # Update the event slot with proper JSONB merge logic
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


@router.delete("/delete/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def delete_event_slot_endpoint(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Delete an existing event slot.

    This endpoint deletes an event slot and all its associated data.
    This action is irreversible.

    Args:
        slot_id: The event's slot ID
        db: Database session

    Returns:
        JSONResponse: Success message confirming deletion

    Raises:
        404: If the referenced event or slot doesn't exist
        500: If slot deletion fails
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    # Check if slot exists
    existing_slot = await check_slot_exists_for_event(db, slot_id)
    if not existing_slot:
        return slot_not_found_response()

    # Delete the event slot
    deleted = await delete_event_slot(db, slot_id)
    if not deleted:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to delete event slot",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slot deleted successfully",
    )


@router.patch("/toggle-status/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def toggle_slot_status_endpoint(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Toggle the status of an event slot (activate/deactivate).

    This endpoint toggles the slot_status field between True and False.
    Active slots are available for booking, inactive slots are not.

    Args:
        slot_id: The event's slot ID
        db: Database session

    Returns:
        JSONResponse: Success message with updated slot data

    Raises:
        404: If the referenced event or slot doesn't exist
        500: If status update fails
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    # Get current slot to check previous status
    current_slot = await get_event_slot(db, slot_id)
    if not current_slot:
        return slot_not_found_response()

    previous_status = current_slot.slot_status

    # Toggle the slot status
    updated_slot = await toggle_slot_status(db, slot_id)
    if not updated_slot:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to toggle slot status",
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

    response_data = SlotStatusToggleResponse(
        slot=slot_response,
        message=f"Slot status changed from {'active' if previous_status else 'inactive'} to {'active' if updated_slot.slot_status else 'inactive'}",
        previous_status=previous_status,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot status updated successfully",
        data=response_data.model_dump(),
    )


@router.get("/date-details/{slot_id}/{date}", status_code=status.HTTP_200_OK)
@exception_handler
async def get_slot_date_details_endpoint(
    slot_id: str,
    date: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get detailed information for a specific slot and date.

    This endpoint returns comprehensive information about slots for a specific date,
    including event details, slot count, capacity, and revenue potential.

    Args:
        slot_id: The event's slot ID
        date: Date in YYYY-MM-DD format
        db: Database session

    Returns:
        JSONResponse: Detailed slot and event information for the specified date

    Raises:
        400: If date format is invalid
        404: If the event, slot, or date is not found
        500: If retrieval fails
    """
    # Get slot date details
    slot_details = await get_slot_date_details(db, slot_id, date)

    if not slot_details:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"No slot data found for slot_id '{slot_id}' and date '{date}'",
            log_error=True,
        )

    # Prepare response data
    response_data = SlotDateDetailsResponse(**slot_details)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot date details retrieved successfully",
        data=response_data.model_dump(),
    )
