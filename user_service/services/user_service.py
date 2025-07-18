from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.logging_config import get_logger
from shared.db.models import Config, Role, User
from user_service.utils.user_validators import is_account_locked

logger = get_logger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    query = User.by_email_query(email.lower())
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def check_user_exists_by_email(db: AsyncSession, email: str) -> bool:
    query = User.by_email_query(email.lower())
    query = query.with_only_columns(User.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def check_user_exists_by_username(
    db: AsyncSession, username: str
) -> bool:
    query = User.by_username_query(username.lower())
    query = query.with_only_columns(User.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    query = User.by_username_query(username.lower())
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    return result.scalar_one_or_none()


async def get_config_or_404(db: AsyncSession) -> Config | None:
    config_result = await db.execute(select(Config).limit(1))
    return config_result.scalar_one_or_none()


async def fetch_locked_user_by_username(
    db: AsyncSession, username: str
) -> tuple[User, bool] | None:
    user_result = await get_user_by_username(db, username)
    if not isinstance(user_result, User):
        return user_result

    locked = is_account_locked(user_result)

    return (user_result, locked)
