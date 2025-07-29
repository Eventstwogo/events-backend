from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.services.response_builders import (
    config_not_found_response,
    role_not_found_response,
)
from admin_service.services.user_service import (
    get_config_or_404,
    get_role_by_name,
)
from admin_service.services.user_validation import validate_unique_user
from admin_service.utils.auth import hash_password
from organizer_service.schemas.register import (
    OrganizerRegisterRequest,
    OrganizerRegisterResponse,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser, UserVerification
from shared.db.sessions.database import get_db
from shared.utils.email_utils import send_organizer_verification_email
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import (
    generate_digits_lowercase,
    generate_digits_uppercase,
    generate_lower_uppercase,
)
from shared.utils.otp_and_tokens import generate_verification_tokens

router = APIRouter()


@router.post(
    "/register",
    response_model=OrganizerRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@exception_handler
async def register_user(
    background_tasks: BackgroundTasks,
    user_data: OrganizerRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Check if user already exists
    unique_user_result = await validate_unique_user(
        db, user_data.username, user_data.email
    )
    if unique_user_result is not None:
        return unique_user_result

    # Get system configuration
    config = await get_config_or_404(db)
    if not config:
        return config_not_found_response()

    # Create new user
    user_id = generate_lower_uppercase(length=6)

    # Hash the password
    password_hash = hash_password(user_data.password)

    # fetch role from database
    role = await get_role_by_name(db, "ORGANIZER")
    if not role:
        return role_not_found_response()

    if not user_data.username:
        user_data.username = user_data.email.split("@")[0]

    # Create new user with encrypted fields
    new_user = AdminUser(
        user_id=user_id,
        username=user_data.username.lower(),
        email=user_data.email.lower(),
        password_hash=password_hash,
        days_180_flag=config.global_180_day_flag,
        profile_id=generate_digits_uppercase(length=6),
        business_id=generate_digits_lowercase(length=6),
        login_status=0,
    )

    # Create verification record with expiration time
    verification_token, expiration_time = generate_verification_tokens(
        expires_in_minutes=60
    )
    verification = UserVerification(
        user_id=user_id,
        email_verification_token=verification_token,
        email_token_expires_at=expiration_time,
        email_verified=False,
        phone_verified=False,
    )

    # Add to database
    db.add(new_user)
    db.add(verification)
    await db.commit()
    await db.refresh(new_user)

    # Send welcome email with verification link in background
    background_tasks.add_task(
        send_organizer_verification_email,
        email=user_data.email,
        username=user_data.username,
        verification_token=verification_token,
        expires_in_minutes=60,  # Set expiration to 60 minutes
        business_name=user_data.username,
    )

    # Return success response
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message=(
            "Organizer registered successfully. Verification email sent "
            "to your email address in background."
        ),
        data=OrganizerRegisterResponse(
            user_id=user_id,
            email=user_data.email,
        ),
    )
