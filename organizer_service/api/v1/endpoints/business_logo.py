from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models.admin_users import AdminUser
from shared.db.models.organizer import BusinessProfile
from shared.db.sessions.database import get_db
from shared.dependencies.admin import get_current_active_user
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url, remove_file_if_exists, save_uploaded_file
from shared.utils.secure_filename import secure_filename


router = APIRouter()


@router.patch("/logo", summary="Update organizer business logo")
@exception_handler
async def update_profile_picture(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    business_logo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update the current organizer business logo.

    Args:
        business_logo: The new organizer business logo file

    Returns:
        JSONResponse: Success message with updated profile URL
    """
    # Validate file type
    if business_logo.content_type not in settings.ALLOWED_MEDIA_TYPES:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid file type for profile picture.",
            log_error=True,
        )

    # Fetch the user
    result = await db.execute(select(AdminUser).where(AdminUser.user_id == current_user.user_id))
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Organizer not found.",
            log_error=True,
        )

    # check if the organizer has business profile or not
    business_result = await db.execute(
        select(BusinessProfile).where(BusinessProfile.business_id == user.business_id)
    )
    existing_business = business_result.scalar_one_or_none()

    if not existing_business:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Business profile not found.",
            log_error=True,
        )

    # Upload new profile picture
    uploaded_url = await save_uploaded_file(
        business_logo,
        settings.PROFILE_PICTURE_UPLOAD_PATH.format(username=secure_filename(user.username)),
    )

    # Delete previous profile picture
    if existing_business.business_logo:
        await remove_file_if_exists(existing_business.business_logo)

    # Update and save
    existing_business.business_logo = uploaded_url
    await db.commit()
    await db.refresh(existing_business)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Profile picture updated successfully.",
        data={"profile_picture": get_media_url(existing_business.business_logo)},
    )


@router.get("/logo", summary="Get organizer business logo")
@exception_handler
async def get_business_logo(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Fetch the current organizer's business logo.

    Returns:
        JSONResponse: Business logo URL (if available)
    """
    # Fetch the user
    result = await db.execute(select(AdminUser).where(AdminUser.user_id == current_user.user_id))
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Organizer not found.",
            log_error=True,
        )

    # Fetch business profile
    business_result = await db.execute(
        select(BusinessProfile).where(BusinessProfile.business_id == user.business_id)
    )
    existing_business = business_result.scalar_one_or_none()

    if not existing_business:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Business profile not found.",
            log_error=True,
        )

    # If no logo is uploaded
    if not existing_business.business_logo:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Business logo not found.",
            log_error=False,
        )

    # Return logo URL
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Business logo fetched successfully.",
        data={"business_logo": get_media_url(existing_business.business_logo)},
    )
