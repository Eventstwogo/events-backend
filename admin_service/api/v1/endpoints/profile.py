from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.schemas.profile import UserProfile
from lifespan import settings
from shared.core.api_response import api_response
from shared.db.models import AdminUser, Role
from shared.db.sessions.database import get_db
from shared.dependencies.admin import get_current_active_user
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import (
    get_media_url,
    remove_file_if_exists,
    save_uploaded_file,
)
from shared.utils.secure_filename import secure_filename

router = APIRouter()


@router.get("", response_model=UserProfile, summary="Get current user profile")
@exception_handler
async def get_profile(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get the current user's profile information.

    Returns:
        JSONResponse: User profile data
    """
    # Query user with role information
    stmt = (
        select(AdminUser, Role.role_name)
        .join(Role, AdminUser.role_id == Role.role_id)
        .where(AdminUser.user_id == current_user.user_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User profile not found.",
            log_error=True,
        )

    user, role_name = row

    # Create response object
    profile_data = {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role_id": user.role_id,
        "role_name": role_name,
        "profile_picture": (
            get_media_url(user.profile_picture)
            if user.profile_picture
            else None
        ),
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Profile fetched successfully.",
        data=profile_data,
    )


# @router.put("", response_model=UserProfile, summary="Update user profile")
# @exception_handler
# async def update_profile(
#     current_user: Annotated[AdminUser, Depends(get_current_active_user)],
#     profile_data: UpdateProfileRequest,
#     db: AsyncSession = Depends(get_db),
# ) -> JSONResponse:
#     """
#     Update the current user's profile information.

#     Args:
#         profile_data: The updated profile information

#     Returns:
#         JSONResponse: Updated user profile
#     """
#     # Fetch the user
#     result = await db.execute(
#         select(AdminUser).where(AdminUser.user_id == current_user.user_id)
#     )
#     user = result.scalar_one_or_none()

#     if not user:
#         return api_response(
#             status_code=status.HTTP_404_NOT_FOUND,
#             message="User not found.",
#             log_error=True,
#         )

#     # Validate username
#     new_username = normalize_whitespace(profile_data.username)
#     if new_username.lower() != user.username:
#         # Validate username format
#         if not is_valid_username(
#             new_username, allow_spaces=True, allow_hyphens=True
#         ):
#             return api_response(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 message="Username can only contain letters, numbers, spaces, and hyphens.",
#                 log_error=True,
#             )

#         if not validate_length_range(new_username, 4, 32):
#             return api_response(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 message="Username must be 4–32 characters long.",
#                 log_error=True,
#             )

#         if contains_xss(new_username):
#             return api_response(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 message="Username contains potentially malicious content.",
#                 log_error=True,
#             )

#         if has_excessive_repetition(new_username, max_repeats=3):
#             return api_response(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 message="Username contains excessive repeated characters.",
#                 log_error=True,
#             )

#         if len(new_username) < 3 or not all(
#             c.isalpha() for c in new_username[:3]
#         ):
#             return api_response(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 message="First three characters of username must be letters.",
#                 log_error=True,
#             )

#         # Check if username already exists using hash-based query
#         query = AdminUser.by_username_query(new_username.lower())
#         existing_user = await db.execute(query)
#         existing_user = existing_user.scalar_one_or_none()
#         if existing_user and existing_user.user_id != current_user.user_id:
#             return api_response(
#                 status_code=status.HTTP_409_CONFLICT,
#                 message="Username already exists.",
#                 log_error=True,
#             )

#         user.username = new_username.lower()

#     # Update email if changed
#     if profile_data.email != user.email:
#         # Check if email already exists using hash-based query
#         query = AdminUser.by_email_query(profile_data.email.lower())
#         existing_email = await db.execute(query)
#         existing_email = existing_email.scalar_one_or_none()
#         if existing_email and existing_email.user_id != current_user.user_id:
#             return api_response(
#                 status_code=status.HTTP_409_CONFLICT,
#                 message="Email already exists.",
#                 log_error=True,
#             )

#         user.email = profile_data.email

#     await db.commit()
#     await db.refresh(user)

#     # Fetch role name for response
#     role_result = await db.execute(
#         select(Role.role_name).where(Role.role_id == user.role_id)
#     )
#     role_name = role_result.scalar_one()

#     return api_response(
#         status_code=status.HTTP_200_OK,
#         message="Profile updated successfully.",
#         data={
#             "user_id": user.user_id,
#             "username": user.username,
#             "email": user.email,
#             "role_id": user.role_id,
#             "role_name": role_name,
#             "profile_picture": (
#                 get_media_url(user.profile_picture)
#                 if user.profile_picture
#                 else None
#             ),
#         },
#     )


@router.patch("/picture", summary="Update profile picture")
@exception_handler
async def update_profile_picture(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    profile_picture: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update the current user's profile picture.

    Args:
        profile_picture: The new profile picture file

    Returns:
        JSONResponse: Success message with updated profile URL
    """
    # Validate file type
    if profile_picture.content_type not in settings.ALLOWED_MEDIA_TYPES:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid file type for profile picture.",
            log_error=True,
        )

    # Fetch the user
    result = await db.execute(
        select(AdminUser).where(AdminUser.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Upload new profile picture
    uploaded_url = await save_uploaded_file(
        profile_picture,
        settings.PROFILE_PICTURE_UPLOAD_PATH.format(
            username=secure_filename(user.username)
        ),
    )

    # Delete previous profile picture
    if user.profile_picture:
        remove_file_if_exists(user.profile_picture)

    # Update and save
    user.profile_picture = uploaded_url
    await db.commit()
    await db.refresh(user)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Profile picture updated successfully.",
        data={"profile_picture": get_media_url(user.profile_picture)},
    )


@router.delete("", summary="Delete current user account")
@exception_handler
async def delete_account(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Soft-delete the current user's account.

    Returns:
        JSONResponse: Success message
    """
    # Fetch the user
    result = await db.execute(
        select(AdminUser).where(AdminUser.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Check if user is already deactivated
    if user.is_deleted:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is already deactivated.",
            log_error=True,
        )

    # Soft delete the user
    user.is_deleted = True
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Account deactivated successfully.",
    )
