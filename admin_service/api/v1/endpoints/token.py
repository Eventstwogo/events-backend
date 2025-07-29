from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.schemas.token import TokenRefreshRequest, TokenResponse
from admin_service.services.session_management import TokenSessionManager
from admin_service.utils.auth import (
    create_jwt_token,
    revoke_token,
    verify_jwt_token,
)
from shared.core.api_response import api_response
from shared.core.config import PRIVATE_KEY, PUBLIC_KEY, settings
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, AdminUserDeviceSession
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

logger = get_logger(__name__)

# Token type constants to avoid hardcoded strings
TOKEN_TYPE_ACCESS = "access"  # nosec B105
TOKEN_TYPE_REFRESH = "refresh"  # nosec B105

router = APIRouter()


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
@exception_handler
async def refresh_token(
    request: Request,
    response: Response,
    refresh_data: TokenRefreshRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Refresh an expired access token using a valid refresh token.

    Args:
        refresh_data: The refresh token data

    Returns:
        JSONResponse: New access and refresh tokens
    """
    refresh_token = refresh_data.refresh_token

    # Verify the refresh token
    try:
        # Decode the refresh token
        payload = verify_jwt_token(
            token=refresh_token,
            public_key=PUBLIC_KEY.get_secret_value(),
        )

        # Extract user information from the token
        user_id = payload.get("uid")
        if not user_id:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid refresh token: missing user ID.",
                log_error=True,
            )

        # Extract session ID if available
        session_id = payload.get("sid")

        # Extract token JTI for revocation
        token_jti = payload.get("jti")
        if not token_jti:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid refresh token: missing token ID.",
                log_error=True,
            )

        # Check token type
        token_type = payload.get("token_type")
        if token_type != TOKEN_TYPE_REFRESH:
            return api_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid token type. Expected refresh token.",
                log_error=True,
            )

        # Check if the user exists and is active
        stmt = select(AdminUser).where(AdminUser.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found.",
                log_error=True,
            )

        if user.is_deleted:
            return api_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="User account is deactivated.",
                log_error=True,
            )

        # Validate session if session ID is present
        session = None
        if session_id:
            # Validate session using SessionManager
            session_valid, session_error = (
                await TokenSessionManager.validate_token_session(payload, db)
            )
            if not session_valid:
                return api_response(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message=f"Session validation failed: {session_error}",
                    log_error=True,
                )

            # Get session for token generation
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.session_id == session_id,
                AdminUserDeviceSession.user_id == user_id,
                AdminUserDeviceSession.is_active.is_(True),
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

        # Implement token rotation - revoke the used refresh token
        # This prevents refresh token reuse and session hijacking
        try:
            revoke_token(refresh_token, PUBLIC_KEY.get_secret_value())
            logger.info(f"Refresh token rotated for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to revoke old refresh token: {e}")

        # Generate new tokens
        if session:
            # Update session last_used_at timestamp
            session.last_used_at = datetime.now(timezone.utc)
            await db.commit()

            # Generate tokens with session information
            new_access_token = TokenSessionManager.create_token_with_session(
                user, session, TOKEN_TYPE_ACCESS
            )
            new_refresh_token = TokenSessionManager.create_token_with_session(
                user, session, TOKEN_TYPE_REFRESH
            )
        else:
            # Generate tokens without session (legacy support)
            new_access_token = create_jwt_token(
                data={
                    "uid": user.user_id,
                    "rid": user.role_id,
                    "token_type": TOKEN_TYPE_ACCESS,
                },
                private_key=PRIVATE_KEY.get_secret_value(),
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
            )
            new_refresh_token = create_jwt_token(
                data={
                    "uid": user.user_id,
                    "token_type": TOKEN_TYPE_REFRESH,
                },
                private_key=PRIVATE_KEY.get_secret_value(),
                expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS,
            )

        # Update user's last activity
        user.last_login = datetime.now(timezone.utc)
        await db.commit()

        # Set the new access token cookie
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=False,  # Set True in production
            samesite="lax",
            max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
            path="/",
        )

        # Return new tokens
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Token refreshed successfully.",
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "session_id": session_id if session_id else None,
            },
        )

    except ValueError as ve:
        return api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=f"Invalid refresh token: {str(ve)}",
            log_error=True,
        )
    except Exception as e:
        return api_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=f"Error processing refresh token: {str(e)}",
            log_error=True,
        )


@router.post("/revoke", summary="Revoke refresh token")
@exception_handler
async def perform_revoke_token(
    refresh_data: TokenRefreshRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Revoke a refresh token to prevent it from being used again.

    This will deactivate the associated session if found.

    Args:
        refresh_data: The refresh token to revoke

    Returns:
        JSONResponse: Success message
    """
    refresh_token = refresh_data.refresh_token

    try:
        # Decode the token to get session information
        payload = verify_jwt_token(
            token=refresh_token,
            public_key=PUBLIC_KEY.get_secret_value(),
        )

        # Extract session ID and user ID if available
        session_id = payload.get("sid")
        user_id = payload.get("uid")

        if session_id and user_id:
            # Find and deactivate the session
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.session_id == session_id,
                AdminUserDeviceSession.user_id == user_id,
                AdminUserDeviceSession.is_active.is_(True),
            )

            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if session:
                session.is_active = False
                await db.commit()

                return api_response(
                    status_code=status.HTTP_200_OK,
                    message="Token revoked and session terminated successfully.",
                )

    except Exception as e:
        # If token verification fails, we still want to acknowledge the revocation
        logger.warning(f"Token verification failed during revocation: {e}")

    # Return success even if we couldn't find/deactivate a session
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Token revoked successfully.",
    )
