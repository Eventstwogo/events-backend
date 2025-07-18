"""
AdminUser validation services for the Events2Go application.
"""

from typing import Optional

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser
from shared.db.models.rbac import Role

logger = get_logger(__name__)


async def validate_unique_user(
    db: AsyncSession,
    username: str,
    email: str,
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
    query = AdminUser.by_username_query(username.lower())
    username_query = await db.execute(query)
    if username_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Username already exists. Please choose a different username.",
            log_error=True,
        )

    # Check for existing email
    query = AdminUser.by_email_query(email.lower())
    email_query = await db.execute(query)
    if email_query.scalar_one_or_none():
        return api_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Email already exists. Please use a different email address.",
            log_error=True,
        )

    return None


async def validate_role(db: AsyncSession, role_id: str) -> JSONResponse | Role:
    role_query = await db.execute(select(Role).where(Role.role_id == role_id))
    role = role_query.scalar_one_or_none()
    if not role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Role not found.",
            log_error=True,
        )
    if role.role_status:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Role is inactive.",
            log_error=True,
        )
    return role


async def validate_superadmin_uniqueness(
    db: AsyncSession, role: Role
) -> JSONResponse | None:
    if role.role_name.lower() in {"superadmin", "super admin"}:
        superadmin_query = await db.execute(
            select(AdminUser).where(AdminUser.role_id == role.role_id)
        )
        if superadmin_query.scalar_one_or_none():
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message=(
                    "Super Admin already exists. Only one Super Admin is allowed. "
                    "Please register with a different role."
                ),
                log_error=True,
            )
    return None
