from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.db.models import Permission, Role, RolePermission
from shared.db.sessions.database import get_db
from rbac_service.schemas import (
    CreateRolePermission,
    RolePermissionDetails,
    RolePermissionUpdate,
)
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post("/", summary="Create a new role-permission relationship")
@exception_handler
async def create_role_permission(
    role_permission: CreateRolePermission,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    permission_result = await db.execute(
        select(Permission).where(
            Permission.permission_id == role_permission.permission_id
        )
    )
    permission = permission_result.scalars().first()
    if not permission:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Invalid permission ID or permission not found.",
            log_error=True,
        )

    role_result = await db.execute(
        select(Role).where(Role.role_id == role_permission.role_id)
    )
    role = role_result.scalars().first()
    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Invalid role ID or role not found.",
            log_error=True,
        )

    # Check for existing role-permission relationship
    existing_rp_result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_permission.role_id,
            RolePermission.permission_id == role_permission.permission_id,
        )
    )
    existing_rp = existing_rp_result.scalars().first()

    if existing_rp:
        if existing_rp.rp_status is False:
            # Already active, no need to create
            return api_response(
                status_code=status.HTTP_200_OK,
                message="This role-permission relationship is already active.",
                data={"id": existing_rp.id},
            )

        # Reactivate the existing one
        existing_rp.rp_status = False
        existing_rp.timestamp = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_rp)
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Existing role-permission reactivated.",
            data={"id": existing_rp.id},
        )

    new_role_perm = RolePermission(
        role_id=role_permission.role_id,
        permission_id=role_permission.permission_id,
        rp_status=False,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(new_role_perm)
    await db.commit()
    await db.refresh(new_role_perm)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Role-permission created successfully.",
        data={"id": new_role_perm.id},
    )


@router.get(
    "/",
    response_model=List[RolePermissionDetails],
    summary="Get role-permission records by status",
)
@exception_handler
async def get_all_role_permissions(
    is_active: Optional[bool] = Query(
        None, description="Filter by active status"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    query = select(RolePermission).order_by(RolePermission.id)

    if is_active is not None:
        query = query.where(RolePermission.rp_status == is_active)

    result = await db.execute(query)
    role_permissions = result.scalars().all()

    if not role_permissions:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No role-permissions found for the given status.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Role-permissions retrieved successfully.",
        data=role_permissions,
    )


@router.get("/{record_id}", summary="Get a specific role-permission record")
@exception_handler
async def get_specific_role_permission(
    record_id: int,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(RolePermission).where(RolePermission.id == record_id)
    )
    role_permission = result.scalars().first()

    if not role_permission:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role-permission not found.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Role-permission retrieved successfully.",
        data=role_permission,
    )


@router.put("/{record_id}", summary="Update role-permission relationship")
@exception_handler
async def update_role_permission(
    record_id: int,
    update_data: RolePermissionUpdate,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(RolePermission).where(RolePermission.id == record_id)
    )
    role_permission = result.scalars().first()

    if not role_permission:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role-permission not found.",
            log_error=True,
        )

    if update_data.role_id:
        role_permission.role_id = update_data.role_id

    if update_data.permission_id:
        role_permission.permission_id = update_data.permission_id

    await db.commit()
    await db.refresh(role_permission)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Role-permission updated successfully.",
        data=role_permission,
    )


@router.patch(
    "/{record_id}/status", summary="Update status of a role-permission"
)
@exception_handler
async def update_role_permission_status(
    record_id: int,
    role_perm_status: bool = Query(
        False, description="Set status to active/inactive"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(RolePermission).where(RolePermission.id == record_id)
    )
    role_permission = result.scalars().first()

    if not role_permission:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role-permission not found.",
            log_error=True,
        )

    role_permission.rp_status = role_perm_status
    await db.commit()
    await db.refresh(role_permission)

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Status updated to {'Inactive' if role_perm_status else 'Active'}.",
        data=role_permission,
    )


@router.delete(
    "/{record_id}",
    summary="Delete a role-permission relationship (soft or hard)",
)
@exception_handler
async def delete_role_permission(
    record_id: int,
    hard_delete: bool = Query(
        False, description="Set to true for permanent delete"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    result = await db.execute(
        select(RolePermission).where(RolePermission.id == record_id)
    )
    role_permission = result.scalars().first()

    if not role_permission:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role-permission not found.",
            log_error=True,
        )

    if role_permission.rp_status is True:
        if not hard_delete:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Role-permission is already soft-deleted.",
                log_error=False,
            )
        # Hard delete allowed if already soft-deleted
        await db.delete(role_permission)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Role-permission permanently deleted (hard delete).",
        )

    if hard_delete:
        await db.delete(role_permission)
        await db.commit()
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Role-permission permanently deleted (hard delete).",
        )

    # Soft delete
    role_permission.rp_status = True
    await db.commit()
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Role-permission soft-deleted successfully.",
    )
