from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.constants import (
    ONBOARDING_APPROVED,
    ONBOARDING_REJECTED,
    ONBOARDING_UNDER_REVIEW,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser, BusinessProfile
from shared.db.sessions.database import get_db
from shared.utils.email_utils.admin_emails import (
    send_organizer_approval_notification,
    send_organizer_rejection_notification,
    send_organizer_review_notification,
)
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post("/approve", response_model=dict)
@exception_handler
async def approve_organizer(
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Fetch organizer
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Organizer {user_id} does not exist",
            log_error=True,
        )

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.business_id == organizer.business_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    if not business_profile:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Business profile for Organizer {user_id} does not exist",
            log_error=True,
        )

    # Update values
    organizer.is_verified = 1
    business_profile.is_approved = ONBOARDING_APPROVED
    business_profile.approved_date = datetime.now()

    db.add_all([organizer, business_profile])
    await db.commit()

    # Send approval notification email in background
    background_tasks.add_task(
        send_organizer_approval_notification,
        email=organizer.email,
        organizer_name=organizer.username,
        application_date=business_profile.timestamp.strftime("%B %d, %Y"),
        admin_name="Events2Go Admin Team",
        admin_message="Congratulations! Your application has been approved. Welcome to Events2Go!",
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Organizer approved successfully",
    )


@router.post("/reject", response_model=dict)
@exception_handler
async def reject_organizer(
    user_id: str,
    reviewer_comment: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    reviewer_comment = reviewer_comment.strip()
    if not reviewer_comment:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Reviewer comment cannot be empty",
            log_error=True,
        )

    # Fetch organizer
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Organizer {user_id} does not exist",
            log_error=True,
        )

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.business_id == organizer.business_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    if not business_profile:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Business profile for Organizer {user_id} does not exist",
            log_error=True,
        )

    # Update values
    organizer.is_verified = 0
    organizer.is_deleted = True
    business_profile.is_approved = ONBOARDING_REJECTED
    business_profile.reviewer_comment = reviewer_comment.strip()

    db.add_all([organizer, business_profile])
    await db.commit()

    # Send rejection notification email in background
    background_tasks.add_task(
        send_organizer_rejection_notification,
        email=organizer.email,
        organizer_name=organizer.username,
        application_date=business_profile.timestamp.strftime("%B %d, %Y"),
        admin_name="Events2Go Admin Team",
        admin_message=reviewer_comment,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Organizer approval rejected successfully",
    )


@router.patch("/under-review", response_model=dict)
@exception_handler
async def under_review_organizer(
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Fetch organizer
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Organizer {user_id} does not exist",
            log_error=True,
        )

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.business_id == organizer.business_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()
    if not business_profile:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Business profile for Organizer {user_id} does not exist",
            log_error=True,
        )

    # Update values
    business_profile.is_approved = ONBOARDING_UNDER_REVIEW
    db.add(business_profile)
    await db.commit()

    # Send review notification email in background
    background_tasks.add_task(
        send_organizer_review_notification,
        email=organizer.email,
        organizer_name=organizer.username,
        application_id=business_profile.ref_number,
        application_date=business_profile.timestamp.strftime("%B %d, %Y"),
        review_timeframe="1-2 business days",
    )

    return api_response(status_code=status.HTTP_200_OK, message="Under review")


@router.put("/soft-delete", response_model=dict)
@exception_handler
async def soft_delete_organizer(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Organizer {user_id} does not exist",
            log_error=True,
        )

    if organizer.is_deleted:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message=f"Organizer '{user_id}' is already inactive.",
            log_error=False,
        )

    organizer.is_deleted = True
    db.add(organizer)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Organizer '{user_id}' has been soft deleted (deactivated) successfully.",
    )


@router.put("/restore", response_model=dict)
@exception_handler
async def restore_organizer(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Organizer {user_id} does not exist",
            log_error=True,
        )

    if not organizer.is_deleted:
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message=f"Organizer '{user_id}' is already active.",
            log_error=False,
        )

    organizer.is_deleted = False
    db.add(organizer)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Organizer '{user_id}' has been restored (activated) successfully.",
    )
