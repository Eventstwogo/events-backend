from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import AdminUser, BusinessProfile
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post("/approve", response_model=dict)
@exception_handler
async def approve_organizer(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Fetch organizer
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        raise HTTPException(status_code=404, detail="Organizer not found")

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.business_id == organizer.business_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    if not business_profile:
        raise HTTPException(
            status_code=404, detail="Business profile not found"
        )

    # Update values
    organizer.is_verified = 1
    business_profile.is_approved = 1

    db.add_all([organizer, business_profile])
    await db.commit()

    return {"message": "Organizer approved successfully"}


@router.post("/reject", response_model=dict)
@exception_handler
async def reject_organizer(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Fetch organizer
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        raise HTTPException(status_code=404, detail="Organizer not found")

    # Fetch business profile
    profile_stmt = select(BusinessProfile).where(
        BusinessProfile.business_id == organizer.business_id
    )
    profile_result = await db.execute(profile_stmt)
    business_profile = profile_result.scalar_one_or_none()

    if not business_profile:
        raise HTTPException(
            status_code=404, detail="Business profile not found"
        )

    # Update values
    organizer.is_verified = 0
    business_profile.is_approved = 2

    db.add_all([organizer, business_profile])
    await db.commit()

    return {"message": "Organizer approval rejected successfully"}


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
        raise HTTPException(status_code=404, detail="Organizer not found")

    if organizer.is_deleted:
        return {"message": f"Organizer '{user_id}' is already inactive."}

    organizer.is_deleted = True
    db.add(organizer)
    await db.commit()

    return {
        "message": f"Organizer '{user_id}' has been soft deleted (deactivated) successfully."
    }


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
        raise HTTPException(status_code=404, detail="Organizer not found")

    if not organizer.is_deleted:
        return {"message": f"Organizer '{user_id}' is already active."}

    organizer.is_deleted = False
    db.add(organizer)
    await db.commit()

    return {
        "message": f"Organizer '{user_id}' has been restored (activated) successfully."
    }
