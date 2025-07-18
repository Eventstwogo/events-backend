from typing import Annotated, Optional

from fastapi import (
    Depends,
    HTTPException,
    Request,
)
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.services.response_builders import (
    user_not_found_response,
)
from admin_service.services.session_management import TokenSessionManager
from admin_service.services.user_service import get_user_by_id
from admin_service.utils.auth import verify_jwt_token
from shared.core.config import PUBLIC_KEY
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser
from shared.db.sessions.database import get_db

logger = get_logger(__name__)

# OAuth2 scheme for token authentication
admin_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/admin/login", scheme_name="AdminAuth"
)

# Alternative Bearer token scheme for admin
admin_bearer_scheme = HTTPBearer(scheme_name="AdminBearer")


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(admin_oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> AdminUser | JSONResponse:
    """Get current authenticated user from JWT token"""
    # Try OAuth2 token first, then fallback to request extraction
    auth_token = token or extract_token_from_request(request)
    if not auth_token:
        raise HTTPException(
            status_code=401, detail="Missing authentication token"
        )
    user = await get_current_user_from_token(auth_token, db)

    # Store the request object for later use (to access token in other endpoints)
    setattr(user, "_request", request)

    return user


async def get_current_active_user(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
) -> AdminUser:
    """Get current active user (ensure user is not deleted/disabled)"""
    if current_user.is_deleted:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def extract_token_from_request(request: Request) -> Optional[str]:
    """Extract token from Authorization header or cookie"""
    header = request.headers.get("authorization")
    if header and header.startswith("Bearer "):
        return header[7:]
    cookie = request.cookies.get("access_token")
    return (
        cookie
        if cookie and cookie.lower() not in ["undefined", "null"]
        else None
    )


async def get_current_user_from_token(
    token: str, db: AsyncSession
) -> AdminUser | JSONResponse:
    """Get current authenticated user from JWT token with session validation"""
    public_key = PUBLIC_KEY.get_secret_value()
    if not public_key:
        logger.error("Missing public key for token verification")
        raise HTTPException(status_code=401, detail="Token verification failed")

    try:
        payload = verify_jwt_token(token, public_key)
        user_id = payload.get("uid")
        if not user_id:
            raise ValueError("Missing user_id")
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Validate session if session info is present in token
    session_valid, session_error = (
        await TokenSessionManager.validate_token_session(payload, db)
    )
    if not session_valid:
        logger.warning(f"Session validation failed: {session_error}")
        raise HTTPException(status_code=401, detail="Session no longer valid")

    user = await get_user_by_id(db, user_id)
    if not user:
        return user_not_found_response()

    if user.is_deleted:
        raise HTTPException(status_code=401, detail="Inactive user")

    return user
