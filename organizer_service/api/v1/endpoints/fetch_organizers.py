from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from shared.core.security import decrypt_data
from shared.db.models import AdminUser, BusinessProfile
from shared.db.sessions.database import get_db
from shared.utils.data_utils import (
    create_organizer_validation_error,
    process_business_profile_data,
    validate_organizer_with_business_profile,
)

router = APIRouter()


@router.get("/", response_model=list[dict])
async def get_all_organizers(db: AsyncSession = Depends(get_db)):
    # Fetch all AdminUsers with their business profiles
    stmt = select(AdminUser).options(joinedload(AdminUser.business_profile))
    result = await db.execute(stmt)
    users = result.scalars().all()

    all_organizer_data = []

    for user in users:
        # Validate organizer role and business profile
        validation_result = await validate_organizer_with_business_profile(
            db, user.user_id, user.business_id
        )

        # Skip users who are not organizers
        if not validation_result["is_valid"]:
            # Only include organizers with validation errors (not non-organizers)
            if (
                validation_result["role_name"]
                and validation_result["role_name"].lower() == "organizer"
            ):
                all_organizer_data.append(
                    create_organizer_validation_error(
                        user.user_id, validation_result["error_message"]
                    )
                )
            continue

        business_profile = user.business_profile

        # Process profile_details and purpose using utility functions
        decrypted_profile_details, purpose_data = process_business_profile_data(
            business_profile.profile_details if business_profile else None,
            business_profile.purpose if business_profile else None,
            use_fallback=True,  # Use fallback for list endpoint to avoid breaking
        )

        all_organizer_data.append(
            {
                "organizer_login": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "role": validation_result["role_name"],
                    "is_verified": user.is_verified,
                    "is_active": user.is_verified,
                    "last_login": user.last_login,
                    "created_at": user.created_at,
                },
                "business_profile": {
                    "business_id": (
                        business_profile.business_id
                        if business_profile
                        else None
                    ),
                    "store_name": (
                        business_profile.store_name
                        if business_profile
                        else None
                    ),
                    "location": (
                        business_profile.location if business_profile else None
                    ),
                    "is_approved": validation_result[
                        "business_profile_approved"
                    ],
                    "profile_details": decrypted_profile_details,
                    "purpose": purpose_data,
                    "payment_preference": (
                        business_profile.payment_preference
                        if business_profile
                        else []
                    ),
                    "ref_number": (
                        business_profile.ref_number
                        if business_profile
                        else None
                    ),
                },
                "status": "valid",
            }
        )

    return all_organizer_data


@router.get("/{user_id}", response_model=dict)
async def get_organizer_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    # Fetch user with business profile
    stmt = (
        select(AdminUser)
        .options(joinedload(AdminUser.business_profile))
        .where(AdminUser.user_id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate organizer role and business profile
    validation_result = await validate_organizer_with_business_profile(
        db, user.user_id, user.business_id
    )

    if not validation_result["is_valid"]:
        if (
            validation_result["role_name"]
            and validation_result["role_name"].lower() != "organizer"
        ):
            current_role = validation_result["role_name"].upper()
            raise HTTPException(
                status_code=403,
                detail=f"This endpoint is restricted to organizers only. Your current role '{current_role}' does not have permission to access organizer details.",
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Organizer profile not found. {validation_result['error_message']}",
            )

    business_profile = user.business_profile

    # Process profile_details and purpose using utility functions
    try:
        decrypted_profile_details, purpose_data = process_business_profile_data(
            business_profile.profile_details if business_profile else None,
            business_profile.purpose if business_profile else None,
            use_fallback=False,  # Strict mode for single item endpoint
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    return {
        "organizer_login": {
            "user_id": user.user_id,
            "email": user.email,
            "role": validation_result["role_name"],
            "is_verified": user.is_verified,
            "is_active": user.is_verified,
            "last_login": user.last_login,
            "created_at": user.created_at,
        },
        "business_profile": {
            "business_id": (
                business_profile.business_id if business_profile else None
            ),
            "store_name": (
                business_profile.store_name if business_profile else None
            ),
            "location": business_profile.location if business_profile else None,
            "is_approved": validation_result["business_profile_approved"],
            "profile_details": decrypted_profile_details,
            "purpose": purpose_data,
            "payment_preference": (
                business_profile.payment_preference if business_profile else []
            ),
            "ref_number": (
                business_profile.ref_number if business_profile else None
            ),
            "timestamp": (
                business_profile.timestamp if business_profile else None
            ),
        },
        "status": "valid",
    }
