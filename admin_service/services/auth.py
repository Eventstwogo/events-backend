# auth_service.py
from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.utils.auth import create_jwt_token, verify_password
from shared.constants import (
    ACCOUNT_LOCKED_STATUS,
    ACCOUNT_LOCKOUT_DURATION_HOURS,
    ACTIVE_LOGIN_STATUS,
    MAX_LOGIN_ATTEMPTS_BEFORE_LOCKOUT,
    PASSWORD_EXPIRED_DAYS,
    PASSWORD_EXPIRED_STATUS,
)
from shared.core.api_response import api_response
from shared.core.config import PRIVATE_KEY, settings
from shared.db.models import AdminUser, AdminUserDeviceSession


async def check_account_lock(
    user: AdminUser, db: AsyncSession
) -> JSONResponse | None:
    if user.login_status == ACCOUNT_LOCKED_STATUS:
        if user.account_locked_at and (
            datetime.now(timezone.utc) - user.account_locked_at
        ) < timedelta(hours=ACCOUNT_LOCKOUT_DURATION_HOURS):
            return api_response(
                status_code=status.HTTP_423_LOCKED,
                message=(
                    "Account is temporarily locked due to multiple failed login attempts. "
                    f"Try again after {ACCOUNT_LOCKOUT_DURATION_HOURS} hours."
                ),
                log_error=True,
            )
        user.login_status = ACTIVE_LOGIN_STATUS
        user.failure_login_attempts = 0
        await db.commit()
    return None


async def check_password(
    user: AdminUser, password: str, db: AsyncSession
) -> JSONResponse | None:
    if not verify_password(password, user.password_hash):
        user.failure_login_attempts += 1
        await db.commit()

        remaining_attempts = (
            MAX_LOGIN_ATTEMPTS_BEFORE_LOCKOUT - user.failure_login_attempts
        )

        if user.failure_login_attempts >= MAX_LOGIN_ATTEMPTS_BEFORE_LOCKOUT:
            user.login_status = ACCOUNT_LOCKED_STATUS
            user.account_locked_at = datetime.now(timezone.utc)
            await db.commit()
            return api_response(
                status_code=status.HTTP_423_LOCKED,
                message=(
                    f"Account locked after {MAX_LOGIN_ATTEMPTS_BEFORE_LOCKOUT} failed "
                    f"login attempts. Try again after {ACCOUNT_LOCKOUT_DURATION_HOURS} hours."
                ),
                log_error=True,
            )

        return api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=f"Incorrect password. {remaining_attempts} attempt(s) remaining before account lock.",
            log_error=True,
        )

    return None


def generate_token(user: AdminUser) -> str:
    return create_jwt_token(
        data={
            "uid": user.user_id,
            "rid": user.role_id,
            "token_type": "access",
        },
        private_key=PRIVATE_KEY.get_secret_value(),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
    )


async def check_password_expiry(user: AdminUser, now: datetime) -> bool:
    if user.days_180_flag and user.days_180_timestamp:
        if (now - user.days_180_timestamp).days >= PASSWORD_EXPIRED_DAYS:
            user.login_status = PASSWORD_EXPIRED_STATUS
            return True
    elif user.days_180_flag:
        user.days_180_timestamp = now
    return False


async def update_session_activity(db: AsyncSession, session_id: int) -> bool:
    """Update the last_used_at timestamp for a session"""
    stmt = select(AdminUserDeviceSession).where(
        AdminUserDeviceSession.session_id == session_id,
        AdminUserDeviceSession.is_active.is_(True),
    )

    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return False

    session.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return True
