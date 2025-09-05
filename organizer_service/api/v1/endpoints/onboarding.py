import json

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.services.user_service import get_all_admin_users
from organizer_service.schemas.onboarding import OnboardingRequest
from organizer_service.services.business_profile import (
    fetch_abn_details,
    validate_abn_id,
)
from shared.constants import ONBOARDING_SUBMITTED
from shared.core.api_response import api_response
from shared.core.security import (
    decrypt_data,
    encrypt_data,
    encrypt_dict_values,
    hash_data,
)
from shared.db.models import AdminUser, BusinessProfile
from shared.db.models.organizer import OrganizerType
from shared.db.sessions.database import get_db
from shared.utils.email_utils import send_organizer_onboarding_email
from shared.utils.email_utils import send_admin_organizer_verification_email
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import generate_digits_letters

router = APIRouter()


async def validate_type_ref_id(db: AsyncSession, type_ref_id: str):
    result = await db.execute(
        select(OrganizerType).where(OrganizerType.type_id == type_ref_id)
    )
    organizer_type = result.scalar_one_or_none()

    if not organizer_type:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"OrganizerType with type_id '{type_ref_id}' does not exist.",
            log_error=True,
        )
    return organizer_type


@router.post("")
@exception_handler
async def organizer_onboarding(
    background_tasks: BackgroundTasks,
    data: OnboardingRequest,
    abn_id: str = Depends(validate_abn_id),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Validate user_id exists
    profile_check_stmt = select(AdminUser).where(
        AdminUser.user_id == data.user_id
    )
    profile_result = await db.execute(profile_check_stmt)
    existing_profile = profile_result.scalar_one_or_none()

    if not existing_profile:
        return JSONResponse(
            status_code=404,
            content={
                "message": "Invalid profile reference ID. Profile not found."
            },
        )

    # check organizer type
    organizer_type = await validate_type_ref_id(db, data.type_ref_id)

    # Clean and normalize store name
    store_name_cleaned = " ".join(
        data.store_name.strip().split()
    )  # Remove extra spaces between words

    # Validate store name uniqueness
    store_name_check_stmt = select(BusinessProfile).where(
        BusinessProfile.store_name.ilike(store_name_cleaned)
    )
    store_name_result = await db.execute(store_name_check_stmt)
    existing_store_name = store_name_result.scalar_one_or_none()

    if existing_store_name:
        return JSONResponse(
            status_code=409,
            content={
                "message": "Store name already exists. Please choose a different store name."
            },
        )

    # Additional store name validations
    store_name_lower = store_name_cleaned.lower()
    reserved_names = [
        "admin",
        "api",
        "www",
        "mail",
        "support",
        "help",
        "info",
        "test",
        "demo",
        "shop",
        "store",
    ]
    if store_name_lower in reserved_names:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Store name contains reserved words. Please choose a different name."
            },
        )

    # Validate store name doesn't start or end with special characters (spaces auto-cleaned)
    if store_name_cleaned.startswith(("-", "_")) or store_name_cleaned.endswith(
        ("-", "_")
    ):
        return JSONResponse(
            status_code=400,
            content={
                "message": "Store name cannot start or end with special characters."
            },
        )

    # Clean and normalize location - automatically handle all spacing and comma issues
    location_cleaned = data.location.strip()
    location_cleaned = " ".join(
        location_cleaned.split()
    )  # Remove extra spaces between words
    location_cleaned = ",".join(
        [part.strip() for part in location_cleaned.split(",")]
    )  # Clean spaces around commas

    # Remove any empty parts caused by consecutive commas
    location_parts = [
        part for part in location_cleaned.split(",") if part.strip()
    ]
    location_cleaned = ", ".join(location_parts)

    # Auto-clean: Remove leading/trailing commas if present
    location_cleaned = location_cleaned.strip(", ")

    # Validate location format (only check meaningful limits)
    if len(location_parts) > 5:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Location format invalid. Too many comma-separated values."
            },
        )

    # Fetch and validate ABN details
    abn_data = await fetch_abn_details(abn_id)
    if not abn_data:
        return JSONResponse(
            status_code=404, content={"message": "Unable to fetch ABN details."}
        )

    # Check if ABN already exists
    abn_hash = hash_data(abn_id)
    abn_check_stmt = select(BusinessProfile).where(
        BusinessProfile.abn_hash == abn_hash
    )
    abn_result = await db.execute(abn_check_stmt)
    existing_abn = abn_result.scalar_one_or_none()

    if existing_abn:
        return JSONResponse(
            status_code=409,
            content={
                "message": "ABN number already exists. This business is already registered."
            },
        )

    # Encrypt ABN and profile details
    encrypted_abn_id = encrypt_data(abn_id)
    encrypted_profile_dict = encrypt_dict_values(abn_data)
    encrypted_profile_json = json.dumps(encrypted_profile_dict)

    ref_number = generate_digits_letters()

    # Create new BusinessProfile instance
    new_profile = BusinessProfile(
        business_id=existing_profile.business_id,
        abn_id=encrypted_abn_id,
        abn_hash=abn_hash,
        profile_details=encrypted_profile_json,
        store_name=store_name_cleaned,
        store_url=str(data.store_url),
        location=location_cleaned,
        is_approved=ONBOARDING_SUBMITTED,
        purpose=json.dumps([p.value for p in data.purpose]),
        ref_number=ref_number,
        type_ref_id=data.type_ref_id,
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    
    admin_users = await get_all_admin_users(db)
    admin_emails = [user.email for user in admin_users]

    # Get organizer email for sending onboarding confirmation email
    try:
        organizer_email = existing_profile.email
        business_name = store_name_cleaned
        organizer_name = business_name  # Using business name as organizer name

        # Send onboarding confirmation email with reference number
        background_tasks.add_task(
            send_organizer_onboarding_email,
            email=organizer_email,
            username=organizer_name,
            business_name=business_name,
            reference_number=ref_number,
            status="Active",
        )
        
        background_tasks.add_task(
            send_admin_organizer_verification_email,
            admin_emails=admin_emails,
            business_name=business_name,
            reference_number=ref_number,
            organizer_name=organizer_name,
            organizer_email=organizer_email,
            phone=None,
            documents_status="Pending Review",
            location=location_cleaned,
        )
    except Exception as email_error:
        # Log the error but don't fail the onboarding process
        print(f"Warning: Failed to send onboarding email: {str(email_error)}")

    return JSONResponse(
        status_code=201,
        content={
            "message": "Organizer onboarding completed successfully. Confirmation email sent.",
            "reference_number": ref_number,
            "business_id": existing_profile.business_id,
            "store_url": str(data.store_url),
        },
    )
