from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.security import (
    decrypt_dict_values,
)
from shared.db.models import BusinessProfile
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get("/{business_id}", status_code=200)
@exception_handler
async def get_business_profile(
    business_id: str = Path(..., min_length=6, max_length=12),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BusinessProfile).where(
            BusinessProfile.business_id == business_id
        )
    )
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=404, detail="Business profile not found"
        )

    # Directly use the dictionary values from JSONB
    decrypted_profile = decrypt_dict_values(business.profile_details)

    return {
        "business_id": business.business_id,
        "profile_details": decrypted_profile,
        "business_logo": business.business_logo,
        "location": business.location,
        "payment_preference": business.payment_preference,
        "store_name": business.store_name,
        "store_url": business.store_url,
        "ref_number": business.ref_number,
        "purpose": business.purpose,  # Already a dict or list
        "is_approved": business.is_approved,
        "timestamp": business.timestamp,
    }
