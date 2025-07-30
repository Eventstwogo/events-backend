from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from starlette.responses import JSONResponse

from admin_service.services.response_builders import user_not_found_response
from admin_service.services.user_service import get_user_by_email
from organizer_service.schemas.verify import (
    EmailVerificationRequest,
    EmailVerificationSentResponse,
    ResendEmailTokenRequest,
    VerificationResponse,
)
from shared.core.api_response import api_response
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, AdminUserVerification
from shared.db.sessions.database import get_db
from shared.utils.email_utils.admin_emails import (
    send_organizer_verification_email,
)
from shared.utils.exception_handlers import exception_handler
from shared.utils.otp_and_tokens import generate_verification_tokens

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/verify",
    response_model=VerificationResponse,
    summary="Verify email with token",
)
@exception_handler
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Verify a user's email address using the token sent to their email.

    Args:
        request: The verification request containing the user email and token
        db: Database session

    Returns:
        JSONResponse: Response with verification result
    """
    # Find user by email with verification data using joinedload for efficient loading
    # Convert email to lowercase to match how it's stored in the database
    email_lower = request.email.lower()
    logger.info(f"Looking for user with email: {email_lower}")

    stmt = AdminUser.by_email_query(email_lower).options(
        joinedload(AdminUser.verification)
    )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"AdminUser not found with email: {email_lower}")
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"AdminUser with email '{email_lower}' not found.",
            log_error=True,
        )

    # Check if verification record exists
    if not user.verification:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No verification record found for this user.",
            log_error=True,
        )

    verification = user.verification

    # Check if token exists and is not expired
    if not verification.email_verification_token:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No verification token has been generated. Please request a new token.",
            log_error=True,
        )

    if (
        verification.email_token_expires_at is None
        or verification.email_token_expires_at < datetime.now(timezone.utc)
    ):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Verification token has expired. Please request a new token.",
            log_error=True,
        )

    # Verify token
    if verification.email_verification_token != request.token:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid verification token.",
            log_error=True,
        )

    # Mark email as verified
    verification.email_verified = True
    verification.email_verification_token = None  # Clear the token
    verification.email_token_expires_at = None  # Clear the expiration time

    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Email verified successfully.",
        data=VerificationResponse(
            user_id=user.user_id,
            verified=True,
            message="Email verified successfully.",
        ),
    )


@router.post(
    "/resend-token",
    response_model=EmailVerificationSentResponse,
    summary="Resend email verification token",
)
@exception_handler
async def resend_email_token(
    request: ResendEmailTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Resend the email verification token to the user's email address.

    Args:
        request: The request containing the user's email
        db: Database session

    Returns:
        JSONResponse: Response with success message
    """
    # Find user by email
    user = await get_user_by_email(db, request.email)
    if not user:
        return user_not_found_response()

    # Load user with verification data using selectinload
    stmt = (
        select(AdminUser)
        .options(selectinload(AdminUser.verification))
        .where(AdminUser.user_id == user.user_id)
    )

    result = await db.execute(stmt)
    user_with_verification = result.scalar_one_or_none()

    if not user_with_verification:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="AdminUser not found.",
            log_error=True,
        )

    # Get or create verification record
    verification = user_with_verification.verification
    if not verification:
        verification = AdminUserVerification(
            user_id=user.user_id,
            email_verified=False,
            phone_verified=False,
        )
        db.add(verification)

    # Check if email is already verified
    if verification.email_verified:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Email is already verified.",
            log_error=True,
        )

    # Generate verification token using the utility function
    verification_token, expiration_time = generate_verification_tokens(
        expires_in_minutes=30
    )

    # Update verification record
    verification.email_verification_token = verification_token
    verification.email_token_expires_at = expiration_time

    await db.commit()

    # Send email with verification link
    email_sent = send_organizer_verification_email(
        email=user.email,
        username=user.username,
        verification_token=verification_token,
        expires_in_minutes=60,  # Set expiration to 60 minutes
        business_name=user.username,
    )

    if not email_sent:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send verification email. Please try again later.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Verification email sent successfully.",
        data=EmailVerificationSentResponse(
            user_id=user.user_id,
            email=user.email,
            message="Verification email sent. Please check your inbox.",
            expires_in_minutes=30,
        ),
    )
