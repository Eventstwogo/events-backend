# permissions.py
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from rbac_service.schemas import (
    CreatePermission,
    PermissionDetails,
    PermissionUpdate,
)
from shared.core.api_response import api_response
from shared.db.models import Permission
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import generate_digits_lowercase
from shared.utils.validators import is_single_reserved_word

router = APIRouter()


@router.post("", summary="Create a new permission")
@exception_handler
async def create_permission(
    permission: CreatePermission,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Permission).where(
            Permission.permission_name == permission.permission_name
        )
    )
    existing_permission: Permission | None = result.scalars().first()
    if existing_permission:
        if existing_permission.permission_status is False:
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Permission with this name already exists.",
                log_error=True,
            )

        # Reactivate soft-deleted permission
        existing_permission.permission_status = False
        existing_permission.permission_tstamp = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_permission)

        return api_response(
            status_code=status.HTTP_200_OK,
            message="Soft-deleted permission reactivated successfully.",
            data={"permission_id": existing_permission.permission_id},
        )

    if is_single_reserved_word(permission.permission_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in permission names.",
        )

    # Create new permission
    permission_id = generate_digits_lowercase()
    new_permission = Permission(
        permission_id=permission_id,
        permission_name=permission.permission_name,
        permission_status=False,
        permission_tstamp=datetime.now(timezone.utc),
    )

    db.add(new_permission)
    await db.commit()
    await db.refresh(new_permission)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Permission created successfully.",
        data={"permission_id": new_permission.permission_id},
    )


@router.get(
    "",
    response_model=List[PermissionDetails],
    summary="Get permissions by active status",
)
@exception_handler
async def get_permissions(
    is_active: Optional[bool] = Query(
        None, description="Filter by active status"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    query = select(Permission)

    if is_active is not None:
        query = query.where(Permission.permission_status == is_active)

    result = await db.execute(query)
    permissions = result.scalars().all()

    if not permissions:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No permissions found for the given status.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Permissions retrieved successfully.",
        data=permissions,
    )


@router.get("/search", summary="Find permission by name")
@exception_handler
async def get_permission_id_by_name(
    permission_name: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Permission).where(Permission.permission_name == permission_name)
    )
    permission = result.scalars().first()

    if not permission:
        return api_response(
            status_code=404,
            message="Permission not found.",
            log_error=True,
        )

    return api_response(
        status_code=200,
        message="Permission ID retrieved successfully.",
        data={"permission_id": permission.permission_id},
    )


@router.put("/{permission_id}", summary="Update permission details")
@exception_handler
async def update_permission(
    permission_id: str,
    update_data: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Permission).where(Permission.permission_id == permission_id)
    )
    permission = result.scalars().first()

    if not permission:
        return api_response(
            status_code=404,
            message="Permission not found.",
            log_error=True,
        )

    if is_single_reserved_word(update_data.permission_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in permission names.",
        )

    if update_data.permission_name:
        # Check for duplicate permission_name in a different permission
        duplicate_check = await db.execute(
            select(Permission).where(
                Permission.permission_name == update_data.permission_name,
                Permission.permission_id != permission_id,
            )
        )
        duplicate_permission = duplicate_check.scalars().first()

        if duplicate_permission:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="A permission with this name already exists.",
                log_error=False,
            )

        permission.permission_name = update_data.permission_name

    await db.commit()
    await db.refresh(permission)

    return api_response(
        status_code=200,
        message="Permission updated successfully.",
        data=permission,
    )


@router.patch("/{permission_id}/status", summary="Update permission status")
@exception_handler
async def update_permission_status(
    permission_id: str,
    perm_status: bool = Query(..., description="Set permission status"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Permission).where(Permission.permission_id == permission_id)
    )
    permission = result.scalars().first()

    if not permission:
        return api_response(
            status_code=404,
            message="Permission not found.",
            log_error=True,
        )

    permission.permission_status = perm_status
    await db.commit()
    await db.refresh(permission)

    return api_response(
        status_code=200,
        message=f"Permission status updated to {'Inactive' if perm_status else 'Active'}.",
        data=permission,
    )


@router.delete("/{permission_id}", summary="Delete a permission (soft or hard)")
@exception_handler
async def delete_permission(
    permission_id: str,
    hard_delete: bool = Query(
        False, description="Set to true for permanent (hard) delete"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(Permission).where(Permission.permission_id == permission_id)
    )
    permission = result.scalars().first()

    if not permission:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Permission not found.",
            log_error=True,
        )

    # Handle soft-deleted case
    if permission.permission_status is True:
        if not hard_delete:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Permission is already soft-deleted.",
                log_error=False,
            )
        # Proceed with hard delete
        await db.delete(permission)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Permission permanently deleted (hard delete).",
        )

    # Execute hard or soft delete
    if hard_delete:
        await db.delete(permission)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Permission permanently deleted (hard delete).",
        )

    # Soft delete
    permission.permission_status = True
    await db.commit()
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Permission soft-deleted successfully.",
    )
