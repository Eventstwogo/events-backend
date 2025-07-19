from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_service.utils.auth import create_jwt_token
from shared.core.config import PRIVATE_KEY, settings
from shared.core.logging_config import get_logger
from shared.db.models import AdminUser, AdminUserDeviceSession
from shared.utils.device_info import (
    DeviceInfoExtractor,
    DeviceSessionManager,
    LocationService,
)

logger = get_logger(__name__)


class SessionManager:
    """Comprehensive session management service"""

    MAX_SESSIONS_PER_USER = 10  # Maximum active sessions per user

    @staticmethod
    async def create_session(
        user: AdminUser,
        request: Request,
        db: AsyncSession,
        include_location: bool = True,
    ) -> AdminUserDeviceSession:
        """
        Create a new device session with comprehensive device information.
        If a similar session exists (same device fingerprint and browser), reuse it.

        Args:
            user: The user for whom to create the session
            request: FastAPI request object
            db: Database session
            include_location: Whether to fetch location information

        Returns:
            AdminUserDeviceSession: The created or reused session
        """
        # Extract comprehensive device information
        device_info = DeviceInfoExtractor.extract_comprehensive_device_info(
            request
        )
        fingerprint = device_info.get("fingerprint")
        browser_family = device_info.get("browser_family")
        ip_address = device_info.get("ip_address")

        # Check for existing active session with same fingerprint and browser
        existing_session = None
        if fingerprint and browser_family:
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.user_id == user.user_id,
                AdminUserDeviceSession.is_active.is_(True),
                AdminUserDeviceSession.device_fingerprint == fingerprint,
                AdminUserDeviceSession.browser_family == browser_family,
            )
            result = await db.execute(stmt)
            existing_session = result.scalar_one_or_none()

            if existing_session:
                logger.info(
                    f"Reusing existing session {existing_session.session_id} "
                    f"for user {user.user_id}"
                )
                # Update the session with current information
                existing_session.last_used_at = datetime.now(timezone.utc)
                existing_session.ip_address = ip_address
                await db.commit()
                await db.refresh(existing_session)
                return existing_session

        # Get location information if requested
        location_info = None
        if include_location and ip_address:
            location_info = await LocationService.get_location_from_ip(
                ip_address
            )

        # Generate device name
        device_name = DeviceSessionManager.generate_device_name(device_info)

        # Check if we should create a new session or reuse existing one
        existing_sessions = await SessionManager._get_active_sessions(
            user.user_id, db
        )

        # Clean up old sessions if we're at the limit
        if len(existing_sessions) >= SessionManager.MAX_SESSIONS_PER_USER:
            await SessionManager._cleanup_old_sessions(user.user_id, db)

        # Create new session
        session = AdminUserDeviceSession(
            user_id=user.user_id,
            ip_address=ip_address,
            user_agent=device_info.get("user_agent"),
            device_name=device_name,
            device_fingerprint=fingerprint,
            device_family=device_info.get("device_family"),
            device_brand=device_info.get("device_brand"),
            device_model=device_info.get("device_model"),
            device_type=device_info.get("device_type"),
            browser_family=browser_family,
            browser_version=device_info.get("browser_version"),
            os_family=device_info.get("os_family"),
            os_version=device_info.get("os_version"),
            language=device_info.get("language"),
            is_mobile=device_info.get("is_mobile", False),
            is_tablet=device_info.get("is_tablet", False),
            is_pc=device_info.get("is_pc", False),
            is_bot=device_info.get("is_bot", False),
            logged_in_at=datetime.now(timezone.utc),
            last_used_at=datetime.now(timezone.utc),
            is_active=True,
        )

        # Add location information if available
        if location_info:
            city = location_info.get("city", "")
            country = location_info.get("country", "")
            session.location = f"{city}, {country}"
            session.country = location_info.get("country")
            session.country_code = location_info.get("country_code")
            session.city = location_info.get("city")
            session.latitude = (
                str(location_info.get("latitude"))
                if location_info.get("latitude")
                else None
            )
            session.longitude = (
                str(location_info.get("longitude"))
                if location_info.get("longitude")
                else None
            )
            session.timezone = location_info.get("timezone")
            session.isp = location_info.get("isp")

        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(
            f"Created new session {session.session_id} for user {user.user_id}"
        )

        return session

    @staticmethod
    async def update_session_activity(
        session_id: int,
        db: AsyncSession,
        additional_info: Optional[Dict] = None,
    ) -> bool:
        """
        Update session activity timestamp and Any additional information.

        Args:
            session_id: Session ID to update
            db: Database session
            additional_info: Additional information to update

        Returns:
            bool: True if session was updated successfully
        """
        try:
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.session_id == session_id,
                AdminUserDeviceSession.is_active.is_(True),
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if session:
                session.last_used_at = datetime.now(timezone.utc)

                # Update additional info if provided
                if additional_info:
                    for key, value in additional_info.items():
                        if hasattr(session, key):
                            setattr(session, key, value)

                await db.commit()
                return True

            return False

        except Exception as e:
            logger.error(
                f"Failed to update session activity for session {session_id}: {e}"
            )
            return False

    @staticmethod
    async def terminate_session(
        session_id: int, db: AsyncSession, reason: str = "user_logout"
    ) -> bool:
        """
        Terminate a specific session.

        Args:
            session_id: Session ID to terminate
            db: Database session
            reason: Reason for termination

        Returns:
            bool: True if session was terminated successfully
        """
        try:
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.session_id == session_id
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if session:
                # Only update if the session is active
                if session.is_active:
                    session.is_active = False
                    session.logged_out_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.info(
                        f"Terminated session {session_id} (reason: {reason})"
                    )
                    return True
                else:
                    logger.info(f"Session {session_id} already terminated")
                    return True

            logger.warning(f"Session {session_id} not found")
            return False

        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {e}")
            return False

    @staticmethod
    async def terminate_all_user_sessions(
        user_id: str, db: AsyncSession, except_session_id: Optional[int] = None
    ) -> int:
        """
        Terminate all sessions for a user except optionally one.

        Args:
            user_id: User ID
            db: Database session
            except_session_id: Session ID to keep active

        Returns:
            int: Number of sessions terminated
        """
        try:
            # Get all active sessions for the user
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.user_id == user_id,
                AdminUserDeviceSession.is_active.is_(True),
            )

            if except_session_id:
                stmt = stmt.where(
                    AdminUserDeviceSession.session_id != except_session_id
                )

            result = await db.execute(stmt)
            sessions = list(result.scalars().all())

            terminated_count = 0
            logout_time = datetime.now(timezone.utc)

            for session in sessions:
                session.is_active = False
                session.logged_out_at = logout_time
                terminated_count += 1

            if terminated_count > 0:
                await db.commit()
                logger.info(
                    f"Terminated {terminated_count} sessions for user {user_id}"
                )
            else:
                logger.info(
                    f"No active sessions to terminate for user {user_id}"
                )

            return terminated_count

        except Exception as e:
            logger.error(
                f"Failed to terminate sessions for user {user_id}: {e}"
            )
            return 0

    @staticmethod
    async def get_user_sessions(
        user_id: str,
        db: AsyncSession,
        active_only: bool = True,
        limit: int = 50,
    ) -> List[AdminUserDeviceSession]:
        """
        Get user sessions with optional filtering.

        Args:
            user_id: User ID
            db: Database session
            active_only: Whether to return only active sessions
            limit: Maximum number of sessions to return

        Returns:
            List of AdminUserDeviceSession objects
        """
        try:
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.user_id == user_id
            )

            if active_only:
                stmt = stmt.where(AdminUserDeviceSession.is_active.is_(True))

            stmt = stmt.order_by(
                desc(AdminUserDeviceSession.last_used_at)
            ).limit(limit)

            result = await db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []

    @staticmethod
    async def detect_suspicious_activity(
        user_id: str, current_session: AdminUserDeviceSession, db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Detect suspicious activity patterns.

        Args:
            user_id: User ID
            current_session: Current session
            db: Database session

        Returns:
            List of suspicious activity alerts
        """
        alerts = []

        try:
            # Get recent sessions for comparison
            recent_sessions = await SessionManager._get_recent_sessions(
                user_id, db, hours=24
            )

            # Check for unusual location
            if current_session.country and recent_sessions:
                recent_countries = {
                    s.country for s in recent_sessions if s.country
                }
                if (
                    recent_countries
                    and current_session.country not in recent_countries
                ):
                    alerts.append(
                        {
                            "type": "new_location",
                            "message": f"Login from new country: {current_session.country}",
                            "severity": "medium",
                        }
                    )

            # Check for unusual device
            if current_session.device_fingerprint and recent_sessions:
                recent_fingerprints = {
                    s.device_fingerprint
                    for s in recent_sessions
                    if s.device_fingerprint
                }
                if (
                    recent_fingerprints
                    and current_session.device_fingerprint
                    not in recent_fingerprints
                ):
                    alerts.append(
                        {
                            "type": "new_device",
                            "message": f"Login from new device: {current_session.device_name}",
                            "severity": "low",
                        }
                    )

            # Check for concurrent sessions from different locations
            concurrent_sessions = await SessionManager._get_active_sessions(
                user_id, db
            )
            if len(concurrent_sessions) > 1:
                countries = {
                    s.country for s in concurrent_sessions if s.country
                }
                if len(countries) > 1:
                    alerts.append(
                        {
                            "type": "concurrent_locations",
                            "message": (
                                f"Concurrent sessions from multiple countries: "
                                f"{', '.join(countries)}"
                            ),
                            "severity": "high",
                        }
                    )

        except Exception as e:
            logger.error(
                f"Failed to detect suspicious activity for user {user_id}: {e}"
            )

        return alerts

    @staticmethod
    async def _get_active_sessions(
        user_id: str, db: AsyncSession
    ) -> List[AdminUserDeviceSession]:
        """Get all active sessions for a user"""
        stmt = (
            select(AdminUserDeviceSession)
            .where(
                AdminUserDeviceSession.user_id == user_id,
                AdminUserDeviceSession.is_active.is_(True),
            )
            .order_by(desc(AdminUserDeviceSession.last_used_at))
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _get_recent_sessions(
        user_id: str, db: AsyncSession, hours: int = 24
    ) -> List[AdminUserDeviceSession]:
        """Get recent sessions within specified hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(AdminUserDeviceSession)
            .where(
                AdminUserDeviceSession.user_id == user_id,
                AdminUserDeviceSession.last_used_at >= cutoff_time,
            )
            .order_by(desc(AdminUserDeviceSession.last_used_at))
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _cleanup_old_sessions(user_id: str, db: AsyncSession):
        """Clean up old sessions when limit is reached"""
        # Get all sessions ordered by last use
        stmt = (
            select(AdminUserDeviceSession)
            .where(
                AdminUserDeviceSession.user_id == user_id,
                AdminUserDeviceSession.is_active.is_(True),
            )
            .order_by(desc(AdminUserDeviceSession.last_used_at))
        )

        result = await db.execute(stmt)
        sessions = list(result.scalars().all())

        # Keep only the most recent sessions
        sessions_to_terminate = sessions[
            SessionManager.MAX_SESSIONS_PER_USER - 1 :
        ]

        logout_time = datetime.now(timezone.utc)
        for session in sessions_to_terminate:
            session.is_active = False
            session.logged_out_at = logout_time

        await db.commit()

        logger.info(
            f"Cleaned up {len(sessions_to_terminate)} old sessions for user {user_id}"
        )


class TokenSessionManager:
    """Manage the integration between JWT tokens and device sessions"""

    @staticmethod
    def create_token_with_session(
        user: AdminUser,
        session: AdminUserDeviceSession,
        token_type: str = "access",
    ) -> str:
        """
        Create a JWT token that includes session information.

        Args:
            user: User object
            session: Device session
            token_type: Type of token (access/refresh)

        Returns:
            str: JWT token
        """

        # Prepare token data
        token_data = {
            "uid": user.user_id,
            "rid": user.role_id,
            "sid": session.session_id,
            "token_type": token_type,
            "df": session.device_fingerprint,
        }

        # Set expiration based on token type
        if token_type == "access":
            expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS
        else:  # refresh
            expires_in = settings.REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS

        return create_jwt_token(
            data=token_data,
            private_key=PRIVATE_KEY.get_secret_value(),
            expires_in=expires_in,
        )

    @staticmethod
    async def validate_token_session(
        token_payload: Dict[str, Any], db: AsyncSession
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that the token's session is still valid.

        Args:
            token_payload: Decoded JWT payload
            db: Database session

        Returns:
            Tuple of (is_valid, error_message)
        """
        session_id = token_payload.get("sid")
        user_id = token_payload.get("uid")

        if not session_id or not user_id:
            return True, None  # No session validation needed for older tokens

        try:
            # Check if session exists and is active
            stmt = select(AdminUserDeviceSession).where(
                AdminUserDeviceSession.session_id == session_id,
                AdminUserDeviceSession.user_id == user_id,
                AdminUserDeviceSession.is_active.is_(True),
            )

            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                return False, "Session no longer active"

            # Update last used time
            session.last_used_at = datetime.now(timezone.utc)
            await db.commit()

            return True, None

        except Exception as e:
            logger.error(f"Failed to validate token session: {e}")
            return False, "Session validation failed"
