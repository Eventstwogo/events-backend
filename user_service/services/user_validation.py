"""
User validation services for the Events2Go application.
"""

from typing import Optional, Tuple

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.core.logging_config import get_logger
from shared.db.models import User
from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    has_excessive_repetition,
    normalize_whitespace,
    validate_length_range,
)

logger = get_logger(__name__)


async def validate_unique_user(
    db: AsyncSession,
    username: str,
    email: str,
    phone_number: Optional[str] = None,
) -> Optional[JSONResponse]:
    """
    Validate that a user with the given username, email, or phone number doesn't already exist.

    Args:
        db: Database session
        username: Username to check
        email: Email to check
        phone_number: Optional phone number to check

    Returns:
        JSONResponse with error if user exists, None otherwise
    """
    # Check for existing username
    query = User.by_username_query(username.lower())
    username_query = await db.execute(query)
    if username_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message=f"Username {username.lower()} already exists. Please choose a different username.",
            log_error=True,
        )

    # Check for existing email
    query = User.by_email_query(email.lower())
    email_query = await db.execute(query)
    if email_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message=f"Email {email.lower()} already exists. Please use a different email address.",
            log_error=True,
        )

    # Check for existing phone number if provided
    if phone_number:
        query = User.by_phone_number_query(phone_number)
        phone_query = await db.execute(query)
        if phone_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Phone number {phone_number} already exists. Please use a different phone number.",
                log_error=True,
            )

    return None


def validate_name_field(
    field_value: str, field_label: str
) -> Optional[JSONResponse]:
    """
    Validates an individual name field (first name or last name).
    Returns a JSONResponse if invalid, else None.
    """
    if not validate_length_range(field_value, 1, 255):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"{field_label} must be 1–255 characters long.",
            log_error=True,
        )

    if contains_xss(field_value):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"{field_label} contains potentially malicious content.",
            log_error=True,
        )

    if has_excessive_repetition(field_value, max_repeats=3):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"{field_label} contains excessive repeated characters.",
            log_error=True,
        )

    return None  # No issues


def validate_profile_names(
    profile_data,
) -> Tuple[Optional[JSONResponse], Optional[str], Optional[str]]:
    """
    Validates first name and last name fields of the profile.
    Returns a tuple: (error_response, cleaned_first_name, cleaned_last_name)
    """

    new_first_name = (
        normalize_whitespace(profile_data.first_name)
        if profile_data.first_name
        else None
    )
    new_last_name = (
        normalize_whitespace(profile_data.last_name)
        if profile_data.last_name
        else None
    )

    # Only compare if both are provided
    if new_first_name and new_last_name:
        if new_first_name.lower() == new_last_name.lower():
            return (
                api_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="First name and last name cannot be the same.",
                    log_error=True,
                ),
                None,
                None,
            )

    # Validate first name if provided
    if new_first_name:
        result = validate_name_field(new_first_name, "First name")
        if result:
            return result, None, None

    # Validate last name if provided
    if new_last_name:
        result = validate_name_field(new_last_name, "Last name")
        if result:
            return result, None, None

    # Everything is valid
    return None, new_first_name, new_last_name
