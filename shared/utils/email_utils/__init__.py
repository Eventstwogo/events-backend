"""Email utilities package for Events2Go."""

from .admin_emails import (
    send_admin_password_reset_email,
    send_admin_welcome_email,
)
from .user_emails import (
    send_password_reset_email,
    send_user_verification_email,
)

__all__ = [
    # User email functions
    "send_password_reset_email",
    "send_user_verification_email",
    # Admin email functions
    "send_admin_password_reset_email",
    "send_admin_welcome_email",
]
