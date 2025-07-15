from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from starlette.responses import JSONResponse

from shared.core.logging_config import get_logger
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models import User, UserVerification
from shared.db.sessions.database import get_db
from user_service.schemas.register import AddPhoneNumberRequest
from user_service.schemas.verify import (
    EmailVerificationRequest,
    EmailVerificationSentResponse,
    PhoneOTPSentResponse,
    PhoneVerificationCodeRequest,
    ResendEmailTokenRequest,
    ResendPhoneOTPRequest,
    UpdatePhoneNumberRequest,
    VerificationResponse,
)
from user_service.services.response_builders import user_not_found_response
from user_service.services.user_service import get_user_by_email, get_user_by_id
from shared.utils.email import email_sender
from shared.utils.exception_handlers import exception_handler
from shared.utils.sms import send_sms_otp
import string

router = APIRouter()
logger = get_logger(__name__)


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


def generate_otps(length: int = 6, expires_in_minutes: int = 10) -> tuple[str, datetime]:
    """
    Generate a numeric OTP (One-Time Password) with expiration time.

    Args:
        length: Length of the OTP to generate (default: 6)
        expires_in_minutes: Number of minutes until the OTP expires (default: 10)

    Returns:
        tuple[str, datetime]: A random string of digits and its expiration time
    """
    otp = "".join(secrets.choice(string.digits) for _ in range(length))
    expiration_time = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return otp, expiration_time


