from typing import List, Optional

from fastapi import APIRouter, Depends, Form, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.schemas.admin_user import AdminUserResponse
from admin_service.services.response_builders import user_not_found_response
from admin_service.services.user_service import get_user_by_id
from shared.core.api_response import api_response
from shared.db.models import AdminUser, Role
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url
from shared.utils.username_validators import UsernameValidator
from shared.utils.validators import (
    normalize_whitespace,
    validate_length_range,
)

router = APIRouter()


@router.get("", response_model=List[AdminUserResponse])
@exception_handler
async def get_admin_users(
    is_deleted: Optional[bool] = Query(
        None,
        description=(
            "Filter by account status: false=active, true=inactive, omit=all"
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a list of admin users with optional filtering by account status.

    Args:
        is_deleted: Optional filter for account status

    Returns:
        JSONResponse: List of admin users with their details
    """
    # Create a select statement with the columns we want
    stmt = select(AdminUser, Role.role_name).select_from(AdminUser).join(Role)

    if is_deleted is False:
        stmt = stmt.where(AdminUser.is_deleted.is_(False))  # fetch active users
    elif is_deleted is True:
        stmt = stmt.where(
            AdminUser.is_deleted.is_(True)
        )  # fetch inactive users

    result = await db.execute(stmt)
    rows = result.all()
    if not rows:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No admin users found for the given status.",
            log_error=True,
        )

    # Map the query result to AdminUserResponse
    users = [
        AdminUserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role_id=user.role_id,
            role_name=role_name,
            profile_picture=get_media_url(user.profile_picture),
            is_deleted=user.is_deleted,
            last_login=user.last_login,
            created_at=user.created_at,
        )
        for user, role_name in rows
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin users fetched successfully.",
        data=users,
    )


@router.get("/{user_id}")
@exception_handler
async def get_admin_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific admin user by their ID.

    Args:
        user_id: The ID of the user to retrieve

    Returns:
        JSONResponse: Admin user details
    """
    # Validate user ID format
    if not user_id or len(user_id) != 6:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid user ID format. Must be 6 characters long.",
            log_error=True,
        )

    # Query with only requested fields
    stmt = (
        select(AdminUser, Role.role_name)
        .select_from(AdminUser)
        .join(Role, AdminUser.role_id == Role.role_id)
        .where(AdminUser.user_id == user_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    user, role_name = row

    # Create response object with only requested fields
    user_data = {
        "username": user.username.title(),
        "email": user.email,
        "role_id": user.role_id,
        "role_name": role_name,
        "profile_picture": get_media_url(user.profile_picture),
        "status": user.is_deleted,
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin user fetched successfully.",
        data=user_data,
    )


@router.put("/{user_id}", summary="Update username and role by user ID")
@exception_handler
async def update_username_and_role(
    user_id: str,
    new_username: Optional[str] = Form(
        default=None,
        title="New Username",
        description="New username for the admin user (optional)",
    ),
    new_role_id: Optional[str] = Form(
        default=None,
        title="New Role ID",
        description="New role ID for the admin user (optional)",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Validate and sanitize form inputs
    # Skip validation if username is None or empty string
    if new_username is not None:
        new_username = UsernameValidator(
            min_length=4, max_length=32, max_spaces=2
        ).validate(new_username)

    # Skip validation if role_id is None or empty string
    if new_role_id is not None:
        new_role_id = normalize_whitespace(new_role_id)
        if not new_role_id:  # If empty after normalization, set to None to skip
            new_role_id = None
        else:
            # Validate only if not empty
            if not validate_length_range(new_role_id, 6, 6):
                return api_response(
                    status.HTTP_400_BAD_REQUEST,
                    "Role ID must be exactly 6 characters long.",
                    log_error=True,
                )

    # Fetch user
    result = await db.execute(
        select(AdminUser).where(AdminUser.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found.", log_error=True
        )

    if user.is_deleted:
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "Cannot update inactive user.",
            log_error=True,
        )

    # Detect no changes
    if (not new_username or new_username.lower() == user.username) and (
        not new_role_id or new_role_id == user.role_id
    ):
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "No changes detected.",
            log_error=False,
        )

    role_name = None

    # === Update username ===
    if new_username and new_username.lower() != user.username:
        # Check for existing username using hash-based query (case-insensitive)
        query = AdminUser.by_username_query(new_username.lower())
        existing_user = await db.execute(query)
        existing_user = existing_user.scalar_one_or_none()
        if existing_user and existing_user.user_id != user_id:
            return api_response(
                status.HTTP_409_CONFLICT,
                "Username already exists.",
                log_error=True,
            )
        user.username = new_username.lower()

    # === Update role ===
    if new_role_id and new_role_id != user.role_id:
        role_result = await db.execute(
            select(Role).where(Role.role_id == new_role_id)
        )
        role = role_result.scalar_one_or_none()
        if not role:
            return api_response(
                status.HTTP_404_NOT_FOUND, "Role not found.", log_error=True
            )

        if role.role_status:
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Cannot assign an inactive role.",
                log_error=True,
            )

        # Enforce only one superadmin from DB role name
        role_name = role.role_name
        if role_name.lower() == "superadmin":
            superadmin_check = await db.execute(
                select(AdminUser)
                .join(Role, AdminUser.role_id == Role.role_id)
                .where(
                    Role.role_name.ilike("superadmin"),
                    AdminUser.user_id != user.user_id,
                )
            )
            if superadmin_check.scalar_one_or_none():
                return api_response(
                    status.HTTP_400_BAD_REQUEST,
                    "A Superadmin already exists.Only one Superadmin is allowed in the system.",
                    log_error=True,
                )

        user.role_id = new_role_id

    await db.commit()
    await db.refresh(user)

    # Fetch role name if not updated
    if not role_name:
        role_result = await db.execute(
            select(Role).where(Role.role_id == user.role_id)
        )
        role = role_result.scalar_one_or_none()
        role_name = role.role_name if role else None

    return api_response(
        status.HTTP_200_OK,
        "User updated successfully.",
        data={
            "user_id": user.user_id,
            "username": user.username,
            "role_id": user.role_id,
            "role_name": role_name,
        },
    )


@router.patch("/deactivate/{user_id}")
@exception_handler
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Soft delete (deactivate) a user by setting is_deleted to True.

    Args:
        user_id: The ID of the user to deactivate

    Returns:
        JSONResponse: Success message confirming user deactivation
    """
    # Find user using the common utility function
    user = await get_user_by_id(db, user_id)
    if not user:
        return user_not_found_response()

    if user.is_deleted:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is already deactivated.",
            log_error=True,
        )

    user.is_deleted = True
    await db.commit()
    await db.refresh(user)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="User soft-deleted successfully.",
    )


@router.patch("/reactivate/{user_id}")
@exception_handler
async def reactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Restore (reactivate) a user by setting is_deleted to False.

    Args:
        user_id: The ID of the user to reactivate

    Returns:
        JSONResponse: Success message confirming user restoration
    """
    # Find user using the common utility function
    user = await get_user_by_id(db, user_id)
    if not user:
        return user_not_found_response()

    if not user.is_deleted:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is already active.",
            log_error=True,
        )

    user.is_deleted = False
    await db.commit()
    await db.refresh(user)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="User restored successfully.",
    )


@router.delete("/{user_id}")
@exception_handler
async def hard_delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Permanently delete a user from the database.

    Args:
        user_id: The ID of the user to permanently delete

    Returns:
        JSONResponse: Success message confirming permanent deletion
    """
    # Find user using the common utility function
    user = await get_user_by_id(db, user_id)
    if not user:
        return user_not_found_response()

    if user.role.role_name.lower() == "superadmin":
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Superadmins cannot be permanently deleted.",
            log_error=True,
        )

    await db.delete(user)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="User permanently deleted.",
    )
