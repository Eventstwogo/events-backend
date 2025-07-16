from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.db.models import User, UserVerification
from shared.db.sessions.database import get_db
from user_service.schemas.register import (
    UserRegisterRequest,
    UserRegisterResponse,
)
from user_service.services.response_builders import config_not_found_response
from user_service.services.user_service import get_config_or_404
from user_service.services.user_validation import validate_unique_user
from user_service.utils.auth import hash_password
from shared.utils.email import send_user_verification_email
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import (
    generate_lower_uppercase,
)

router = APIRouter()


def generate_verification_tokens(
    length: int = 32, expires_in_minutes: int = 30
) -> tuple[str, datetime]:
    """
    Generate a cryptographically secure verification token with expiration time.

    Args:
        length: Byte length of the token to generate (default: 32)
               The resulting string will be longer due to base64 encoding
        expires_in_minutes: Number of minutes until the token expires (default: 30)

    Returns:
        tuple[str, datetime]: A secure random token and its expiration time
    """
    token = secrets.token_urlsafe(length)
    expiration_time = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return token, expiration_time


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@exception_handler
async def register_user(
    background_tasks: BackgroundTasks,
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Register a new user.

    This endpoint creates a new user with the provided information.
    A welcome email with verification link will be sent to the user's email address.

    Args:
        background_tasks: FastAPI background tasks handler
        user_data: User registration data including first_name, last_name, username, email, and password
        db: Database session

    Returns:
        JSONResponse: Response with user details and success message
    """
    # Check if user already exists
    unique_user_result = await validate_unique_user(db, user_data.username, user_data.email)
    if unique_user_result is not None:
        return unique_user_result

    # Validate first name and last name are not the same
    if user_data.first_name.strip().lower() == user_data.last_name.strip().lower():
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="First name and last name cannot be the same.",
            log_error=True,
        )

    # Create new user
    user_id = generate_lower_uppercase(length=6)

    # Hash the password
    password_hash = hash_password(user_data.password)

    # Get system configuration
    config = await get_config_or_404(db)
    if not config:
        return config_not_found_response()

    # Create new user with encrypted fields
    new_user = User(
        user_id=user_id,
        username=user_data.username.lower(),
        first_name=user_data.first_name.title(),
        last_name=user_data.last_name.title(),
        email=user_data.email.lower(),
        password_hash=password_hash,
        days_180_flag=config.global_180_day_flag,
    )

    # Create verification record with expiration time
    verification_token, expiration_time = generate_verification_tokens(expires_in_minutes=30)
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
        send_user_verification_email,
        email=user_data.email,
        username=user_data.username,
        verification_token=verification_token,
        user_id=user_id,
    )

    # Return success response
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="User registered successfully. Verification email sent to your email address.",
        data=UserRegisterResponse(
            user_id=user_id,
            email=user_data.email,
        ),
    )