@router.post(
    "/email/verify",
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

    stmt = User.by_email_query(email_lower).options(joinedload(User.verification))

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found with email: {email_lower}")
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"User with email '{email_lower}' not found.",
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
    "/email/resend-token",
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
    stmt = select(User).options(selectinload(User.verification)).where(User.user_id == user.user_id)

    result = await db.execute(stmt)
    user_with_verification = result.scalar_one_or_none()

    if not user_with_verification:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Get or create verification record
    verification = user_with_verification.verification
    if not verification:
        verification = UserVerification(
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
    verification_token, expiration_time = generate_verification_tokens(expires_in_minutes=30)

    # Update verification record
    verification.email_verification_token = verification_token
    verification.email_token_expires_at = expiration_time

    await db.commit()

    # Create verification link
    verification_link = (
        f"{settings.FRONTEND_URL}/verify-email?email={user.email}&token={verification_token}"
    )

    # Send verification email
    email_context = {
        "username": user.username,
        "verification_link": verification_link,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    email_sent = email_sender.send_email(
        to=user.email,
        subject="Verify Your Email Address",
        template_file="user/email_verification.html",
        context=email_context,
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


@router.post("/phone/add", response_model=PhoneOTPSentResponse, summary="Add User phone number")
@exception_handler
async def add_phone_number(
    request: AddPhoneNumberRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Add or update a user's phone number and send OTP verification code.

    This endpoint adds a phone number to the user's profile and sends an OTP code
    for verification.

    Args:
        request: The request containing user email and phone number
        db: Database session

    Returns:
        JSONResponse: Response with success message and OTP expiration info
    """
    # Find user by email
    user = await get_user_by_email(db, request.email)
    if not user:
        return user_not_found_response()

    # Load user with verification data using selectinload
    stmt = select(User).options(selectinload(User.verification)).where(User.user_id == user.user_id)

    result = await db.execute(stmt)
    user_with_verification = result.scalar_one_or_none()

    if not user_with_verification:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Update user's phone number
    user_with_verification.phone_number = request.phone_number

    # Get or create verification record
    verification = user_with_verification.verification
    if not verification:
        verification = UserVerification(
            user_id=user.user_id,
            email_verified=False,
            phone_verified=False,
        )
        db.add(verification)

    # Reset phone verification status since phone number changed
    verification.phone_verified = False

    # Generate OTP code using the utility function
    otp_code, expiration_time = generate_otps(expires_in_minutes=10)

    # Update verification record
    verification.phone_verification_code = otp_code
    verification.phone_code_expires_at = expiration_time

    await db.commit()

    # Send OTP via SMS
    sms_sent = send_sms_otp(request.phone_number, otp_code)

    if not sms_sent:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send OTP code. Please try again later.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Phone number updated and OTP sent successfully.",
        data=PhoneOTPSentResponse(
            user_id=user.user_id,
            phone_number=request.phone_number,
            message="OTP sent to your phone. Please check your messages.",
            expires_in_minutes=10,
        ),
    )


@router.post(
    "/phone/update",
    response_model=PhoneOTPSentResponse,
    summary="Update phone number and send OTP",
)
@exception_handler
async def update_phone_number(
    request: UpdatePhoneNumberRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update user's phone number and send OTP verification code.

    This endpoint updates the user's phone number and sends an OTP code
    for verification.

    Args:
        request: The request containing user ID and new phone number
        db: Database session

    Returns:
        JSONResponse: Response with success message and OTP expiration info
    """
    # Find user by ID
    user = await get_user_by_id(db, request.user_id)
    if not user:
        return user_not_found_response()

    # Load user with verification data using selectinload
    stmt = select(User).options(selectinload(User.verification)).where(User.user_id == user.user_id)

    result = await db.execute(stmt)
    user_with_verification = result.scalar_one_or_none()

    if not user_with_verification:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Update user's phone number
    user_with_verification.phone_number = request.phone_number

    # Get or create verification record
    verification = user_with_verification.verification
    if not verification:
        verification = UserVerification(
            user_id=user.user_id,
            email_verified=False,
            phone_verified=False,
        )
        db.add(verification)

    # Reset phone verification status since phone number changed
    verification.phone_verified = False

    # Generate OTP code using the utility function
    otp_code, expiration_time = generate_otps(expires_in_minutes=10)

    # Update verification record
    verification.phone_verification_code = otp_code
    verification.phone_code_expires_at = expiration_time

    await db.commit()

    # Send OTP via SMS
    sms_sent = send_sms_otp(request.phone_number, otp_code)

    if not sms_sent:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send OTP code. Please try again later.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Phone number updated and OTP sent successfully.",
        data=PhoneOTPSentResponse(
            user_id=user.user_id,
            phone_number=request.phone_number,
            message="OTP sent to your phone. Please check your messages.",
            expires_in_minutes=10,
        ),
    )


@router.post(
    "/phone/verify",
    response_model=VerificationResponse,
    summary="Verify phone number with OTP code",
)
@exception_handler
async def verify_phone_otp(
    request: PhoneVerificationCodeRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Verify a user's phone number using the OTP code.

    Args:
        request: The verification request containing the user ID and OTP code
        db: Database session

    Returns:
        JSONResponse: Response with verification result
    """
    # Find user by ID with verification data using joinedload
    stmt = (
        select(User).options(joinedload(User.verification)).where(User.user_id == request.user_id)
    )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Check if user has a phone number
    if not user.phone_number or user.phone_number == "0":
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User does not have a phone number. Please update the phone number first.",
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

    # Check if OTP code exists and is not expired
    if not verification.phone_verification_code:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No OTP code has been generated. Please request a new code.",
            log_error=True,
        )

    if (
        verification.phone_code_expires_at is None
        or verification.phone_code_expires_at < datetime.now(timezone.utc)
    ):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="OTP code has expired. Please request a new code.",
            log_error=True,
        )

    # Verify OTP code
    if verification.phone_verification_code != request.verification_code:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid OTP code.",
            log_error=True,
        )

    # Mark phone as verified
    verification.phone_verified = True
    verification.phone_verification_code = None  # Clear the code
    verification.phone_code_expires_at = None  # Clear the expiration time

    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Phone number verified successfully.",
        data=VerificationResponse(
            user_id=user.user_id,
            verified=True,
            message="Phone number verified successfully.",
        ),
    )


@router.post(
    "/phone/resend-otp",
    response_model=PhoneOTPSentResponse,
    summary="Resend phone OTP code",
)
@exception_handler
async def resend_phone_otp(
    request: ResendPhoneOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Resend the OTP code to the user's phone number.

    Args:
        request: The request containing the user ID
        db: Database session

    Returns:
        JSONResponse: Response with success message
    """
    # Find user by ID
    user = await get_user_by_id(db, request.user_id)
    if not user:
        return user_not_found_response()

    # Load user with verification data using selectinload
    stmt = select(User).options(selectinload(User.verification)).where(User.user_id == user.user_id)

    result = await db.execute(stmt)
    user_with_verification = result.scalar_one_or_none()

    if not user_with_verification:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Check if user has a phone number
    if not user_with_verification.phone_number or user_with_verification.phone_number == "0":
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User does not have a phone number. Please update the phone number first.",
            log_error=True,
        )

    # Get or create verification record
    verification = user_with_verification.verification
    if not verification:
        verification = UserVerification(
            user_id=user.user_id,
            email_verified=False,
            phone_verified=False,
        )
        db.add(verification)

    # Check if phone is already verified
    if verification.phone_verified:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Phone number is already verified.",
            log_error=True,
        )

    # Generate OTP code using the utility function
    otp_code, expiration_time = generate_otps(expires_in_minutes=10)

    # Update verification record
    verification.phone_verification_code = otp_code
    verification.phone_code_expires_at = expiration_time

    await db.commit()

    # Send OTP via SMS
    sms_sent = send_sms_otp(user_with_verification.phone_number, otp_code)

    if not sms_sent:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send OTP code. Please try again later.",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="OTP code sent successfully.",
        data=PhoneOTPSentResponse(
            user_id=user.user_id,
            phone_number=user_with_verification.phone_number,
            message="OTP sent to your phone. Please check your messages.",
            expires_in_minutes=10,
        ),
    )
