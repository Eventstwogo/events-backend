from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_service.utils.user_validators import is_account_locked
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser
from shared.db.models.admin_users import AdminUserVerification
from shared.db.models.config import Config
from shared.db.models.rbac import Role

logger = get_logger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> AdminUser | None:
    query = AdminUser.by_email_query(email.lower())
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_user_email_verified(db: AsyncSession, user_id: str) -> bool:
    """
    Check if a user's email is verified without triggering lazy loading.

    Args:
        db: Database session
        user_id: The user ID to check

    Returns:
        bool: True if email is verified, False otherwise
    """
    result = await db.execute(
        select(AdminUserVerification.email_verified).where(
            AdminUserVerification.user_id == user_id
        )
    )
    verification_data = result.scalar_one_or_none()
    return verification_data is True if verification_data is not None else False


async def get_all_admin_users(db: AsyncSession) -> List[AdminUser]:
    """
    Get all users who have the ADMIN role.

    Args:
        db: Database session

    Returns:
        List[AdminUser]: List of admin users
    """
    result = await db.execute(
        select(AdminUser)
        .join(Role, Role.role_id == AdminUser.role_id)
        .where(Role.role_name == "ADMIN")
    )
    admin_users = list(result.scalars().all())
    return admin_users


async def get_user_role_name(db: AsyncSession, user_id: str) -> Optional[str]:
    """
    Get a user's role name without triggering lazy loading.

    Args:
        db: Database session
        user_id: The user ID to check

    Returns:
        Optional[str]: The role name if found, None otherwise
    """
    result = await db.execute(
        select(Role.role_name)
        .join(AdminUser, AdminUser.role_id == Role.role_id)
        .where(AdminUser.user_id == user_id)
    )
    role_name = result.scalar_one_or_none()
    return role_name


async def get_user_by_id(db: AsyncSession, user_id: str) -> AdminUser | None:
    result = await db.execute(
        select(AdminUser).where(AdminUser.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def check_user_exists_by_email(db: AsyncSession, email: str) -> bool:
    query = AdminUser.by_email_query(email.lower())
    query = query.with_only_columns(AdminUser.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def check_user_exists_by_username(
    db: AsyncSession, username: str
) -> bool:
    query = AdminUser.by_username_query(username.lower())
    query = query.with_only_columns(AdminUser.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def get_user_by_username(
    db: AsyncSession, username: str
) -> AdminUser | None:
    query = AdminUser.by_username_query(username.lower())
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    stmt = select(Role).where(func.lower(Role.role_name) == func.lower(name))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_config_or_404(db: AsyncSession) -> Config | None:
    config_result = await db.execute(select(Config).limit(1))
    return config_result.scalar_one_or_none()


async def fetch_locked_user_by_username(
    db: AsyncSession, username: str
) -> tuple[AdminUser, bool] | None:
    user_result = await get_user_by_username(db, username)
    if not isinstance(user_result, AdminUser):
        return user_result

    locked = is_account_locked(user_result)

    return (user_result, locked)
