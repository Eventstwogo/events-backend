"""Admin email functions for Events2Go."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.parse import quote

from pydantic import EmailStr

from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.utils.email import email_sender

logger = get_logger(__name__)


def send_organizer_password_reset_email(
    email: EmailStr,
    username: str,
    reset_token: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 60,  # Default to 1 hour
) -> bool:
    """Send admin password reset email."""
    encoded_email = quote(email, safe="")
    reset_link = f"{settings.ORGANIZER_FRONTEND_URL}/reset-password?email={encoded_email}&token={reset_token}"
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
        template_file="organizer/password_reset.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send admin password reset email to %s", email)

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
        "registration_date": datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
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
        logger.warning("Failed to send organizer verification email to %s", email)

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
        "vendor_portal_url": organizer_portal_url or f"{settings.ORGANIZER_FRONTEND_URL}",
        "creation_date": datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
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


def send_event_creation_email_new(
    email: EmailStr,
    organizer_name: str,
    event_title: str,
    event_id: str,
    event_location: str,
    is_online: bool,
    event_category: str,
    created_by_role: str = "organizer",  # "admin" or "organizer"
) -> bool:
    # Determine the appropriate URL based on who created the event
    if created_by_role.lower() == "organizer":
        event_url = f"{settings.ORGANIZER_FRONTEND_URL}/Events/view/{event_id}"
    else:
        event_url = f"{settings.ADMIN_FRONTEND_URL}/Events/view/{event_id}"

    context = {
        "organizer_name": organizer_name,
        "event_title": event_title,
        "is_online": is_online,
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


def send_organizer_approval_notification(
    email: EmailStr,
    organizer_name: str,
    application_date: str,
    admin_name: str,
    admin_message: Optional[str] = None,
    dashboard_url: Optional[str] = None,
    support_url: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> bool:
    """
    Send organizer application approval notification email.

    Args:
        email: Organizer's email address
        organizer_name: Name of the organizer
        application_date: Date when application was submitted
        admin_name: Name of the admin who approved the application
        admin_message: Optional message from admin
        dashboard_url: URL to organizer dashboard
        support_url: URL to support page
        logo_url: URL to company logo

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    context = {
        "organizer_name": organizer_name,
        "organizer_email": email,
        "application_date": application_date,
        "approval_date": datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "admin_name": admin_name,
        "admin_message": admin_message,
        "dashboard_url": dashboard_url or f"{settings.ORGANIZER_FRONTEND_URL}/dashboard",
        "support_url": support_url or f"{settings.ORGANIZER_FRONTEND_URL}/support",
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="🎉 Organizer Application Approved - Events2Go",
        template_file="organizer/approval_notification.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send organizer approval notification email to %s", email)

    return success


def send_organizer_rejection_notification(
    email: EmailStr,
    organizer_name: str,
    application_date: str,
    admin_name: str,
    admin_message: Optional[str] = None,
    reapply_url: Optional[str] = None,
    guidelines_url: Optional[str] = None,
    support_url: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> bool:
    """
    Send organizer application rejection notification email.

    Args:
        email: Organizer's email address
        organizer_name: Name of the organizer
        application_date: Date when application was submitted
        admin_name: Name of the admin who reviewed the application
        admin_message: Optional feedback message from admin
        reapply_url: URL to reapply for organizer status
        guidelines_url: URL to organizer guidelines
        support_url: URL to support page
        logo_url: URL to company logo

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    context = {
        "organizer_name": organizer_name,
        "organizer_email": email,
        "application_date": application_date,
        "review_date": datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "admin_name": admin_name,
        "admin_message": admin_message,
        "reapply_url": reapply_url or f"{settings.ORGANIZER_FRONTEND_URL}/apply",
        "guidelines_url": guidelines_url or f"{settings.ORGANIZER_FRONTEND_URL}/guidelines",
        "support_url": support_url or f"{settings.ORGANIZER_FRONTEND_URL}/support",
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Organizer Application Update - Events2Go",
        template_file="organizer/rejection_notification.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send organizer rejection notification email to %s", email)

    return success


def send_organizer_review_notification(
    email: EmailStr,
    organizer_name: str,
    application_id: str,
    application_date: str,
    review_timeframe: str = "3-5 business days",
    expected_response_date: Optional[str] = None,
    support_url: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> bool:
    """
    Send organizer application under review notification email.

    Args:
        email: Organizer's email address
        organizer_name: Name of the organizer
        application_id: Unique identifier for the application
        application_date: Date when application was submitted
        review_timeframe: Expected timeframe for review completion
        expected_response_date: Expected date for response
        support_url: URL to support page
        logo_url: URL to company logo

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Calculate expected response date if not provided
    if not expected_response_date:
        expected_date = datetime.now(tz=timezone.utc) + timedelta(days=2)
        expected_response_date = expected_date.strftime("%B %d, %Y")

    context = {
        "organizer_name": organizer_name,
        "organizer_email": email,
        "application_id": application_id,
        "application_date": application_date,
        "review_timeframe": review_timeframe,
        "expected_response_date": expected_response_date,
        "support_url": support_url or f"{settings.ORGANIZER_FRONTEND_URL}/support",
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Application Received - Under Review | Events2Go",
        template_file="organizer/review_notification.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send organizer review notification email to %s", email)

    return success
