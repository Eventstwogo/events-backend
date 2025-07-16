# Email Utils Package

This package contains refactored email functionality for Events2Go, organized into separate modules for better maintainability.

## Structure

```
email_utils/
├── __init__.py          # Package initialization and exports
├── user_emails.py       # User-related email functions
├── admin_emails.py      # Admin-related email functions
└── README.md           # This file
```

## Modules

### user_emails.py
Contains all user-facing email functions:
- `send_welcome_email()` - Welcome email for new users
- `send_user_welcome_email()` - Welcome email with verification
- `send_password_reset_email()` - Password reset emails
- `send_security_alert_email()` - Security alerts
- `send_user_verification_email()` - Email verification
- `send_phone_otp_email()` - Phone OTP verification
- `send_account_activated_email()` - Account activation confirmation
- `send_account_locked_email()` - Account locked notifications
- `send_account_unlock_email()` - Account unlock emails
- `send_booking_confirmation_email()` - Booking confirmations
- `send_event_reminder_email()` - Event reminders
- `send_event_canceled_email()` - Event cancellation notifications
- `send_payment_confirmation_email()` - Payment confirmations
- `send_newsletter_subscription_email()` - Newsletter subscriptions
- `send_feedback_request_email()` - Feedback requests
- `send_ticket_delivery_email()` - Ticket delivery
- `send_event_update_email()` - Event updates
- `send_refund_confirmation_email()` - Refund confirmations

### admin_emails.py
Contains all admin-related email functions:
- `send_admin_password_reset_email()` - Admin password reset
- `send_admin_welcome_email()` - Admin welcome emails
- `send_admin_new_event_notification()` - New event notifications for admins

## Usage

### Direct Import from Modules
```python
from shared.utils.email_utils.user_emails import send_welcome_email
from shared.utils.email_utils.admin_emails import send_admin_welcome_email
```

### Import from Package (Recommended)
```python
from shared.utils.email_utils import send_welcome_email, send_admin_welcome_email
```

### Backward Compatibility
All functions are still available through the main email module:
```python
from shared.utils.email import send_welcome_email, send_admin_welcome_email
```

## Core Email Infrastructure

The core email infrastructure (EmailConfig, EmailSender classes, and email_sender instance) remains in the main `shared/utils/email.py` file and is imported by all email modules.

## Benefits of This Structure

1. **Better Organization**: User and admin emails are separated into logical modules
2. **Maintainability**: Easier to find and modify specific email functions
3. **Scalability**: Easy to add new email categories (e.g., organizer_emails.py)
4. **Backward Compatibility**: Existing imports continue to work
5. **Clear Separation of Concerns**: Core email logic vs. specific email functions