from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import AdminUser, BusinessProfile
from shared.db.sessions.database import get_db
from shared.utils.data_utils import (
    process_business_profile_data,
    validate_organizer_with_business_profile,
)
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get("/{user_id}", status_code=200)
@exception_handler
async def get_business_profile(
    user_id: str = Path(..., min_length=6, max_length=12),
    db: AsyncSession = Depends(get_db),
):
    user_stmt = select(AdminUser).where(AdminUser.user_id == user_id)
    result = await db.execute(user_stmt)
    user_result = result.scalars().first()

    if not user_result:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate organizer role and business profile
    validation_result = await validate_organizer_with_business_profile(
        db, user_id, user_result.business_id
    )

    if not validation_result["is_valid"]:
        if (
            validation_result["role_name"]
            and validation_result["role_name"].lower() != "organizer"
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {validation_result['error_message']}",
            )
        else:
            raise HTTPException(
                status_code=404, detail=validation_result["error_message"]
            )

    # Now fetch the business profile
    result = await db.execute(
        select(BusinessProfile).where(
            BusinessProfile.business_id == user_result.business_id
        )
    )
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=404, detail="Business profile not found"
        )

    # Process profile_details and purpose using utility functions
    try:
        decrypted_profile, purpose_list = process_business_profile_data(
            business.profile_details, business.purpose, use_fallback=False
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    return {
        "user_id": user_result.user_id,
        "email": user_result.email,
        "username": user_result.username,
        "role_name": user_result.role.role_name.lower(),
        "business_id": business.business_id,
        "profile_details": decrypted_profile,
        "business_logo": business.business_logo,
        "location": business.location,
        "store_name": business.store_name,
        "store_url": business.store_url,
        "ref_number": business.ref_number,
        "purpose": purpose_list,
        "is_approved": business.is_approved,
        "timestamp": business.timestamp,
    }
