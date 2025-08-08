from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.core.logging_config import get_logger
from shared.db.models import User
from shared.db.sessions.database import get_db
from shared.dependencies.user import get_current_active_user
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url
from user_service.schemas.user import UserMeOut
from user_service.services.response_builders import user_not_found_response
from user_service.services.user_service import get_user_by_id

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=List[UserMeOut], summary="Get all users")
@exception_handler
async def get_app_users(
    current_user: Annotated[User, Depends(get_current_active_user)],
    is_deleted: Optional[bool] = Query(
        None,
        description=(
            "Filter by account status: false=active, true=inactive, omit=all"
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a list of app users with optional filtering by account status.

    Args:
        current_user: The authenticated user making the request
        is_deleted: Optional filter for account status

    Returns:
        JSONResponse: List of app users with their details
    """
    # Create a select statement with the columns we want
    stmt = select(User)

    if is_deleted is False:
        stmt = stmt.where(User.is_deleted.is_(False))  # fetch active users
    elif is_deleted is True:
        stmt = stmt.where(User.is_deleted.is_(True))  # fetch inactive users

    result = await db.execute(stmt)
    users_data = result.scalars().all()
    if not users_data:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No app users found for the given status.",
            log_error=True,
        )

    # Map the query result to UserResponse
    users = [
        UserMeOut(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            profile_picture=user.profile_picture,
            is_deleted=user.is_deleted,
            days_180_flag=user.days_180_flag,
            last_login=user.last_login,
            created_at=user.created_at,
        )
        for user in users_data
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin users fetched successfully.",
        data=users,
    )


@router.get(
    "/for-admins", response_model=List[UserMeOut], summary="Get all users"
)
@exception_handler
async def get_app_users_for_admins(
    is_deleted: Optional[bool] = Query(
        None,
        description=(
            "Filter by account status: false=active, true=inactive, omit=all"
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a list of app users with optional filtering by account status.

    Args:
        current_user: The authenticated user making the request
        is_deleted: Optional filter for account status

    Returns:
        JSONResponse: List of app users with their details
    """
    # Create a select statement with the columns we want
    stmt = select(User)

    if is_deleted is False:
        stmt = stmt.where(User.is_deleted.is_(False))  # fetch active users
    elif is_deleted is True:
        stmt = stmt.where(User.is_deleted.is_(True))  # fetch inactive users

    result = await db.execute(stmt)
    users_data = result.scalars().all()
    if not users_data:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No app users found for the given status.",
            log_error=True,
        )

    # Map the query result to UserResponse
    users = [
        UserMeOut(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            profile_picture=user.profile_picture,
            is_deleted=user.is_deleted,
            days_180_flag=user.days_180_flag,
            last_login=user.last_login,
            created_at=user.created_at,
        )
        for user in users_data
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin users fetched successfully.",
        data=users,
    )


@router.get("/{user_id}", summary="Get user by ID")
@exception_handler
async def get_app_user_by_id(
    user_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific app user by their ID.

    Args:
        user_id: The ID of the user to retrieve
        current_user: The authenticated user making the request

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
    stmt = select(User).where(User.user_id == user_id)

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return user_not_found_response()

    # Create response object with only requested fields
    user_data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "profile_picture": get_media_url(user.profile_picture),
        "status": user.is_deleted,
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Admin user fetched successfully.",
        data=user_data,
    )


# @router.put("/{user_id}", summary="Update username by user ID")
# @exception_handler
# async def update_username(
#     user_id: str,
#     new_username: Optional[str] = Form(
#         default=None,
#         title="New Username",
#         description="New username for the app user (optional)",
#     ),
#     db: AsyncSession = Depends(get_db),
# ) -> JSONResponse:
#     # Validate and sanitize form inputs
#     # Skip validation if username is None or empty string
#     if new_username is not None:
#         new_username = normalize_whitespace(new_username)
#         if not new_username:  # If empty after normalization, set to None to skip
#             new_username = None
#         else:
#             # Validate only if not empty
#             if not is_valid_username(new_username, allow_spaces=True, allow_hyphens=True):
#                 return api_response(
#                     status.HTTP_400_BAD_REQUEST,
#                     "Username can only contain letters, numbers, spaces, and hyphens.",
#                     log_error=True,
#                 )
#             if not validate_length_range(new_username, 4, 32):
#                 return api_response(
#                     status.HTTP_400_BAD_REQUEST,
#                     "Username must be 4–32 characters long.",
#                     log_error=True,
#                 )
#             if contains_xss(new_username):
#                 return api_response(
#                     status.HTTP_400_BAD_REQUEST,
#                     "Username contains potentially malicious content.",
#                     log_error=True,
#                 )
#             if has_excessive_repetition(new_username, max_repeats=3):
#                 return api_response(
#                     status.HTTP_400_BAD_REQUEST,
#                     "Username contains excessive repeated characters.",
#                     log_error=True,
#                 )
#             if len(new_username) < 3 or not all(c.isalpha() for c in new_username[:3]):
#                 return api_response(
#                     status.HTTP_400_BAD_REQUEST,
#                     "First three characters of username must be letters.",
#                     log_error=True,
#                 )

#     # Fetch user
#     result = await db.execute(select(User).where(User.user_id == user_id))
#     user = result.scalar_one_or_none()

#     if not user:
#         return api_response(status.HTTP_404_NOT_FOUND, "User not found.", log_error=True)

#     if user.is_deleted:
#         return api_response(
#             status.HTTP_400_BAD_REQUEST,
#             "Cannot update inactive user.",
#             log_error=True,
#         )

#     # Detect no changes
#     if not new_username or new_username.lower() == user.username:
#         return api_response(
#             status.HTTP_400_BAD_REQUEST,
#             "No changes detected.",
#             log_error=False,
#         )

#     # === Update username ===
#     if new_username and new_username.lower() != user.username:
#         # Check for existing username using hash-based query (case-insensitive)
#         query = User.by_username_query(new_username.lower())
#         existing_user = await db.execute(query)
#         existing_user = existing_user.scalar_one_or_none()
#         if existing_user and existing_user.user_id != user_id:
#             return api_response(
#                 status.HTTP_409_CONFLICT,
#                 "Username already exists.",
#                 log_error=True,
#             )
#         user.username = new_username.lower()

#     return api_response(
#         status.HTTP_200_OK,
#         "User updated successfully.",
#         data={
#             "user_id": user.user_id,
#             "username": user.username,
#         },
#     )


@router.patch("/{user_id}/deactivate", summary="Deactivate user")
@exception_handler
async def deactivate_user(
    user_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Soft delete (deactivate) a user by setting is_deleted to True.

    Args:
        user_id: The ID of the user to deactivate
        current_user: The authenticated user making the request

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


@router.patch("/{user_id}/reactivate", summary="Reactivate user")
@exception_handler
async def reactivate_user(
    user_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Restore (reactivate) a user by setting is_deleted to False.

    Args:
        user_id: The ID of the user to reactivate
        current_user: The authenticated user making the request

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


@router.delete("/{user_id}", summary="Permanently delete user")
@exception_handler
async def hard_delete_user(
    user_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Permanently delete a user from the database.

    Args:
        user_id: The ID of the user to permanently delete
        current_user: The authenticated user making the request

    Returns:
        JSONResponse: Success message confirming permanent deletion
    """
    # Find user using the common utility function
    user = await get_user_by_id(db, user_id)
    if not user:
        return user_not_found_response()

    await db.delete(user)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="User permanently deleted.",
    )
