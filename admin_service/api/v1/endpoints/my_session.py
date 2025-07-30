from typing import Annotated

import jwt
from fastapi import (
    APIRouter,
    Depends,
    Response,
)
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_service.schemas.session import (
    SessionInfo,
    SessionListResponse,
    SessionTerminateResponse,
)
from admin_service.services.session_management import SessionManager
from shared.core.api_response import api_response
from shared.core.config import PUBLIC_KEY, settings
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, AdminUserDeviceSession
from shared.db.sessions.database import get_db
from shared.dependencies.admin import (
    extract_token_from_request,
    get_current_active_user,
)
from shared.utils.exception_handlers import exception_handler

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=SessionListResponse)
@exception_handler
async def get_user_sessions(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    active_only: bool = True,
    limit: int = 10,
) -> JSONResponse:
    """Get all sessions for the current user"""
    sessions = await SessionManager.get_user_sessions(
        current_user.user_id, db, active_only=active_only, limit=limit
    )

    # Format sessions for response
    formatted_sessions = []
    for session in sessions:
        formatted_sessions.append(
            SessionInfo(
                session_id=session.session_id,
                device_name=session.device_name or "Unknown Device",
                browser=(
                    f"{session.browser_family or 'Unknown'} {session.browser_version or ''}".strip()
                ),
                os=f"{session.os_family or 'Unknown'} {session.os_version or ''}".strip(),
                location=session.location or "Unknown Location",
                ip_address=session.ip_address or "Unknown",
                is_active=session.is_active,
                logged_in_at=(
                    session.logged_in_at.isoformat()
                    if session.logged_in_at
                    else None
                ),
                last_used_at=(
                    session.last_used_at.isoformat()
                    if session.last_used_at
                    else None
                ),
                logged_out_at=(
                    session.logged_out_at.isoformat()
                    if session.logged_out_at
                    else None
                ),
                is_current=False,  # Will be updated below
            )
        )

    # Mark current session
    # Get session ID from token
    request = getattr(current_user, "_request", None)
    if request:
        token = extract_token_from_request(request)
        if token:
            try:
                public_key = PUBLIC_KEY.get_secret_value()
                if public_key:
                    payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=[settings.JWT_ALGORITHM],
                        options={"verify_exp": False},
                    )
                    current_session_id = payload.get("sid")
                    if current_session_id:
                        for session in formatted_sessions:
                            if session.session_id == current_session_id:
                                session.is_current = True
                                break
            except Exception as e:
                logger.warning(
                    f"Failed to decode token for session identification: {e}"
                )

    return api_response(
        status_code=200,
        message="User sessions retrieved successfully",
        data={"sessions": formatted_sessions},
    )


@router.delete("/{session_id}")
@exception_handler
async def terminate_user_session(
    session_id: int,
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Terminate a specific session for the current user"""
    # Verify the session belongs to the current user
    stmt = select(AdminUserDeviceSession).where(
        AdminUserDeviceSession.session_id == session_id,
        AdminUserDeviceSession.user_id == current_user.user_id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return api_response(
            status_code=404,
            message="Session not found or does not belong to current user",
        )

    # Check if this is the current session
    is_current_session = False
    request = getattr(current_user, "_request", None)
    if request:
        token = extract_token_from_request(request)
        if token:
            try:
                public_key = PUBLIC_KEY.get_secret_value()
                if public_key:
                    payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=[settings.JWT_ALGORITHM],
                        options={"verify_exp": False},
                    )
                    current_session_id = payload.get("sid")
                    if current_session_id and current_session_id == session_id:
                        is_current_session = True
            except Exception as e:
                logger.warning(
                    f"Failed to decode token for session identification: {e}"
                )

    # Terminate the session
    terminated = await SessionManager.terminate_session(
        session_id, db, reason="user_terminated"
    )

    if terminated:
        # If this was the current session, also clear cookies
        response_data = {"session_id": session_id}
        if is_current_session:
            response = Response()
            response.delete_cookie(
                key="access_token",
                path="/",
                samesite="lax",
                secure=False,  # Set to True in production with HTTPS
            )
            response_data["current_session"] = True

        return api_response(
            status_code=200,
            message="Session terminated successfully",
            data=response_data,
        )
    else:
        return api_response(
            status_code=400, message="Failed to terminate session"
        )


@router.delete("", response_model=SessionTerminateResponse)
@exception_handler
async def terminate_all_user_sessions(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    keep_current: bool = True,
) -> JSONResponse:
    """Terminate all sessions for the current user except the current one"""
    # Get current session ID from token
    current_session_id = None
    if keep_current:
        request = getattr(current_user, "_request", None)
        if request:
            token = extract_token_from_request(request)
            if token:
                try:
                    public_key = PUBLIC_KEY.get_secret_value()
                    if public_key:
                        payload = jwt.decode(
                            token,
                            public_key,
                            algorithms=[settings.JWT_ALGORITHM],
                            options={"verify_exp": False},
                        )
                        current_session_id = payload.get("sid")
                except Exception as e:
                    logger.warning(
                        f"Failed to decode token for session identification: {e}"
                    )

    # Terminate all sessions except current one
    terminated_count = await SessionManager.terminate_all_user_sessions(
        current_user.user_id,
        db,
        except_session_id=current_session_id if keep_current else None,
    )

    # If we're not keeping the current session, also clear cookies
    response_data = {"terminated_count": terminated_count}
    if not keep_current:
        response = Response()
        response.delete_cookie(
            key="access_token",
            path="/",
            samesite="lax",
            secure=False,  # Set to True in production with HTTPS
        )
        response_data["current_session_terminated"] = True

    return api_response(
        status_code=200,
        message=f"Terminated {terminated_count} sessions successfully",
        data=response_data,
    )
