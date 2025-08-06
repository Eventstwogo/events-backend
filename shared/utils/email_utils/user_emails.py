"""User email functions for Events2Go."""

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from pydantic import EmailStr

from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.utils.email import email_sender

logger = get_logger(__name__)


def send_password_reset_email(
    email: EmailStr,
    username: str,
    reset_token: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 24,
) -> bool:
    """Send a password reset email to a user."""
    encoded_email = quote(email, safe="")
    reset_link = f"{settings.USERS_APPLICATION_FRONTEND_URL}/reset-password?email={encoded_email}&token={reset_token}"
    context = {
        "username": username,
        "email": email,
        "reset_link": reset_link,
        "ip_address": ip_address,
        "request_time": request_time
        or datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "expiry_minutes": expiry_minutes,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Reset Your Events2Go Password",
        template_file="user/password_reset.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send password reset email to %s", email)

    return success


def send_user_verification_email(
    email: EmailStr,
    username: str,
    verification_token: str,
    expires_in_minutes: int = 60,
) -> bool:
    """
    Send a welcome email to a new user with email verification link.

    Args:
        email: User's email address
        username: User's username
        verification_token: Email verification token
        user_id: User's unique identifier

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    encoded_email = quote(email, safe="")
    verification_link = (
        f"{settings.USERS_APPLICATION_FRONTEND_URL}/VerifyEmail?email={encoded_email}"
        f"&token={verification_token}"
    )

    context = {
        "username": username,
        "email": email,
        "verification_link": verification_link,
        "welcome_url": f"{settings.USERS_APPLICATION_FRONTEND_URL}",
        "year": str(datetime.now(tz=timezone.utc).year),
        "expires_in_minutes": expires_in_minutes,
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Events2Go - Verify Your Email",
        template_file="user/email_verification.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send welcome email to %s", email)

    return success


def send_email_verification_resend(
    email: EmailStr,
    username: str,
    verification_token: str,
) -> bool:
    """
    Send a resend verification email to a user.

    Args:
        email: User's email address
        username: User's username
        verification_token: Email verification token

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    encoded_email = quote(email, safe="")
    verification_link = (
        f"{settings.USERS_APPLICATION_FRONTEND_URL}/VerifyEmail?email={encoded_email}"
        f"&token={verification_token}"
    )

    email_context = {
        "username": username,
        "verification_link": verification_link,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Verify Your Email Address",
        template_file="user/email_verification.html",
        context=email_context,
    )

    if not success:
        logger.warning("Failed to send verification resend email to %s", email)

    return success
