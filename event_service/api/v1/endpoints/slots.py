from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.slots import (
    SlotCreateRequest,
    SlotFilters,
    SlotListResponse,
    SlotResponse,
    SlotStatusUpdateRequest,
    SlotUpdateRequest,
)
from event_service.services.events import (
    fetch_event_by_id,
)
from event_service.services.response_builder import (
    event_not_found_response,
    invalid_slot_data_response,
    slot_created_successfully_response,
    slot_deleted_successfully_response,
    slot_not_found_response,
    slot_order_already_exists_response,
    slot_status_updated_successfully_response,
    slot_updated_successfully_response,
)
from event_service.services.slots import (
    check_slot_exists,
    check_slot_order_exists,
    count_slots_by_event,
    create_slot,
    delete_slot,
    fetch_slot_by_event_and_slot_id,
    fetch_slot_by_id,
    fetch_slots_by_event_id,
    get_next_slot_order,
    get_slot_statistics,
    update_slot,
    update_slot_status,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post("/{event_id}/slots/", status_code=status.HTTP_201_CREATED)
@exception_handler
async def create_event_slot(
    event_id: str,
    payload: SlotCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a slot to a specific event"""

    # Check if event exists
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Check if slot order already exists for this event
    if await check_slot_order_exists(db, event_id, payload.slot_order):
        return slot_order_already_exists_response()

    # Create the slot
    new_slot = await create_slot(
        db=db,
        event_id=event_id,
        slot_order=payload.slot_order,
        slot_data=payload.slot_data,
        slot_status=payload.slot_status,
    )

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Slot created successfully",
        data={
            "slot_id": new_slot.slot_ids,
            "event_id": new_slot.event_id,
            "slot_order": new_slot.slot_order,
        },
    )


@router.get(
    "/{event_id}/slots/",
    status_code=status.HTTP_200_OK,
    response_model=SlotListResponse,
)
@exception_handler
async def get_event_slots(
    event_id: str,
    status_filter: Optional[bool] = Query(
        None, alias="status", description="Filter by slot status"
    ),
    sort_by: str = Query(default="slot_order", description="Sort field"),
    sort_order: str = Query(
        default="asc", regex="^(asc|desc)$", description="Sort order"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get all slots for a specific event (ordered by slot_order)"""

    # Check if event exists
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Fetch slots with filters
    slots = await fetch_slots_by_event_id(
        db=db,
        event_id=event_id,
        status=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Get total count
    total = await count_slots_by_event(db, event_id)

    # Convert to response format
    slot_responses = [SlotResponse.model_validate(slot) for slot in slots]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slots retrieved successfully",
        data={
            "slots": slot_responses,
            "total": total,
            "event_id": event_id,
        },
    )


@router.get(
    "/{event_id}/slots/{slot_id}",
    status_code=status.HTTP_200_OK,
    response_model=SlotResponse,
)
@exception_handler
async def get_slot_details(
    event_id: str,
    slot_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve slot details"""

    # Check if event exists
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Fetch slot by event_id and slot_id
    slot = await fetch_slot_by_event_and_slot_id(db, event_id, slot_id)
    if not slot:
        return slot_not_found_response()

    # Convert to response format
    slot_response = SlotResponse.model_validate(slot)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot retrieved successfully",
        data=slot_response.model_dump(),
    )


@router.put("/{event_id}/slots/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def update_slot_details(
    event_id: str,
    slot_id: int,
    payload: SlotUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a slot (slot_data, order, status, etc.)"""

    # Check if event exists
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Check if slot exists and belongs to the event
    existing_slot = await fetch_slot_by_event_and_slot_id(db, event_id, slot_id)
    if not existing_slot:
        return slot_not_found_response()

    # Prepare update data
    update_data = {}

    # Validate slot order if provided
    if payload.slot_order is not None:
        # Check if new slot order conflicts with existing slots (excluding current slot)
        if await check_slot_order_exists(
            db, event_id, payload.slot_order, exclude_slot_id=slot_id
        ):
            return slot_order_already_exists_response()
        update_data["slot_order"] = payload.slot_order

    # Add other fields
    if payload.slot_data is not None:
        update_data["slot_data"] = payload.slot_data

    if payload.slot_status is not None:
        update_data["slot_status"] = payload.slot_status

    # Update the slot
    updated_slot = await update_slot(db, slot_id, update_data)
    if not updated_slot:
        return invalid_slot_data_response("Failed to update slot")

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot updated successfully",
        data={
            "slot_id": updated_slot.slot_ids,
            "event_id": updated_slot.event_id,
            "updated_fields": list(update_data.keys()),
        },
    )


@router.patch(
    "/{event_id}/slots/{slot_id}/status", status_code=status.HTTP_200_OK
)
@exception_handler
async def toggle_slot_status(
    event_id: str,
    slot_id: int,
    payload: SlotStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Toggle/Update slot status (active/inactive)"""

    # Check if event exists
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Check if slot exists and belongs to the event
    existing_slot = await fetch_slot_by_event_and_slot_id(db, event_id, slot_id)
    if not existing_slot:
        return slot_not_found_response()

    # Update slot status
    updated_slot = await update_slot_status(db, slot_id, payload.slot_status)
    if not updated_slot:
        return invalid_slot_data_response("Failed to update slot status")

    status_text = "active" if payload.slot_status else "inactive"

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Slot status updated to {status_text}",
        data={
            "slot_id": updated_slot.slot_ids,
            "event_id": updated_slot.event_id,
            "slot_status": updated_slot.slot_status,
            "status_text": status_text,
        },
    )


@router.delete("/{event_id}/slots/{slot_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def delete_event_slot(
    event_id: str,
    slot_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a slot"""

    # Check if event exists
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Check if slot exists and belongs to the event
    existing_slot = await fetch_slot_by_event_and_slot_id(db, event_id, slot_id)
    if not existing_slot:
        return slot_not_found_response()

    # Delete the slot
    success = await delete_slot(db, slot_id)
    if not success:
        return invalid_slot_data_response("Failed to delete slot")

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot deleted successfully",
        data={"slot_id": slot_id, "event_id": event_id, "deleted": True},
    )


@router.get("/{event_id}/slots/statistics", status_code=status.HTTP_200_OK)
@exception_handler
async def get_event_slot_statistics(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get statistics about slots for an event"""

    # Check if event exists
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Get slot statistics
    stats = await get_slot_statistics(db, event_id)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot statistics retrieved successfully",
        data=stats,
    )
