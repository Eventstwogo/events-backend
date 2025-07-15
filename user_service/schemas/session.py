"""
Session schemas for authentication and session management
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DeviceSessionResponse(BaseModel):
    """Basic session information response"""

    session_id: int
    ip_address: Optional[str] = None
    device_name: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    logged_in_at: datetime
    last_used_at: Optional[datetime] = None
    logged_out_at: Optional[datetime] = None
    is_current: bool = Field(
        default=False,
        description="Indicates if this is the current active session",
    )


class SessionInfo(BaseModel):
    """Enhanced schema for session information"""

    session_id: int = Field(..., description="Unique session identifier")
    device_name: str = Field(..., description="Name of the device")
    browser: str = Field(..., description="Browser information")
    os: str = Field(..., description="Operating system information")
    location: str = Field(..., description="Location information")
    ip_address: str = Field(..., description="IP address")
    is_active: bool = Field(..., description="Whether the session is active")
    logged_in_at: Optional[str] = Field(
        None, description="When the session was created"
    )
    last_used_at: Optional[str] = Field(
        None, description="When the session was last used"
    )
    logged_out_at: Optional[str] = Field(
        None, description="When the session was terminated"
    )
    is_current: bool = Field(
        False, description="Whether this is the current session"
    )


class SessionListResponse(BaseModel):
    """Schema for list of sessions response"""

    sessions: List[SessionInfo] = Field(..., description="List of sessions")


class SessionTerminateResponse(BaseModel):
    """Schema for session termination response"""

    terminated_count: int = Field(
        ..., description="Number of sessions terminated"
    )
