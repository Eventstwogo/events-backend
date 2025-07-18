"""User email functions for Events2Go."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import EmailStr

from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.utils.email import email_sender

logger = get_logger(__name__)


def send_welcome_email(
    email: EmailStr, username: str, password: str, logo_url: str
) -> None:
    """Send a welcome email to a new user."""
    context = {
        "username": username,
        "email": email,
        "welcome_url": f"{settings.FRONTEND_URL}",
        "password": password,
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Welcome to Events2Go!",
        template_file="user/welcome_user.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send welcome email to %s", email)


def send_user_welcome_email(
    email: EmailStr, username: str, verification_token: str
) -> bool:
    """
    Send a welcome email to a new user with email verification link.

    Args:
        email: User's email address
        username: User's username
        verification_token: Email verification token

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    verification_link = (
        f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    )

    context = {
        "username": username,
        "email": email,
        "verification_link": verification_link,
        "welcome_url": f"{settings.FRONTEND_URL}",
        "year": str(datetime.now(tz=timezone.utc).year),
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


def send_password_reset_email(
    email: EmailStr,
    username: str,
    reset_link: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 24,
) -> bool:
    """Send a password reset email to a user."""
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


def send_security_alert_email(
    email: EmailStr,
    username: str,
    alert_type: str,
    activity_time: str,
    ip_address: Optional[str] = None,
    location: Optional[str] = None,
    device_info: Optional[str] = None,
    secure_account_url: Optional[str] = None,
    review_activity_url: Optional[str] = None,
) -> bool:
    """Send a security alert email to a user."""
    context = {
        "username": username,
        "alert_type": alert_type,
        "activity_time": activity_time,
        "ip_address": ip_address,
        "location": location,
        "device_info": device_info,
        "secure_account_url": secure_account_url
        or f"{settings.FRONTEND_URL}/security",
        "review_activity_url": review_activity_url
        or f"{settings.FRONTEND_URL}/activity",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Security Alert - {alert_type} - Events2Go",
        template_file="user/security_alert.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send security alert email to %s", email)

    return success


def send_user_verification_email(
    email: EmailStr,
    username: str,
    verification_token: str,
    user_id: str,
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
    verification_link = f"{settings.FRONTEND_URL}/VerifyEmail?email={email}&token={verification_token}"

    context = {
        "username": username,
        "email": email,
        "verification_link": verification_link,
        "welcome_url": f"{settings.FRONTEND_URL}",
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


def send_phone_otp_email(
    email: EmailStr,
    username: str,
    phone_number: str,
    otp_code: str,
    expiry_minutes: int = 10,
) -> bool:
    """Send phone OTP verification email to user."""
    context = {
        "username": username,
        "phone_number": phone_number,
        "otp_code": otp_code,
        "expiry_minutes": expiry_minutes,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Phone Verification Code - Events2Go",
        template_file="user/phone_otp.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send phone OTP email to %s", email)

    return success


def send_account_activated_email(
    email: EmailStr,
    username: str,
    account_type: str = "Standard",
    activation_date: Optional[str] = None,
) -> bool:
    """Send account activation confirmation email."""
    context = {
        "username": username,
        "email": email,
        "account_type": account_type,
        "activation_date": activation_date
        or datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
        "profile_url": f"{settings.FRONTEND_URL}/profile",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Account Activated - Welcome to Events2Go!",
        template_file="user/account_activated.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send account activation email to %s", email)

    return success


def send_account_locked_email(
    email: EmailStr,
    username: str,
    lock_reason: str,
    unlock_url: Optional[str] = None,
) -> bool:
    """Send account locked notification email."""
    context = {
        "username": username,
        "lock_reason": lock_reason,
        "unlock_url": unlock_url or f"{settings.FRONTEND_URL}/unlock-account",
        "support_url": f"{settings.FRONTEND_URL}/support",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Account Security Alert - Events2Go",
        template_file="user/account_locked.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send account locked email to %s", email)

    return success


def send_account_unlock_email(
    email: EmailStr,
    username: str,
    unlock_token: str,
    expiry_hours: int = 24,
) -> bool:
    """Send account unlock email with token."""
    unlock_link = f"{settings.FRONTEND_URL}/unlock-account?token={unlock_token}"

    context = {
        "username": username,
        "unlock_link": unlock_link,
        "expiry_hours": expiry_hours,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Unlock Your Account - Events2Go",
        template_file="user/account_unlock.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send account unlock email to %s", email)

    return success


def send_booking_confirmation_email(
    email: EmailStr,
    username: str,
    booking_id: str,
    event_title: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    ticket_quantity: int,
    ticket_type: str,
    ticket_price: str,
    total_amount: str,
    service_fee: Optional[str] = None,
    taxes: Optional[str] = None,
    event_image: Optional[str] = None,
    qr_code_url: Optional[str] = None,
    ticket_url: Optional[str] = None,
    calendar_url: Optional[str] = None,
) -> bool:
    """Send booking confirmation email with ticket details."""
    context = {
        "username": username,
        "customer_email": email,
        "booking_id": booking_id,
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "venue_name": venue_name,
        "ticket_quantity": ticket_quantity,
        "ticket_type": ticket_type,
        "ticket_price": ticket_price,
        "total_amount": total_amount,
        "service_fee": service_fee,
        "taxes": taxes,
        "event_image": event_image,
        "qr_code_url": qr_code_url,
        "ticket_url": ticket_url
        or f"{settings.FRONTEND_URL}/tickets/{booking_id}",
        "calendar_url": calendar_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Booking Confirmed - {event_title}",
        template_file="user/booking_confirmation.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send booking confirmation email to %s", email)

    return success


def send_event_reminder_email(
    email: EmailStr,
    username: str,
    event_title: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    venue_address: Optional[str] = None,
    booking_id: Optional[str] = None,
    ticket_type: Optional[str] = None,
    ticket_quantity: Optional[int] = None,
    days_remaining: Optional[int] = None,
    hours_remaining: Optional[int] = None,
    minutes_remaining: Optional[int] = None,
    event_image: Optional[str] = None,
    ticket_url: Optional[str] = None,
    calendar_url: Optional[str] = None,
    event_url: Optional[str] = None,
    additional_notes: Optional[str] = None,
) -> bool:
    """Send event reminder email to attendee."""
    context = {
        "username": username,
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "venue_name": venue_name,
        "venue_address": venue_address,
        "booking_id": booking_id,
        "ticket_type": ticket_type,
        "ticket_quantity": ticket_quantity,
        "days_remaining": days_remaining,
        "hours_remaining": hours_remaining,
        "minutes_remaining": minutes_remaining,
        "event_image": event_image,
        "ticket_url": ticket_url,
        "calendar_url": calendar_url,
        "event_url": event_url,
        "additional_notes": additional_notes,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Reminder: {event_title} is coming up!",
        template_file="user/event_reminder.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send event reminder email to %s", email)

    return success


def send_event_canceled_email(
    email: EmailStr,
    username: str,
    event_title: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    booking_id: Optional[str] = None,
    cancellation_reason: Optional[str] = None,
    refund_amount: Optional[str] = None,
    refund_processing_time: Optional[str] = None,
    refund_method: Optional[str] = None,
    dashboard_url: Optional[str] = None,
    support_url: Optional[str] = None,
) -> bool:
    """Send event cancellation notification email."""
    context = {
        "username": username,
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "venue_name": venue_name,
        "booking_id": booking_id,
        "cancellation_reason": cancellation_reason,
        "refund_amount": refund_amount,
        "refund_processing_time": refund_processing_time,
        "refund_method": refund_method,
        "dashboard_url": dashboard_url or f"{settings.FRONTEND_URL}/dashboard",
        "support_url": support_url or f"{settings.FRONTEND_URL}/support",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Event Canceled: {event_title}",
        template_file="user/event_canceled.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send event cancellation email to %s", email)

    return success


def send_payment_confirmation_email(
    email: EmailStr,
    username: str,
    transaction_id: str,
    total_amount: str,
    payment_method: Optional[str] = None,
    payment_date: Optional[str] = None,
    event_title: Optional[str] = None,
    event_date: Optional[str] = None,
    event_time: Optional[str] = None,
    venue_name: Optional[str] = None,
    venue_address: Optional[str] = None,
    booking_id: Optional[str] = None,
    ticket_quantity: Optional[int] = None,
    ticket_type: Optional[str] = None,
    ticket_price: Optional[str] = None,
    ticket_subtotal: Optional[str] = None,
    service_fee: Optional[str] = None,
    taxes: Optional[str] = None,
    discount_amount: Optional[str] = None,
    ticket_url: Optional[str] = None,
    dashboard_url: Optional[str] = None,
    receipt_url: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> bool:
    """Send payment confirmation email."""
    context = {
        "username": username,
        "transaction_id": transaction_id,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "payment_date": payment_date
        or datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "venue_name": venue_name,
        "venue_address": venue_address,
        "booking_id": booking_id,
        "ticket_quantity": ticket_quantity,
        "ticket_type": ticket_type,
        "ticket_price": ticket_price,
        "ticket_subtotal": ticket_subtotal,
        "service_fee": service_fee,
        "taxes": taxes,
        "discount_amount": discount_amount,
        "ticket_url": ticket_url,
        "dashboard_url": dashboard_url or f"{settings.FRONTEND_URL}/dashboard",
        "receipt_url": receipt_url,
        "additional_instructions": additional_instructions,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Payment Successful - Events2Go",
        template_file="user/payment_confirmation.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send payment confirmation email to %s", email)

    return success


def send_newsletter_subscription_email(
    email: EmailStr,
    username: Optional[str] = None,
    subscription_date: Optional[str] = None,
    frequency: Optional[str] = None,
    interests: Optional[str] = None,
    browse_events_url: Optional[str] = None,
    preferences_url: Optional[str] = None,
    account_settings_url: Optional[str] = None,
    incentive_offer: Optional[str] = None,
) -> bool:
    """Send newsletter subscription confirmation email."""
    context = {
        "username": username,
        "email": email,
        "subscription_date": subscription_date
        or datetime.now(tz=timezone.utc).strftime("%B %d, %Y"),
        "frequency": frequency,
        "interests": interests,
        "browse_events_url": browse_events_url
        or f"{settings.FRONTEND_URL}/events",
        "preferences_url": preferences_url
        or f"{settings.FRONTEND_URL}/preferences",
        "account_settings_url": account_settings_url
        or f"{settings.FRONTEND_URL}/settings",
        "incentive_offer": incentive_offer,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Newsletter Subscription Confirmed - Events2Go",
        template_file="user/newsletter_subscription.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send newsletter subscription email to %s", email
        )

    return success


def send_feedback_request_email(
    email: EmailStr,
    username: str,
    event_title: str,
    event_date: str,
    venue_name: str,
    feedback_url: str,
    booking_id: Optional[str] = None,
    attendance_date: Optional[str] = None,
    detailed_feedback_url: Optional[str] = None,
    incentive_offer: Optional[str] = None,
    facebook_share_url: Optional[str] = None,
    twitter_share_url: Optional[str] = None,
    linkedin_share_url: Optional[str] = None,
) -> bool:
    """Send feedback request email after event attendance."""
    context = {
        "username": username,
        "event_title": event_title,
        "event_date": event_date,
        "venue_name": venue_name,
        "booking_id": booking_id,
        "attendance_date": attendance_date,
        "feedback_url": feedback_url,
        "detailed_feedback_url": detailed_feedback_url,
        "incentive_offer": incentive_offer,
        "facebook_share_url": facebook_share_url,
        "twitter_share_url": twitter_share_url,
        "linkedin_share_url": linkedin_share_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"How was {event_title}? Share your feedback!",
        template_file="user/feedback_request.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send feedback request email to %s", email)

    return success


def send_ticket_delivery_email(
    email: EmailStr,
    username: str,
    event_title: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    booking_id: str,
    ticket_quantity: int,
    ticket_type: Optional[str] = None,
    qr_code_url: Optional[str] = None,
    download_url: Optional[str] = None,
    calendar_url: Optional[str] = None,
    event_url: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> bool:
    """Send ticket delivery email with digital tickets."""
    context = {
        "username": username,
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "venue_name": venue_name,
        "booking_id": booking_id,
        "ticket_quantity": ticket_quantity,
        "ticket_type": ticket_type,
        "qr_code_url": qr_code_url,
        "download_url": download_url,
        "calendar_url": calendar_url,
        "event_url": event_url,
        "additional_instructions": additional_instructions,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Your tickets for {event_title} are ready!",
        template_file="user/ticket_delivery.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send ticket delivery email to %s", email)

    return success


def send_event_update_email(
    email: EmailStr,
    username: str,
    event_title: str,
    event_date: str,
    event_time: str,
    venue_name: str,
    update_type: str = "information",
    booking_id: Optional[str] = None,
    changes: Optional[list] = None,
    action_required: Optional[str] = None,
    important_notice: Optional[str] = None,
    event_url: Optional[str] = None,
    ticket_url: Optional[str] = None,
    calendar_url: Optional[str] = None,
    requires_confirmation: bool = False,
    confirmation_url: Optional[str] = None,
) -> bool:
    """Send event update notification email."""
    update_type_class_map = {
        "information": "update-type-info",
        "warning": "update-type-warning",
        "critical": "update-type-critical",
    }

    context = {
        "username": username,
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "venue_name": venue_name,
        "update_type": update_type.title(),
        "update_type_class": update_type_class_map.get(
            update_type.lower(), "update-type-info"
        ),
        "booking_id": booking_id,
        "changes": changes or [],
        "action_required": action_required,
        "important_notice": important_notice,
        "event_url": event_url,
        "ticket_url": ticket_url,
        "calendar_url": calendar_url,
        "requires_confirmation": requires_confirmation,
        "confirmation_url": confirmation_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"Event Update: {event_title}",
        template_file="user/event_update.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send event update email to %s", email)

    return success


def send_refund_confirmation_email(
    email: EmailStr,
    username: str,
    refund_amount: str,
    refund_method: Optional[str] = None,
    processing_time: Optional[str] = None,
    event_title: Optional[str] = None,
    refund_id: Optional[str] = None,
    original_transaction_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    refund_date: Optional[str] = None,
    original_amount: Optional[str] = None,
    refund_fee: Optional[str] = None,
    refund_reason: Optional[str] = None,
    dashboard_url: Optional[str] = None,
    receipt_url: Optional[str] = None,
    support_url: Optional[str] = None,
) -> bool:
    """Send refund confirmation email."""
    context = {
        "username": username,
        "refund_amount": refund_amount,
        "refund_method": refund_method,
        "processing_time": processing_time,
        "event_title": event_title,
        "refund_id": refund_id,
        "original_transaction_id": original_transaction_id,
        "booking_id": booking_id,
        "refund_date": refund_date
        or datetime.now(tz=timezone.utc).strftime("%B %d, %Y"),
        "original_amount": original_amount,
        "refund_fee": refund_fee,
        "refund_reason": refund_reason,
        "dashboard_url": dashboard_url or f"{settings.FRONTEND_URL}/dashboard",
        "receipt_url": receipt_url,
        "support_url": support_url or f"{settings.FRONTEND_URL}/support",
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Refund Processed Successfully - Events2Go",
        template_file="user/refund_confirmation.html",
        context=context,
    )

    if not success:
        logger.warning("Failed to send refund confirmation email to %s", email)

    return success
