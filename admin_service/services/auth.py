# auth_service.py
from datetime import datetime, timedelta, timezone
from fastapi import status
from starlette.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.api_response import api_response
from shared.core.config import PRIVATE_KEY, settings
from shared.db.models import AdminUser, AdminUserDeviceSession
from admin_service.utils.auth import create_jwt_token, verify_password
from sqlalchemy import select


async def check_account_lock(user: AdminUser, db: AsyncSession) -> JSONResponse | None:
    if user.login_status == 1:
        if user.last_login and (datetime.now(timezone.utc) - user.last_login) < timedelta(hours=24):
            return api_response(
                status_code=status.HTTP_423_LOCKED,
                message=(
                    "Account is temporarily locked due to multiple failed login attempts. "
                    "Try again after 24 hours."
                ),
                log_error=True,
            )
        user.login_status = 0
        user.failure_login_attempts = 0
        await db.commit()
    return None


async def check_password(user: AdminUser, password: str, db: AsyncSession) -> JSONResponse | None:
    if not verify_password(password, user.password_hash):
        user.failure_login_attempts += 1
        if user.failure_login_attempts >= 3:
            user.login_status = 1
            user.last_login = datetime.now(timezone.utc)
            await db.commit()
            return api_response(
                status_code=status.HTTP_423_LOCKED,
                message="Account locked after 3 failed login attempts. Try again after 24 hours.",
                log_error=True,
            )
        await db.commit()
        return api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid credentials.",
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
        if (now - user.days_180_timestamp).days >= 180:
            user.login_status = 2
            return True
    elif user.days_180_flag:
        user.days_180_timestamp = now
    return False


async def update_session_activity(db: AsyncSession, session_id: int) -> bool:
    """Update the last_used_at timestamp for a session"""
    stmt = select(AdminUserDeviceSession).where(
        AdminUserDeviceSession.session_id == session_id,
        AdminUserDeviceSession.is_active == True,
    )

    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return False

    session.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return True
