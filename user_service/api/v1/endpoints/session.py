from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, Header, Path, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.core.config import PUBLIC_KEY
from shared.db.models import User, UserDeviceSession
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from user_service.schemas.session import DeviceSessionResponse
from user_service.services.auth import update_session_activity
from user_service.utils.auth import verify_jwt_token

router = APIRouter()


async def get_current_session_id(
    request: Request,
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
) -> Optional[int]:
    """
    Extract the current session ID from the JWT token if available.

    Returns:
        Optional[int]: The session ID or None if not found
    """
    # Get the token from cookie or authorization header
    token = access_token
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]

    if not token:
        return None

    try:
        # Decode the token
        payload = verify_jwt_token(
            token=token,
            public_key=PUBLIC_KEY.get_secret_value(),
        )

        # Check if session_id is in the payload
        return payload.get("sid")
    except Exception:
        return None


@router.get(
    "/",
    response_model=List[DeviceSessionResponse],
    summary="Get user sessions",
)
@exception_handler
async def get_user_sessions(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
) -> JSONResponse:
    """
    Get all active sessions for the current user.

    Returns:
        JSONResponse: List of active device sessions
    """
    current_session_id = await get_current_session_id(
        request, authorization, access_token
    )

    # Query user with device sessions using selectinload for efficient loading
    stmt = (
        select(User)
        .options(selectinload(User.device_sessions))
        .where(User.user_id == user_id)
    )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found.",
            log_error=True,
        )

    # Filter active sessions and sort by last_used_at (most recent first)
    sessions = sorted(
        [session for session in user.device_sessions if session.is_active],
        key=lambda s: s.last_used_at or s.logged_in_at,
        reverse=True,
    )

    if not sessions:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="No active sessions found.",
            data=[],
        )

    # Mark the current session
    for session in sessions:
        if current_session_id and session.session_id == current_session_id:
            setattr(session, "is_current", True)
        else:
            setattr(session, "is_current", False)

    # Update the current session's last_used_at timestamp
    if current_session_id:
        await update_session_activity(db, current_session_id)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Sessions retrieved successfully.",
        data=sessions,
    )


@router.delete("/{session_id}", summary="Terminate a specific session")
@exception_handler
async def terminate_session(
    request: Request,
    user_id: str,
    session_id: int = Path(
        ..., title="Session ID", description="ID of the session to terminate"
    ),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
) -> JSONResponse:
    """
    Terminate a specific user session by its ID.

    Args:
        session_id: The ID of the session to terminate

    Returns:
        JSONResponse: Success message
    """
    current_session_id = await get_current_session_id(
        request, authorization, access_token
    )

    # Check if trying to terminate the current session
    if current_session_id and current_session_id == session_id:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot terminate your current session. Use the logout endpoint instead.",
            log_error=True,
        )

    # Query the specific session
    stmt = select(UserDeviceSession).where(
        UserDeviceSession.session_id == session_id,
        UserDeviceSession.user_id == user_id,
    )

    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Session not found or does not belong to the current user.",
            log_error=True,
        )

    if not session.is_active:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Session is already inactive.",
            log_error=True,
        )

    # Deactivate the session
    session.is_active = False
    await db.commit()

    # Update the current session's last_used_at timestamp
    if current_session_id:
        await update_session_activity(db, current_session_id)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Session terminated successfully.",
    )


@router.delete("/", summary="Terminate all sessions except current")
@exception_handler
async def terminate_all_sessions(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
) -> JSONResponse:
    """
    Terminate all user sessions except the current one.

    Returns:
        JSONResponse: Success message with count of terminated sessions
    """
    current_session_id = await get_current_session_id(
        request, authorization, access_token
    )

    # Query all active sessions for the user
    stmt = select(UserDeviceSession).where(
        UserDeviceSession.user_id == user_id,
        UserDeviceSession.is_active == True,
    )

    result = await db.execute(stmt)
    sessions = result.scalars().all()

    if not sessions:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="No active sessions to terminate.",
        )

    # Deactivate all sessions except the current one
    terminated_count = 0
    for session in sessions:
        if not current_session_id or session.session_id != current_session_id:
            session.is_active = False
            terminated_count += 1

    await db.commit()

    # Update the current session's last_used_at timestamp
    if current_session_id:
        await update_session_activity(db, current_session_id)

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Successfully terminated {terminated_count} sessions.",
        data={"terminated_count": terminated_count},
    )
