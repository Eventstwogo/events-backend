"""
User validation services for the Events2Go application.
"""

from typing import Optional

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.core.logging_config import get_logger
from shared.db.models import User

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
            message="Username already exists. Please choose a different username.",
            log_error=True,
        )

    # Check for existing email
    query = User.by_email_query(email.lower())
    email_query = await db.execute(query)
    if email_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Email already exists. Please use a different email address.",
            log_error=True,
        )

    # Check for existing phone number if provided
    if phone_number:
        query = User.by_phone_number_query(phone_number)
        phone_query = await db.execute(query)
        if phone_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="Phone number already exists. Please use a different phone number.",
                log_error=True,
            )

    return None
