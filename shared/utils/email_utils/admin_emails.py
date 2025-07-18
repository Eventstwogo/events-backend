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
) -> bool:
    """Send welcome email to new admin user."""
    context = {
        "username": username,
        "email": email,
        "password": password,
        "role": role,
        "welcome_url": f"{settings.FRONTEND_URL}/admin",
        "year": str(datetime.now(tz=timezone.utc).year),
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


def send_admin_new_event_notification(
    admin_email: EmailStr,
    admin_name: str,
    event_id: str,
    event_title: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    event_category: Optional[str] = None,
    event_capacity: Optional[str] = None,
    ticket_price: Optional[str] = None,
    submission_date: Optional[str] = None,
    organizer_name: str = "",
    organizer_email: str = "",
    organizer_phone: Optional[str] = None,
    organizer_id: str = "",
    organizer_events_count: Optional[int] = None,
    priority: str = "medium",
    pending_events_count: Optional[int] = None,
    total_events_today: Optional[int] = None,
    approved_events_count: Optional[int] = None,
    rejected_events_count: Optional[int] = None,
    approve_url: str = "",
    reject_url: str = "",
    review_url: str = "",
) -> bool:
    """Send new event submission notification to admin."""
    priority_class_map = {
        "high": "priority-high",
        "medium": "priority-medium",
        "low": "priority-low",
    }

    context = {
        "admin_name": admin_name,
        "event_id": event_id,
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "venue_name": venue_name,
        "event_category": event_category,
        "event_capacity": event_capacity,
        "ticket_price": ticket_price,
        "submission_date": submission_date
        or datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "organizer_name": organizer_name,
        "organizer_email": organizer_email,
        "organizer_phone": organizer_phone,
        "organizer_id": organizer_id,
        "organizer_events_count": organizer_events_count,
        "priority": priority,
        "priority_class": priority_class_map.get(priority, "priority-medium"),
        "pending_events_count": pending_events_count,
        "total_events_today": total_events_today,
        "approved_events_count": approved_events_count,
        "rejected_events_count": rejected_events_count,
        "approve_url": approve_url,
        "reject_url": reject_url,
        "review_url": review_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=admin_email,
        subject=f"New Event Submission: {event_title}",
        template_file="admin/new_event_submission.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send admin event notification email to %s", admin_email
        )

    return success
