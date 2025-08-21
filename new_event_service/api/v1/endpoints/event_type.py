from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from new_event_service.schemas.event_type import (
    EventTypeCreateRequest,
    EventTypeResponse,
    EventTypeUpdateRequest,
    UpdateStatusRequest,
)
from new_event_service.services.event_type import (
    create_event_type_service,
    list_active_event_types_service,
    list_event_types_service,
    update_event_type_service,
    update_event_type_status_service,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Event Type",
)
@exception_handler
async def create_event_type(
    request: EventTypeCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        new_type = await create_event_type_service(db, request)
    except ValueError as e:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            log_error=True,
        )

    response_data = EventTypeResponse.model_validate(new_type)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Event type created successfully",
        data=response_data.model_dump(),
    )


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    summary="Get all Event Types",
)
@exception_handler
async def get_all_event_types(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    event_types = await list_event_types_service(db)

    response_data = [
        EventTypeResponse.model_validate(et).model_dump() for et in event_types
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Fetched all event types successfully",
        data=response_data,
    )


@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    summary="Get all active Event Types",
)
@exception_handler
async def get_active_event_types(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    event_types = await list_active_event_types_service(db)

    response_data = [
        EventTypeResponse.model_validate(et).model_dump() for et in event_types
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Fetched active event types successfully",
        data=response_data,
    )


@router.put(
    "/update/{type_id}",
    status_code=status.HTTP_200_OK,
    summary="Update an Event Type name",
)
@exception_handler
async def update_event_type(
    type_id: str,
    update_data: EventTypeUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        updated_type = await update_event_type_service(
            db, type_id, update_data.new_name
        )
    except ValueError as e:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            log_error=True,
        )

    response_data = EventTypeResponse.model_validate(updated_type)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event type updated successfully",
        data=response_data.model_dump(),
    )


@router.patch(
    "/status/{type_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Event Type Status",
)
@exception_handler
async def update_event_type_status(
    type_id: str,
    request: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        updated_type = await update_event_type_status_service(
            db, type_id, request.status
        )
    except ValueError as e:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=str(e),
        )

    response_data = EventTypeResponse.model_validate(updated_type)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event type status updated successfully",
        data=response_data.model_dump(),
    )
