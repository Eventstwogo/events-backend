"""Admin email functions for Events2Go."""

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from pydantic import EmailStr

from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.utils.email import email_sender

logger = get_logger(__name__)


def send_admin_password_reset_email(
    email: EmailStr,
    username: str,
    reset_token: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 60,  # Default to 1 hour
) -> bool:
    """Send admin password reset email."""
    encoded_email = quote(email, safe="")
    reset_link = f"{settings.ADMIN_FRONTEND_URL}/reset-password?email={encoded_email}&token={reset_token}"
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
        "welcome_url": f"{settings.ADMIN_FRONTEND_URL}/",
        "year": str(datetime.now(tz=timezone.utc).year),
        # "logo_url": logo,
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


def send_organizer_verification_email(
    email: EmailStr,
    username: str,
    verification_token: str,
    expires_in_minutes: int = 30,
    business_name: Optional[str] = None,
) -> bool:
    """Send verification email to organizer with token."""
    encoded_email = quote(email, safe="")
    verification_link = (
        f"{settings.ORGANIZER_FRONTEND_URL}/emailconfirmation?email={encoded_email}"
        f"&token={verification_token}"
    )

    context = {
        "vendor_name": username,
        "vendor_email": email,
        "business_name": business_name or "Your Business",
        "verification_token": verification_token,
        "verification_link": verification_link,
        "expiry_minutes": expires_in_minutes,
        "registration_date": datetime.now(tz=timezone.utc).strftime(
            "%B %d, %Y at %I:%M %p UTC"
        ),
        "header_subtitle": "Verify your Organizer account to get started",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Verify Your Events2Go Organizer Account",
        template_file="organizer/email_verification.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send organizer verification email to %s", email
        )

    return success


def send_organizer_onboarding_email(
    email: EmailStr,
    username: str,
    business_name: str,
    reference_number: str,
    status: str = "Active",
    organizer_portal_url: Optional[str] = None,
    support_phone: Optional[str] = None,
) -> bool:
    """Send onboarding email to new vendor."""
    context = {
        "vendor_name": username,
        "business_name": business_name,
        "email": email,
        "reference_number": reference_number,
        "status": status,
        "vendor_portal_url": organizer_portal_url
        or f"{settings.ORGANIZER_FRONTEND_URL}",
        "creation_date": datetime.now(tz=timezone.utc).strftime(
            "%B %d, %Y at %I:%M %p UTC"
        ),
        "support_phone": support_phone,
        "header_subtitle": "Your vendor account is ready",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Events2Go Vendor Portal",
        template_file="organizer/onboarding.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send vendor onboarding email to %s", email)

    return success


def send_event_creation_email(
    email: EmailStr,
    organizer_name: str,
    event_title: str,
    event_id: str,
    event_start_date: str,
    event_end_date: str,
    event_location: str,
    event_category: str,
    created_by_role: str = "organizer",  # "admin" or "organizer"
) -> bool:
    """
    Send event creation confirmation email.

    Args:
        email: Recipient email address
        organizer_name: Name of the organizer/admin who created the event
        event_title: Title of the created event
        event_id: Unique identifier for the event
        event_start_date: Event start date (formatted string)
        event_end_date: Event end date (formatted string)
        event_location: Event location/venue
        event_category: Event category
        created_by_role: Role of the creator ("admin" or "organizer")

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Determine the appropriate URL based on who created the event
    if created_by_role.lower() == "organizer":
        event_url = f"{settings.ORGANIZER_FRONTEND_URL}/Events/view/{event_id}"
    else:
        event_url = f"{settings.ADMIN_FRONTEND_URL}/Events/view/{event_id}"

    context = {
        "organizer_name": organizer_name,
        "event_title": event_title,
        "event_date": event_start_date,  # For backward compatibility with template
        "event_start_date": event_start_date,
        "event_end_date": event_end_date,
        "event_location": event_location,
        "event_category": event_category,
        "event_url": event_url,
        "event_id": event_id,
        "created_by_role": created_by_role.upper(),
        "creation_date": datetime.now(tz=timezone.utc).strftime(
            "%B %d, %Y at %I:%M %p UTC"
        ),
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Event Created Successfully - {event_title}",
        template_file="organizer/event_created.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send event creation email to %s for event %s",
            email,
            event_id,
        )

    return success
