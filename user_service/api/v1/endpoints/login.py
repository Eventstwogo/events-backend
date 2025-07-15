from datetime import datetime, timezone
from typing import Annotated, Optional, Union

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from shared.core.api_response import api_response
from shared.core.config import PRIVATE_KEY, PUBLIC_KEY, settings
from shared.core.logging_config import get_logger
from shared.db.models import User, UserDeviceSession
from shared.db.sessions.database import get_db
from shared.dependencies.user import extract_token_from_request, get_current_active_user
from user_service.schemas.session import (
    SessionInfo,
    SessionListResponse,
)
from user_service.schemas.user import UserMeOut
from user_service.services.auth import check_account_lock, check_password, check_password_expiry
from user_service.services.response_builders import (
    account_deactivated,
    login_success_response,
    password_expired_response,
    user_not_found_response,
)
from user_service.services.session_management import SessionManager, TokenSessionManager
from user_service.utils.auth import create_jwt_token, revoke_token, verify_jwt_token
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url

logger = get_logger(__name__)

router = APIRouter()


async def fetch_user_by_email(db: AsyncSession, email: str) -> User | None:
    query = User.by_email_query(email.lower())
    result = await db.execute(query)
    return result.scalar_one_or_none()


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/login/login")


@router.post("/login")
@exception_handler
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Handle user login with various validation checks"""
    # Perform initial validation checks
    validation_result = await validate_login_attempt(form_data, db)
    if isinstance(validation_result, JSONResponse):
        return validation_result

    user = validation_result

    # Process successful authentication
    return await process_successful_login(user, request, response, db)


async def validate_login_attempt(
    form_data: OAuth2PasswordRequestForm, db: AsyncSession
) -> Union[User, JSONResponse]:
    """Validate login credentials and account status"""
    # Step 1: Fetch user by email (OAuth2 uses username field for email)
    email = form_data.username.lower()
    user = await fetch_user_by_email(db, email)
    if not user:
        return user_not_found_response()

    # Step 1.1: Check account activation (is_active=False means active)
    if user.is_deleted:
        return account_deactivated()

    # Step 2: Check lock status
    locked_response = await check_account_lock(user, db)
    if locked_response:
        return locked_response

    # Step 3: Check password
    password_check_response = await check_password(user, form_data.password, db)
    if password_check_response:
        return password_check_response

    return user


async def process_successful_login(
    user: User, request: Request, response: Response, db: AsyncSession
) -> JSONResponse:
    """Process successful login and generate response"""
    # Step 5: 180-day password expiration policy
    now = datetime.now(timezone.utc)
    password_expired = await check_password_expiry(user, now)

    # Step 6: Final login updates
    user.last_login = now
    user.failure_login_attempts = 0
    user.successful_login_count += 1

    await db.commit()
    await db.refresh(user)

    # Step 7: Create a comprehensive device session record
    session = await SessionManager.create_session(user, request, db, include_location=True)

    # Step 7.1: Check for suspicious activity
    suspicious_alerts = await SessionManager.detect_suspicious_activity(user.user_id, session, db)

    if suspicious_alerts:
        logger.warning(f"Suspicious activity detected for user {user.user_id}: {suspicious_alerts}")

    # Step 8: Generate JWT access token with session information
    access_token = create_jwt_token(
        data={
            "uid": user.user_id,
            "sid": session.session_id,
            "device_name": session.device_name,
            "token_type": "access",
        },
        private_key=PRIVATE_KEY.get_secret_value(),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
    )

    # Step 9: Generate refresh token with session information
    refresh_token = create_jwt_token(
        data={
            "uid": user.user_id,
            "sid": session.session_id,
            "device_name": session.device_name,
            "token_type": "refresh",
        },
        private_key=PRIVATE_KEY.get_secret_value(),
        expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Convert days to seconds
    )

    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set True in production with HTTPS
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
        path="/",
        domain=None,  # Let browser determine domain
    )

    # Also set the token in the Authorization header for better compatibility
    response.headers["Authorization"] = f"Bearer {access_token}"

    logger.info(f"Set access token cookie and Authorization header for user {user.user_id}")

    # Step 10: Return appropriate response
    if password_expired:
        return password_expired_response(user, access_token, refresh_token)

    # Return successful login response
    return login_success_response(user, access_token, refresh_token, session.session_id)


@router.post("/logout")
@exception_handler
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Handle user logout by clearing cookies, revoking tokens, and deactivating sessions"""

    # Step 1: Clear access token cookie with proper settings
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
    )

    # Step 2: Extract token from request
    token = extract_token_from_request(request)

    # If we have a current user from the token, use that directly
    if current_user:
        user_id = current_user.user_id

        # Get the session ID from the token
        session_id = None
        if token:
            try:
                public_key = PUBLIC_KEY.get_secret_value()
                if public_key:
                    payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=[settings.JWT_ALGORITHM],
                        options={"verify_exp": False},  # Allow expired tokens for logout
                    )
                    session_id = payload.get("sid")
            except Exception as e:
                logger.warning(f"Token decode failed during logout: {e}")

        # Terminate the session if we have a session_id
        if session_id:
            try:
                session_terminated = await SessionManager.terminate_session(
                    session_id, db, reason="user_logout"
                )
                if session_terminated:
                    logger.info(f"Session {session_id} terminated for user {user_id}")
                else:
                    logger.warning(f"Failed to terminate session {session_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Error terminating session {session_id}: {e}")
        else:
            logger.info(f"No session_id found in token for user {user_id}")

        # Revoke the token
        if token:
            try:
                public_key = PUBLIC_KEY.get_secret_value()
                if public_key:
                    revoke_token(token, public_key)
                    logger.info("Access token revoked successfully")
            except Exception as e:
                logger.warning(f"Failed to revoke access token: {e}")

        return api_response(
            status_code=200,
            message="Logout successful.",
            data={"user_id": user_id},
        )

    # If we don't have a current user but have a token, try to extract info from it
    if token and not current_user:
        try:
            public_key = PUBLIC_KEY.get_secret_value()
            if not public_key:
                logger.warning("Public key not available for token verification during logout")
                return api_response(status_code=200, message="Logout successful.")

            # Revoke the access token
            try:
                revoke_token(token, public_key)
                logger.info("Access token revoked successfully")
            except Exception as e:
                logger.warning(f"Failed to revoke access token: {e}")

            # Decode token to get user and session information
            user_id = None
            session_id = None
            refresh_token_from_payload = None

            try:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={"verify_exp": False},  # Allow expired tokens for logout
                )
                user_id = payload.get("uid")
                session_id = payload.get("sid")

                # Check if this is a refresh token that contains refresh token info
                if payload.get("token_type") == "refresh":
                    refresh_token_from_payload = token

            except Exception as e:
                logger.warning(f"Token decode failed during logout: {e}")
                return api_response(
                    status_code=200,
                    message="Logout successful (token processed).",
                )

            # Handle session deactivation if we have user information
            if user_id:
                if session_id:
                    session_terminated = await SessionManager.terminate_session(
                        session_id, db, reason="user_logout"
                    )
                    if session_terminated:
                        logger.info(f"Session {session_id} terminated for user {user_id}")
                    else:
                        logger.warning(
                            f"Failed to terminate session {session_id} for user {user_id}"
                        )
                else:
                    # Fallback for older tokens without session_id
                    ip_address = request.client.host if request.client else None
                    if ip_address:
                        # Get all active sessions for the user and find by IP
                        active_sessions = await SessionManager.get_user_sessions(
                            user_id, db, active_only=True
                        )
                        session_found = False
                        for session in active_sessions:
                            if session.ip_address == ip_address:
                                await SessionManager.terminate_session(
                                    session.session_id,
                                    db,
                                    reason="user_logout_ip_match",
                                )
                                session_found = True
                                logger.info(
                                    f"Session {session.session_id} terminated for user {user_id} by IP match"
                                )
                                break

                        if not session_found:
                            logger.warning(
                                f"No matching session found for user {user_id} with IP {ip_address}"
                            )
                    else:
                        logger.warning(
                            f"No IP address available for fallback session termination for user {user_id}"
                        )

            # Handle refresh token revocation if we have one
            if refresh_token_from_payload:
                try:
                    # The current token is already a refresh token, so we just revoked it above
                    logger.info("Refresh token revoked during logout")
                except Exception as e:
                    logger.warning(f"Failed to revoke refresh token during logout: {e}")

        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Even if there's an error, we still want to return success for security
            return api_response(status_code=200, message="Logout successful.")

    return api_response(status_code=200, message="Logout successful.")
