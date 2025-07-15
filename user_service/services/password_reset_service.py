import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.logging_config import get_logger
from shared.db.models import User, UserPasswordReset

logger = get_logger(__name__)


def generate_password_reset_token(
    expires_in_minutes: int = 60,
) -> Tuple[str, datetime]:
    """
    Generate a secure 32-character password reset token and its expiration time.

    Args:
        expires_in_minutes: Token expiration time in minutes (default: 60)

    Returns:
        Tuple[str, datetime]: Token and expiration datetime (UTC)
    """
    # Generate a 32-character token using secrets.token_urlsafe
    # token_urlsafe(24) generates ~32 characters
    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return token, expires_at


async def create_password_reset_record(
    db: AsyncSession, user_id: str, token: str, expires_at: datetime
) -> UserPasswordReset:
    """
    Create or update a password reset record for a user.

    Args:
        db: Database session
        user_id: User ID
        token: Reset token
        expires_at: Token expiration time

    Returns:
        UserPasswordReset: The created/updated password reset record
    """
    try:
        # Check if a password reset record already exists for this user
        stmt = select(UserPasswordReset).where(UserPasswordReset.user_id == user_id)
        result = await db.execute(stmt)
        password_reset = result.scalar_one_or_none()

        if password_reset:
            # Update existing record
            password_reset.reset_password_token = token
            password_reset.reset_token_expires_at = expires_at
            logger.info(f"Updated password reset record for user {user_id}")
        else:
            # Create new record
            password_reset = UserPasswordReset(
                user_id=user_id,
                reset_password_token=token,
                reset_token_expires_at=expires_at,
            )
            db.add(password_reset)
            logger.info(f"Created new password reset record for user {user_id}")

        await db.commit()
        await db.refresh(password_reset)
        return password_reset

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating/updating password reset record: {str(e)}")
        raise


async def get_password_reset_by_token(db: AsyncSession, token: str) -> Optional[UserPasswordReset]:
    """
    Get password reset record by token.

    Args:
        db: Database session
        token: Reset token

    Returns:
        UserPasswordReset or None: The password reset record if found
    """
    try:
        stmt = (
            select(UserPasswordReset)
            .options(selectinload(UserPasswordReset.user))
            .where(UserPasswordReset.reset_password_token == token)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error fetching password reset by token: {str(e)}")
        raise


async def validate_reset_token(
    db: AsyncSession, token: str, email: str
) -> Tuple[bool, Optional[str], Optional[User]]:
    """
    Validate a password reset token.

    Args:
        db: Database session
        token: Reset token to validate
        email: Email address to match

    Returns:
        Tuple[bool, Optional[str], Optional[User]]:
        (is_valid, error_message, user)
    """
    try:
        # Get password reset record by token
        password_reset = await get_password_reset_by_token(db, token)

        if not password_reset:
            return False, "Invalid or expired reset token.", None

        # Check if token has expired
        current_time = datetime.now(timezone.utc)
        if (
            password_reset.reset_token_expires_at is None
            or current_time > password_reset.reset_token_expires_at
        ):
            return False, "Reset token has expired.", None

        # Check if user exists and email matches
        user = password_reset.user
        if not user or user.email.lower() != email.lower():
            return False, "Invalid token or email mismatch.", None

        # Check if user account is active
        if user.is_deleted:
            return False, "User account is deactivated.", None

        return True, None, user

    except Exception as e:
        logger.error(f"Error validating reset token: {str(e)}")
        return False, "An error occurred while validating the token.", None


async def mark_password_reset_used(db: AsyncSession, user_id: str) -> None:
    """
    Mark a password reset as used by clearing the token and updating last reset time.

    Args:
        db: Database session
        user_id: User ID
    """
    try:
        stmt = select(UserPasswordReset).where(UserPasswordReset.user_id == user_id)
        result = await db.execute(stmt)
        password_reset = result.scalar_one_or_none()

        if password_reset:
            password_reset.reset_password_token = None
            password_reset.reset_token_expires_at = None
            password_reset.last_reset_done_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(f"Marked password reset as used for user {user_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error marking password reset as used: {str(e)}")
        raise


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """
    Clean up expired password reset tokens.

    Args:
        db: Database session

    Returns:
        int: Number of tokens cleaned up
    """
    try:
        current_time = datetime.now(timezone.utc)

        # Find all expired tokens
        stmt = select(UserPasswordReset).where(
            UserPasswordReset.reset_token_expires_at < current_time,
            UserPasswordReset.reset_password_token.is_not(None),
        )
        result = await db.execute(stmt)
        expired_resets = result.scalars().all()

        count = 0
        for password_reset in expired_resets:
            password_reset.reset_password_token = None
            password_reset.reset_token_expires_at = None
            count += 1

        if count > 0:
            await db.commit()
            logger.info(f"Cleaned up {count} expired password reset tokens")

        return count

    except Exception as e:
        await db.rollback()
        logger.error(f"Error cleaning up expired tokens: {str(e)}")
        raise
