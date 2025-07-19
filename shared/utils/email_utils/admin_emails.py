"""Admin email functions for Events2Go."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import EmailStr

from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.utils.email import email_sender

logger = get_logger(__name__)


def send_admin_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 60,  # Default to 1 hour
) -> bool:
    """Send admin password reset email."""
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
        subject="Admin Password Reset - Events2Go",
        template_file="admin/password_reset.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send admin password reset email to %s", email)

    return success


def send_admin_welcome_email(
    email: EmailStr,
    username: str,
    password: str,
    role: str = "Administrator",
    logo: Optional[str] = None,
) -> bool:
    """Send welcome email to new admin user."""
    context = {
        "username": username,
        "email": email,
        "password": password,
        "role": role,
        "welcome_url": f"{settings.FRONTEND_URL}/admin",
        "year": str(datetime.now(tz=timezone.utc).year),
        "logo_url": logo,
    }

    success = email_sender.send_email(
        to=email,
        subject="Admin Access Granted - Events2Go",
        template_file="admin/welcome_admin.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send admin welcome email to %s", email)

    return success
