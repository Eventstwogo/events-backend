"""Admin email functions for Events2Go."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence
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
    reset_link = (
        f"{settings.ADMIN_FRONTEND_URL}/reset-password?email={encoded_email}&token={reset_token}"
    )
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
        "creation_date": datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Event Created Successfully - {event_title}",
        template_file="admin/event_created.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send event creation email to %s for event %s",
            email,
            event_id,
        )

    return success


def _send_to_admins(
    admin_emails: Sequence[EmailStr], subject: str, template_file: str, context: Dict
) -> bool:
    """Helper to send the same email to multiple admins."""
    success_all = True
    for admin_email in admin_emails:
        success = email_sender.send_email(
            to=admin_email,
            subject=subject,
            template_file=template_file,
            context=context,
        )
        if not success:
            logger.warning("Failed to send '%s' email to admin %s", subject, admin_email)
            success_all = False
    return success_all


# === New admin notifications ===


def send_admin_organizer_query_email(
    admin_emails: Sequence[EmailStr],
    organizer_name: str,
    organizer_email: EmailStr,
    subject: str,
    message: str,
) -> bool:
    """Notify admins when an organizer submits a query via support/contact.

    Uses template: admin/organizer_query.html
    """
    context = {
        "organizer_name": organizer_name,
        "organizer_email": organizer_email,
        "query_subject": subject,
        "query_message": message,
        "submitted_at": datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "review_url": f"{settings.ADMIN_FRONTEND_URL}/Enquiries",
        "support_email": settings.SUPPORT_EMAIL,
        "year": str(datetime.now(tz=timezone.utc).year),
    }
    return _send_to_admins(
        admin_emails,
        subject=f"Organizer Query Received: {subject}",
        template_file="admin/organizer_query.html",
        context=context,
    )


def send_admin_contact_us_email(
    admin_emails: Sequence[EmailStr],
    name: str,
    email: EmailStr,
    subject: str,
    message: str,
    phone: Optional[str] = None,
) -> bool:
    """Notify admins when a visitor submits the Contact Us form.

    Uses template: admin/contact_us.html
    """
    context = {
        "name": name,
        "email": email,
        "phone": phone,
        "subject": subject,
        "message": message,
        "submitted_at": datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "review_url": f"{settings.ADMIN_FRONTEND_URL}/ContactUs",
        "support_email": settings.SUPPORT_EMAIL,
        "year": str(datetime.now(tz=timezone.utc).year),
    }
    return _send_to_admins(
        admin_emails,
        subject=f"Contact Us Submission: {subject}",
        template_file="admin/contact_us.html",
        context=context,
    )


def send_admin_organizer_verification_email(
    admin_emails: list[EmailStr],
    organizer_name: str,
    business_name: str,
    reference_number: str,
    organizer_email: EmailStr,
    phone: Optional[str] = None,
    location: Optional[str] = None,
    documents_status: Optional[str] = "Pending review",
) -> bool:
    """Send notification email to all admins for organizer verification.

    Matches template variables in admin/organizer_verification.html
    """
    created_at = datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    context = {
        "organizer_name": organizer_name,
        "company_name": business_name,
        "organizer_email": organizer_email,
        "phone": phone,
        "location": location,
        "created_at": created_at,
        "documents_status": documents_status,
        "reference_number": reference_number,
        "review_url": f"{settings.ADMIN_FRONTEND_URL}/Organizers",
        "support_email": settings.SUPPORT_EMAIL,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    return _send_to_admins(
        admin_emails,
        subject=f"Organizer Verification Required: {business_name}",
        template_file="admin/organizer_verification.html",
        context=context,
    )
