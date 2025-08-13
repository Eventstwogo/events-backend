from datetime import date, datetime, timedelta
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
    event_not_created_response,
    event_not_found_response,
    event_slots_not_created_response,
    invalid_slot_data_response,
    slot_already_exists_response,
    slot_not_found_response,
)
from event_service.services.slots import (
    check_event_created_status_by_id,
    check_event_exists_by_slot_id,
    check_event_slot_created_status_by_id,
    check_slot_exists_for_event,
    create_event_slot,
    deep_merge_slot_data,
    delete_event_slot,
    get_event_slot,
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
                    error_msg = (
                        f"Slot date '{date_key}' is before event start date "
                        f"({event_start_date}). All slot dates must be within "
                        f"the event's date range."
                    )
                    return (False, error_msg)

                if slot_date > event_end_date:
                    error_msg = (
                        f"Slot date '{date_key}' is after event end date "
                        f"({event_end_date}). All slot dates must be within "
                        f"the event's date range."
                    )
                    return (False, error_msg)

            except ValueError as e:
                return False, str(e)

        return True, ""

    except Exception as e:
        return False, f"Error validating slot dates: {str(e)}"


def populate_missing_dates_and_filter(
    slot_data: dict, event_start_date: date, event_end_date: date
) -> dict:
    """
    Populate missing dates with empty dictionaries and remove dates outside event range.

    Args:
        slot_data: Original slot data dictionary
        event_start_date: Event's start date
        event_end_date: Event's end date

    Returns:
        dict: Modified slot data with all event dates populated
    """
    # Create a new dictionary to store the processed data
    processed_slot_data = {}

    # First, filter existing slot_data to only include dates within event range
    for date_key, date_slots in slot_data.items():
        try:
            slot_date = parse_slot_date(date_key).date()
            # Only include dates that are within the event date range
            if event_start_date <= slot_date <= event_end_date:
                processed_slot_data[date_key] = date_slots
        except ValueError:
            # Skip invalid date formats
            continue

    # Generate all dates between event start and end dates
    current_date = event_start_date
    while current_date <= event_end_date:
        date_key = current_date.strftime("%Y-%m-%d")

        # If date is not present in processed data, add it with empty dictionary
        if date_key not in processed_slot_data:
            processed_slot_data[date_key] = {}

        current_date += timedelta(days=1)

    return processed_slot_data


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Integrated in Admin and Organizer frontend",
)
@exception_handler
async def create_event_slot_endpoint(
    slot_request: EventSlotCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new event slot with nested date/slot structure.

    This endpoint creates a new slot for an existing event. The slot contains
    scheduling and configuration data organized by dates and individual slots.

    The system validates that:
    - All provided slot dates are within the event's date range
    - Slot data structure is valid
    - Slot limits are not exceeded

    The system automatically:
    - Populates all dates between event start and end dates with empty dictionaries if not provided
    - Ensures all event dates are present in the final slot_data

    Args:
        slot_request: Event slot creation request data
        db: Database session

    Returns:
        JSONResponse: Success message with created slot data

    Raises:
        400: If validation fails, slot already exists, or dates are outside event range
        404: If the referenced event doesn't exist
        500: If slot creation fails
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_request.slot_id)
    if not event:
        return event_not_found_response()

    slot_created_event = await check_event_created_status_by_id(
        db, event.slot_id
    )
    if not slot_created_event:
        return event_not_created_response()

    # Check if slot already exists for this event
    existing_slot = await check_slot_exists_for_event(db, slot_request.slot_id)
    if existing_slot:
        return slot_already_exists_response()

    # Validate slot data structure (basic validation)
    if not slot_request.slot_data:
        return invalid_slot_data_response("Slot data cannot be empty")

    # Validate that slot_data has the correct nested structure
    for date_key, date_slots in slot_request.slot_data.items():
        if not isinstance(date_slots, dict):
            return invalid_slot_data_response(
                f"Invalid slot structure for date {date_key}"
            )

    # Validate slot dates against event date range BEFORE processing
    is_valid, error_message = validate_slot_dates_against_event(
        slot_request.slot_data, event.start_date, event.end_date
    )
    if not is_valid:
        return invalid_slot_data_response(error_message)

    # Populate missing dates and filter out dates outside event range
    slot_request.slot_data = populate_missing_dates_and_filter(
        slot_request.slot_data, event.start_date, event.end_date
    )

    # Count total slots after processing
    total_slots_count = 0
    for date_key, date_slots in slot_request.slot_data.items():
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
        event=event,
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


@router.put(
    "/update/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Integrated in Admin and Organizer frontend",
)
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

    slot_created_event = await check_event_slot_created_status_by_id(
        db, slot_id
    )
    if not slot_created_event:
        return event_slots_not_created_response()

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

    # # Validate slot dates against event date range
    # is_valid, error_message = validate_slot_dates_against_event(
    #     slot_request.slot_data, event.start_date, event.end_date
    # )
    # if not is_valid:
    #     return invalid_slot_data_response(error_message)

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
        error_msg = (
            f"After merging, total number of individual slots "
            f"({total_merged_slots}) would exceed maximum limit (100)"
        )
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error_msg,
            log_error=True,
        )

    # # Validate all dates in merged data are within event date range
    # is_merged_valid, merged_error = validate_slot_dates_against_event(
    #     merged_data, event.start_date, event.end_date
    # )
    # if not is_merged_valid:
    #     return invalid_slot_data_response(f"After merging: {merged_error}")

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


