"""Email utilities package for Events2Go."""

from .user_emails import *
from .admin_emails import *

__all__ = [
    # User email functions
    "send_welcome_email",
    "send_user_welcome_email", 
    "send_password_reset_email",
    "send_security_alert_email",
    "send_user_verification_email",
    "send_phone_otp_email",
    "send_account_activated_email",
    "send_account_locked_email",
    "send_account_unlock_email",
    "send_booking_confirmation_email",
    "send_event_reminder_email",
    "send_event_canceled_email",
    "send_payment_confirmation_email",
    "send_newsletter_subscription_email",
    "send_feedback_request_email",
    "send_ticket_delivery_email",
    "send_event_update_email",
    "send_refund_confirmation_email",
    
    # Admin email functions
    "send_admin_password_reset_email",
    "send_admin_welcome_email",
    "send_admin_new_event_notification",
]