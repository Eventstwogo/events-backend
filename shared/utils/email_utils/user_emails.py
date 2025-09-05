"""User email functions for Events2Go."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import quote

from pydantic import EmailStr

from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.utils.email import email_sender

logger = get_logger(__name__)


def send_password_reset_email(
    email: EmailStr,
    username: str,
    reset_token: str,
    ip_address: Optional[str] = None,
    request_time: Optional[str] = None,
    expiry_minutes: int = 24,
) -> bool:
    """Send a password reset email to a user."""
    encoded_email = quote(email, safe="")
    reset_link = f"{settings.USERS_APPLICATION_FRONTEND_URL}/reset-password?email={encoded_email}&token={reset_token}"
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


def send_user_verification_email(
    email: EmailStr,
    username: str,
    verification_token: str,
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
    encoded_email = quote(email, safe="")
    verification_link = (
        f"{settings.USERS_APPLICATION_FRONTEND_URL}/VerifyEmail?email={encoded_email}"
        f"&token={verification_token}"
    )

    context = {
        "username": username,
        "email": email,
        "verification_link": verification_link,
        "welcome_url": f"{settings.USERS_APPLICATION_FRONTEND_URL}",
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


def send_email_verification_resend(
    email: EmailStr,
    username: str,
    verification_token: str,
) -> bool:
    """
    Send a resend verification email to a user.

    Args:
        email: User's email address
        username: User's username
        verification_token: Email verification token

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    encoded_email = quote(email, safe="")
    verification_link = (
        f"{settings.USERS_APPLICATION_FRONTEND_URL}/VerifyEmail?email={encoded_email}"
        f"&token={verification_token}"
    )

    email_context = {
        "username": username,
        "verification_link": verification_link,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject="Verify Your Email Address",
        template_file="user/email_verification.html",
        context=email_context,
    )

    if not success:
        logger.warning("Failed to send verification resend email to %s", email)

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
        "event_url": event_url or f"{settings.USERS_APPLICATION_FRONTEND_URL}/event/{event_slug}",
        "my_bookings_url": my_bookings_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/Profile/Bookings",
        "support_url": support_url or f"{settings.USERS_APPLICATION_FRONTEND_URL}/support",
        "help_center_url": help_center_url or f"{settings.USERS_APPLICATION_FRONTEND_URL}/help",
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"🎉 Booking Confirmed - {event_title} | Events2Go",
        template_file="user/booking_success.html",
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
    total_discount: float,
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
            "total_amount": f"{sc['total_amount']:.2f}",
            "discount_amount": f"{sc.get('discount_amount', 'N/A')}",
            "subtotal": f"{sc['subtotal']:.2f}" if "subtotal" in sc else "-",
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
        "event_url": event_url or f"{settings.USERS_APPLICATION_FRONTEND_URL}/event/{event_slug}",
        "my_bookings_url": my_bookings_url
        or f"{settings.USERS_APPLICATION_FRONTEND_URL}/Profile/Bookings",
        "support_url": support_url or f"{settings.USERS_APPLICATION_FRONTEND_URL}/support",
        "help_center_url": help_center_url or f"{settings.USERS_APPLICATION_FRONTEND_URL}/help",
        "logo_url": logo_url,
        "year": str(datetime.now(tz=timezone.utc).year),
    }

    success = email_sender.send_email(
        to=email,
        subject=f"🎉 Booking Confirmed - {event_title} | Events2Go",
        template_file="user/booking_success.html",
        context=context,
    )

    if not success:
        logger.warning(
            "Failed to send booking success email to %s for order %s",
            email,
            order_id,
        )

    return success
