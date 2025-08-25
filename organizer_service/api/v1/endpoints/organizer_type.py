from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from organizer_service.schemas.organizer_type import (
    OrganizerTypeCreateRequest,
    OrganizerTypeResponse,
    OrganizerTypeUpdateRequest,
    UpdateStatusRequest,
)
from organizer_service.services.organizer_type import (
    create_organizer_type_service,
    list_active_organizer_types_service,
    list_organizer_types_service,
    update_organizer_type_service,
    update_organizer_type_status_service,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Organizer Type",
)
@exception_handler
async def create_organizer_type(
    request: OrganizerTypeCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        new_type = await create_organizer_type_service(db, request)
    except ValueError as e:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            log_error=True,
        )

    response_data = OrganizerTypeResponse.model_validate(new_type)
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Organizer type created successfully",
        data=response_data.model_dump(),
    )


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    summary="Get all Organizer Types",
)
@exception_handler
async def get_all_organizer_types(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    organizer_types = await list_organizer_types_service(db)
    response_data = [
        OrganizerTypeResponse.model_validate(ot).model_dump()
        for ot in organizer_types
    ]
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Fetched all organizer types successfully",
        data=response_data,
    )


@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    summary="Get all active Organizer Types",
)
@exception_handler
async def get_active_organizer_types(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    organizer_types = await list_active_organizer_types_service(db)
    response_data = [
        OrganizerTypeResponse.model_validate(ot).model_dump()
        for ot in organizer_types
    ]
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Fetched active organizer types successfully",
        data=response_data,
    )


@router.put(
    "/update/{type_id}",
    status_code=status.HTTP_200_OK,
    summary="Update an Organizer Type name",
)
@exception_handler
async def update_organizer_type(
    type_id: str,
    update_data: OrganizerTypeUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        updated_type = await update_organizer_type_service(
            db, type_id, update_data.new_name
        )
    except ValueError as e:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
            log_error=True,
        )

    response_data = OrganizerTypeResponse.model_validate(updated_type)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Organizer type updated successfully",
        data=response_data.model_dump(),
    )


@router.patch(
    "/status/{type_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Organizer Type Status",
)
@exception_handler
async def update_organizer_type_status(
    type_id: str,
    request: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    try:
        updated_type = await update_organizer_type_status_service(
            db, type_id, request.status
        )
    except ValueError as e:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=str(e),
        )

    response_data = OrganizerTypeResponse.model_validate(updated_type)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Organizer type status updated successfully",
        data=response_data.model_dump(),
    )
