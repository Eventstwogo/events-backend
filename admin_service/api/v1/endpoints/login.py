from datetime import datetime, timezone
from typing import Annotated, Union

import jwt
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_service.services.auth import (
    check_account_lock,
    check_password,
    check_password_expiry,
)
from admin_service.services.response_builders import (
    account_deactivated,
    account_not_approved,
    email_not_verified_response,
    initial_login_response,
    login_success_response,
    password_expired_response,
    user_not_found_response,
)
from admin_service.services.session_management import (
    SessionManager,
    TokenSessionManager,
)
from admin_service.services.user_service import (
    check_user_email_verified,
    get_user_by_email,
    get_user_role_name,
)
from admin_service.utils.auth import revoke_token
from lifespan import PUBLIC_KEY, settings
from shared.constants import (
    ONBOARDING_APPROVED,
    ONBOARDING_NOT_STARTED,
    ONBOARDING_REJECTED,
    ONBOARDING_SUBMITTED,
)
from shared.core.api_response import api_response
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, BusinessProfile
from shared.db.sessions.database import get_db
from shared.dependencies.admin import (
    extract_token_from_request,
    get_current_user,
)
from shared.utils.exception_handlers import exception_handler

logger = get_logger(__name__)

router = APIRouter()


async def get_organizer_profile_info(user: AdminUser, db: AsyncSession) -> dict:
    """
    Returns organizer business profile approval status and onboarding progress.

    For Organizer users:
    - Fetches actual BusinessProfile info
    - Determines onboarding_status from is_approved and verification state

    For non-Organizer users:
    - Returns is_approved=2 (approved) to allow frontend flow

    Returns:
        dict: Contains is_approved, ref_number, and onboarding_status
    """
    user_role_name = await get_user_role_name(db, user.user_id)

    # Non-organizer users
    if not user_role_name or user_role_name.lower() != "organizer":
        return {
            "is_approved": ONBOARDING_APPROVED,
            "ref_number": "",
            "reviewer_comment": "",
            "onboarding_status": "approved",
        }

    # Default for organizers
    is_approved = ONBOARDING_NOT_STARTED
    ref_number = ""
    reviewer_comment = ""
    onboarding_status = "not_started"

    # Fetch business profile data
    profile_stmt = select(
        BusinessProfile.is_approved,
        BusinessProfile.ref_number,
        BusinessProfile.reviewer_comment,
    ).where(BusinessProfile.business_id == user.business_id)

    result = await db.execute(profile_stmt)
    profile = result.one_or_none()

    if profile:
        is_approved, ref_number, reviewer_comment_from_db = profile

        if is_approved == ONBOARDING_APPROVED and user.is_verified:
            onboarding_status = "approved"
        elif is_approved == ONBOARDING_REJECTED:
            onboarding_status = "rejected"
            reviewer_comment = reviewer_comment_from_db or ""
        elif is_approved == ONBOARDING_SUBMITTED:
            onboarding_status = (
                "under_review" if not user.is_verified else "approved"
            )
        else:
            onboarding_status = "submitted"
    else:
        is_approved = ONBOARDING_NOT_STARTED
        onboarding_status = "not_started"

    return {
        "is_approved": is_approved,
        "ref_number": ref_number or "",
        "reviewer_comment": reviewer_comment,
        "onboarding_status": onboarding_status,
    }


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
) -> Union[AdminUser, JSONResponse]:
    """Validate login credentials and account status"""
    # Step 1: Fetch user by email (OAuth2 uses username field for email)
    email = form_data.username.lower()
    user = await get_user_by_email(db, email)
    if not user:
        return user_not_found_response()

    # Step 1.1: Email verification check
    email_verified = await check_user_email_verified(db, user.user_id)
    if not email_verified:
        return email_not_verified_response()

    # # Step 1.2: Account approval check
    # if user.is_verified != 1:
    #     return account_not_approved()

    # Step 1.3: Check account activation (is_active=False means active)
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

    # Step 4: Handle first-time login (status -1)
    if user.login_status == -1:
        return initial_login_response(user)

    return user


