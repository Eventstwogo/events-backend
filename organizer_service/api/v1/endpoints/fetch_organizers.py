import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from shared.core.security import decrypt_data, decrypt_dict_values
from shared.db.models import AdminUser, BusinessProfile
from shared.db.sessions.database import get_db

router = APIRouter()


@router.get("/", response_model=list[dict])
async def get_all_organizers(db: AsyncSession = Depends(get_db)):
    stmt = select(AdminUser).options(joinedload(AdminUser.business_profile))
    result = await db.execute(stmt)
    organizers = result.scalars().all()

    all_organizer_data = []

    for organizer in organizers:
        business_profile = organizer.business_profile

        # Decrypt profile_details if present
        decrypted_profile_details = {}
        if business_profile and business_profile.profile_details:
            try:
                raw_data = business_profile.profile_details
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)
                decrypted_profile_details = decrypt_dict_values(raw_data)
            except Exception as e:
                decrypted_profile_details = {
                    "error": f"Decryption failed: {str(e)}"
                }

        decrypted_email = decrypt_data(organizer.email)

        all_organizer_data.append(
            {
                "organizer_login": {
                    "user_id": organizer.user_id,
                    "email": decrypted_email,
                    "is_verified": organizer.is_verified,
                    "is_active": organizer.is_verified,
                    "last_login": organizer.last_login,
                    "created_at": organizer.created_at,
                },
                "business_profile": {
                    "store_name": (
                        business_profile.store_name
                        if business_profile
                        else None
                    ),
                    "location": (
                        business_profile.location if business_profile else None
                    ),
                    "is_approved": (
                        business_profile.is_approved
                        if business_profile
                        else None
                    ),
                    "profile_details": decrypted_profile_details,
                    "purpose": (
                        business_profile.purpose if business_profile else {}
                    ),
                    "payment_preference": (
                        business_profile.payment_preference
                        if business_profile
                        else []
                    ),
                },
            }
        )

    return all_organizer_data


@router.get("/{user_id}", response_model=dict)
async def get_organizer_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):

    # Fetch organizer login
    stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(stmt)
    organizer = result.scalar_one_or_none()

    if not organizer:
        raise HTTPException(status_code=404, detail="Organizer not found")

    # Fetch business profile
    business_stmt = select(BusinessProfile).where(
        BusinessProfile.business_id == organizer.business_id
    )
    business_result = await db.execute(business_stmt)
    business_profile = business_result.scalar_one_or_none()

    # Decrypt profile_details if available
    decrypted_profile_details = {}
    if business_profile and business_profile.profile_details:
        try:
            # Ensure profile_details is a dict before decrypting
            raw_data = business_profile.profile_details
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)
            decrypted_profile_details = decrypt_dict_values(raw_data)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to decrypt profile details: {str(e)}",
            )

    return {
        "organizer_login": {
            "user_id": organizer.user_id,
            "email": organizer.email,
            "is_verified": organizer.is_verified,
            "is_active": organizer.is_verified,
            "last_login": organizer.last_login,
            "created_at": organizer.created_at,
        },
        "business_profile": {
            "store_name": (
                business_profile.store_name if business_profile else None
            ),
            "location": business_profile.location if business_profile else None,
            "is_approved": (
                business_profile.is_approved if business_profile else None
            ),
            "profile_details": decrypted_profile_details,
            "purpose": business_profile.purpose if business_profile else {},
        },
    }
