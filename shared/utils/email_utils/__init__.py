"""Email utilities package for Events2Go."""

from .admin_emails import (
    send_admin_password_reset_email,
    send_admin_welcome_email,
    send_event_creation_email,
    send_admin_contact_us_email,
    send_admin_organizer_query_email,
    send_admin_organizer_verification_email,
)
from .organizer_emails import (
    send_organizer_verification_email,
    send_organizer_onboarding_email,
    send_organizer_password_reset_email,
    send_event_creation_email_new,
    send_organizer_approval_notification,
    send_organizer_rejection_notification,
    send_organizer_review_notification,
)
from .user_emails import (
    send_password_reset_email,
    send_user_verification_email,
    send_email_verification_resend,
    send_booking_success_email,
    send_new_booking_success_email,
)

__all__ = [
    # User email functions
    "send_password_reset_email",
    "send_user_verification_email",
    "send_event_creation_email",
    "send_admin_contact_us_email",
    "send_admin_organizer_query_email",
    "send_admin_organizer_verification_email",
    
    # Organizer email functions
    "send_organizer_verification_email",
    "send_organizer_onboarding_email",
    "send_organizer_password_reset_email",
    "send_event_creation_email_new",
    "send_organizer_approval_notification",
    "send_organizer_rejection_notification",
    "send_organizer_review_notification",
    
    # Admin email functions
    "send_admin_password_reset_email",
    "send_admin_welcome_email",
    "send_email_verification_resend",
    "send_booking_success_email",
    "send_new_booking_success_email",
]