async def process_successful_login(
    user: AdminUser, request: Request, response: Response, db: AsyncSession
) -> JSONResponse:
    """Process successful login and generate response"""
    # Step 5: 180-day password expiration policy
    now = datetime.now(timezone.utc)
    password_expired = await check_password_expiry(user, now)

    # Step 6: Final login updates
    user.last_login = now
    user.failure_login_attempts = 0
    user.successful_login_count += 1

    # Step 7: Create a comprehensive device session record
    session = await SessionManager.create_session(
        user, request, db, include_location=True
    )

    # Step 7.1: Check for suspicious activity
    suspicious_alerts = await SessionManager.detect_suspicious_activity(
        user.user_id, session, db
    )
    if suspicious_alerts:
        # Log suspicious activity (you might want to send notifications here)
        for alert in suspicious_alerts:
            logger.warning(
                f"Suspicious activity detected for user {user.user_id}: {alert['message']}"
            )

    await db.refresh(user)

    # Step 8: Get organizer profile information if user is an organizer
    organizer_info = await get_organizer_profile_info(user, db)

    # Step 9: Generate JWT access token with session information
    access_token = TokenSessionManager.create_token_with_session(
        user, session, "access"
    )

    # Step 10: Generate refresh token with session information
    refresh_token = TokenSessionManager.create_token_with_session(
        user, session, "refresh"
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

    logger.info(
        f"Set access token cookie and Authorization header for user {user.user_id}"
    )

    # Step 11: Return appropriate response
    if password_expired:
        return password_expired_response(
            user, access_token, refresh_token, organizer_info
        )

    # Return successful login response
    return login_success_response(
        user, access_token, refresh_token, session.session_id, organizer_info
    )


@router.post("/logout")
@exception_handler
async def logout(
    request: Request,
    response: Response,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
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
                        options={
                            "verify_exp": False
                        },  # Allow expired tokens for logout
                    )
                    session_id = payload.get("sid")
            except Exception as e:
                logger.warning(f"Token decode failed during logout: {e}")

        # Terminate the session
        if session_id:
            session_terminated = await SessionManager.terminate_session(
                session_id, db, reason="user_logout"
            )
            if session_terminated:
                logger.info(
                    f"Session {session_id} terminated for user {user_id}"
                )
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
                            f"Session {session.session_id} terminated for user {user_id}"
                            " by IP match"
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
                logger.warning(
                    "Public key not available for token verification during logout"
                )
                return api_response(
                    status_code=200, message="Logout successful."
                )

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
                    options={
                        "verify_exp": False
                    },  # Allow expired tokens for logout
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
                        logger.info(
                            f"Session {session_id} terminated for user {user_id}"
                        )
                    else:
                        logger.warning(
                            f"Failed to terminate session {session_id} for user {user_id}"
                        )
                else:
                    # Fallback for older tokens without session_id
                    ip_address = request.client.host if request.client else None
                    if ip_address:
                        # Get all active sessions for the user and find by IP
                        active_sessions = (
                            await SessionManager.get_user_sessions(
                                user_id, db, active_only=True
                            )
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
                                    f"Session {session.session_id} terminated for user {user_id}"
                                    " by IP match"
                                )
                                break

                        if not session_found:
                            logger.warning(
                                f"No matching session found for user {user_id} with IP {ip_address}"
                            )
                    else:
                        logger.warning(
                            "No IP address available for fallback session termination "
                            f"for user {user_id}"
                        )

            # Handle refresh token revocation if we have one
            if refresh_token_from_payload:
                try:
                    # The current token is already a refresh token, so we just revoked it above
                    logger.info("Refresh token revoked during logout")
                except Exception as e:
                    logger.warning(
                        f"Failed to revoke refresh token during logout: {e}"
                    )

        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Even if there's an error, we still want to return success for security
            return api_response(status_code=200, message="Logout successful.")

    return api_response(status_code=200, message="Logout successful.")
