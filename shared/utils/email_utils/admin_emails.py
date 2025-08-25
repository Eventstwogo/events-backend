"""Admin email functions for Events2Go."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
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
        template_file="admin/password_reset.html",
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
        "approval_date": datetime.now(tz=timezone.utc).strftime(
            "%B %d, %Y at %I:%M %p UTC"
        ),
        "admin_name": admin_name,
        "admin_message": admin_message,
        "dashboard_url": dashboard_url
        or f"{settings.ORGANIZER_FRONTEND_URL}/dashboard",
        "support_url": support_url
        or f"{settings.ORGANIZER_FRONTEND_URL}/support",
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
        logger.warning(
            "Failed to send organizer approval notification email to %s", email
        )

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
        "review_date": datetime.now(tz=timezone.utc).strftime(
            "%B %d, %Y at %I:%M %p UTC"
        ),
        "admin_name": admin_name,
        "admin_message": admin_message,
        "reapply_url": reapply_url
        or f"{settings.ORGANIZER_FRONTEND_URL}/apply",
        "guidelines_url": guidelines_url
        or f"{settings.ORGANIZER_FRONTEND_URL}/guidelines",
        "support_url": support_url
        or f"{settings.ORGANIZER_FRONTEND_URL}/support",
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
        logger.warning(
            "Failed to send organizer rejection notification email to %s", email
        )

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
        "support_url": support_url
        or f"{settings.ORGANIZER_FRONTEND_URL}/support",
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
        logger.warning(
            "Failed to send organizer review notification email to %s", email
        )

    return success


def send_booking_success_email(
    email: EmailStr,
    user_name: str,
    booking_id: str,
    event_title: str,
    event_slug: str,
    event_date: str,
    event_location: str,
    event_category: str,
    time_slot: str,
    num_seats: int,
    price_per_seat: float,
    total_price: float,
    booking_date: str,
    event_url: Optional[str] = None,
    my_bookings_url: Optional[str] = None,
    support_url: Optional[str] = None,
    help_center_url: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> bool:
    """
    Send booking success confirmation email with digital ticket.

    Args:
        email: User's email address
        user_name: Name of the user who made the booking
        booking_id: Unique booking identifier
        event_title: Title of the booked event
        event_date: Event date (formatted string)
        event_location: Event location/venue
        event_category: Event category
        time_slot: Booked time slot
        num_seats: Number of seats booked
        price_per_seat: Price per individual seat
        total_price: Total amount paid
        booking_date: Date when booking was made
        event_url: URL to view event details
        my_bookings_url: URL to user's bookings page
        support_url: URL to support page
        help_center_url: URL to help center
        logo_url: URL to company logo

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    context = {
        "user_name": user_name,
        "user_email": email,
        "booking_id": booking_id,
        "event_title": event_title,
        "event_date": event_date,
        "event_location": event_location,
        "event_category": event_category,
        "time_slot": time_slot,
        "num_seats": num_seats,
        "price_per_seat": f"{price_per_seat:.2f}",
        "total_price": f"{total_price:.2f}",
        "booking_date": booking_date,
        "event_url": event_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/event/{event_slug}",
        "my_bookings_url": my_bookings_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/Profile/Bookings",
        "support_url": support_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/support",
        "help_center_url": help_center_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/help",
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"🎉 Booking Confirmed - {event_title} | Events2Go",
        template_file="organizer/booking_success.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send booking success email to %s for booking %s",
            email,
            booking_id,
        )

    return success


def send_new_booking_success_email(
    email: EmailStr,
    user_name: str,
    order_id: str,
    event_title: str,
    event_slug: str,
    event_date: str,
    event_time: str,
    event_duration: str,
    event_location: str,
    event_category: str,
    booking_date: str,
    total_amount: float,
    seat_categories: List[
        Dict[str, str]
    ],  # list of {label, num_seats, price_per_seat, total_price}
    event_url: Optional[str] = None,
    my_bookings_url: Optional[str] = None,
    support_url: Optional[str] = None,
    help_center_url: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> bool:
    """
    Send booking success confirmation email with detailed ticket info.

    Args:
        email: User's email address
        user_name: Name of the user who made the booking
        order_id: Unique booking order identifier
        event_title: Title of the booked event
        event_slug: Slug for event details page
        event_date: Event date (string)
        event_time: Event start time (string)
        event_duration: Duration of the event (string)
        event_location: Event venue
        event_category: Event category name
        booking_date: Date when booking was made
        total_amount: Total order amount
        seat_categories: List of seat categories booked with details
        event_url: URL to view event details
        my_bookings_url: URL to user's bookings page
        support_url: URL to support page
        help_center_url: URL to help center
        logo_url: URL to company logo

    Returns:
        bool: True if email sent successfully, False otherwise
    """

    # Build a structured table-like representation for email template
    seat_categories_summary = [
        {
            "label": sc["label"],
            "num_seats": sc["num_seats"],
            "price_per_seat": f"{sc['price_per_seat']:.2f}",
            "total_price": f"{sc['total_price']:.2f}",
        }
        for sc in seat_categories
    ]

    context = {
        "user_name": user_name,
        "user_email": email,
        "order_id": order_id,
        "event_title": event_title,
        "event_date": event_date,
        "event_time": event_time,
        "event_duration": event_duration,
        "event_location": event_location,
        "event_category": event_category,
        "booking_date": booking_date,
        "total_amount": f"{total_amount:.2f}",
        "seat_categories": seat_categories_summary,  # ✅ all seat categories
        "event_url": event_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/event/{event_slug}",
        "my_bookings_url": my_bookings_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/Profile/Bookings",
        "support_url": support_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/support",
        "help_center_url": help_center_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/help",
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"🎉 Booking Confirmed - {event_title} | Events2Go",
        template_file="organizer/booking_success.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send booking success email to %s for order %s",
            email,
            order_id,
        )

    return success