@router.get(
    "/get/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Integrated in Admin and Organizer frontend",
)
@exception_handler
async def get_event_slot_endpoint(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get an existing event slot data.

    This endpoint returns the complete event slot data with all dates within
    the event's date range populated (empty dictionaries for dates without slots).
    This ensures clients receive a consistent structure with all event dates present.

    Args:
        slot_id: The event's slot ID
        db: Database session

    Returns:
        JSONResponse: Event slot data with all event dates populated

    Raises:
        404: If the referenced event or slot doesn't exist
    """

    # Validate that the event exists
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    slot_created_event = await check_event_slot_created_status_by_id(
        db, slot_id
    )
    if not slot_created_event:
        return event_slots_not_created_response()

    # Get the event slot
    slot = await get_event_slot(db, slot_id)
    if not slot:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Event slot not found",
            log_error=True,
        )

    # Populate missing dates and filter slot data to ensure all event dates are present
    populated_slot_data = populate_missing_dates_and_filter(
        slot.slot_data or {}, event.start_date, event.end_date
    )

    # Prepare response data
    slot_response = EventSlotResponse(
        id=slot.id,
        slot_id=slot.slot_id,
        slot_data=populated_slot_data,
        slot_status=slot.slot_status,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slot retrieved successfully",
        data=slot_response.model_dump(),
    )


@router.delete(
    "/delete/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Not integrated in any frontend",
)
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

    slot_created_event = await check_event_slot_created_status_by_id(
        db, slot_id
    )
    if not slot_created_event:
        return event_slots_not_created_response()

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


@router.patch(
    "/toggle-status/{slot_id}",
    status_code=status.HTTP_200_OK,
    summary="Not integrated in any frontend",
)
@exception_handler
async def toggle_slot_status_endpoint(
    slot_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Toggle the status of an event slot (activate/deactivate).

    This endpoint toggles the slot_status field between True and False.
    Active slots are available for booking, inactive slots are not.

    The returned slot data includes all dates within the event's date range
    populated (empty dictionaries for dates without slots).

    Args:
        slot_id: The event's slot ID
        db: Database session

    Returns:
        JSONResponse: Success message with updated slot data (all dates populated)

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

    # Populate missing dates and filter slot data to ensure all event dates are present
    populated_slot_data = populate_missing_dates_and_filter(
        updated_slot.slot_data or {}, event.start_date, event.end_date
    )

    # Prepare response data
    slot_response = EventSlotResponse(
        id=updated_slot.id,
        slot_id=updated_slot.slot_id,
        slot_data=populated_slot_data,
        slot_status=updated_slot.slot_status,
        created_at=updated_slot.created_at,
        updated_at=updated_slot.updated_at,
    )

    status_message = (
        f"Slot status changed from {'active' if previous_status else 'inactive'} "
        f"to {'active' if updated_slot.slot_status else 'inactive'}"
    )
    response_data = SlotStatusToggleResponse(
        slot=slot_response,
        message=status_message,
        previous_status=previous_status,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot status updated successfully",
        data=response_data.model_dump(),
    )


@router.get(
    "/date-details/{slot_id}/{date}",
    status_code=status.HTTP_200_OK,
    summary="Not integrated in any frontend",
)
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

    The system automatically ensures all event dates are populated (even if empty),
    so this endpoint will return data for any date within the event's date range,
    showing empty slot data if no slots are configured for that date.

    Args:
        slot_id: The event's slot ID
        date: Date in YYYY-MM-DD format
        db: Database session

    Returns:
        JSONResponse: Detailed slot and event information for the specified date

    Raises:
        400: If date format is invalid or date is outside event range
        404: If the event or slot is not found
        500: If retrieval fails
    """
    # Validate that the event exists first to get event date range
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return event_not_found_response()

    slot_created_event = await check_event_slot_created_status_by_id(
        db, slot_id
    )
    if not slot_created_event:
        return event_slots_not_created_response()

    # Get the event slot
    slot = await get_event_slot(db, slot_id)
    if not slot:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Event slot not found",
            log_error=True,
        )

    # Populate missing dates and filter slot data to ensure all event dates are present
    populated_slot_data = populate_missing_dates_and_filter(
        slot.slot_data or {}, event.start_date, event.end_date
    )

    # Validate date format
    try:
        requested_date = parse_slot_date(date).date()
    except ValueError as e:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            log_error=True,
        )

    # Check if the requested date is within event date range
    if requested_date < event.start_date or requested_date > event.end_date:
        error_msg = (
            f"Date '{date}' is outside event date range "
            f"({event.start_date} to {event.end_date})"
        )
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error_msg,
            log_error=True,
        )

    # Get date slots (will be empty dict if no slots exist for this date)
    date_slots = populated_slot_data.get(date, {})

    # Calculate statistics for this date
    slots_count = len(date_slots)
    total_capacity = 0
    total_revenue_potential = 0.0

    for slot_key, slot_details in date_slots.items():
        if isinstance(slot_details, dict):
            capacity = slot_details.get("capacity", 0)
            price = slot_details.get("price", 0.0)

            # Ensure capacity and price are numeric
            try:
                capacity = int(capacity) if capacity else 0
                price = float(price) if price else 0.0
            except (ValueError, TypeError):
                capacity = 0
                price = 0.0

            total_capacity += capacity
            total_revenue_potential += capacity * price

    # Prepare slot details response
    slot_details = {
        "slot_id": slot_id,
        "event_date": date,
        "slots_count": slots_count,
        "slots_data": date_slots,
        "event_title": event.event_title,
        "event_id": event.event_id,
        "event_status": event.event_status,
        "slot_status": slot.slot_status,
        "total_capacity": total_capacity,
        "total_revenue_potential": round(total_revenue_potential, 2),
        "event_location": event.location,
        "is_online": event.is_online,
        "start_date": event.start_date,
        "end_date": event.end_date,
    }

    # Prepare response data
    response_data = SlotDateDetailsResponse(**slot_details)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot date details retrieved successfully",
        data=response_data.model_dump(),
    )
