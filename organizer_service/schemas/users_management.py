from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.db.models.events import EventStatus


class UserTypeEnum(str, Enum):
    """Enum for user types based on role_name"""

    ORGANIZER = "organizer"
    ADMIN = "admin"
    ALL = "all"


class EventInfo(BaseModel):
    """Basic event information for user response"""

    event_id: str
    event_title: str
    event_status: EventStatus
    created_at: datetime


class UserInfo(BaseModel):
    """User information model"""

    user_id: str
    username: str
    email: str
    profile_picture: Optional[str] = None
    role_name: str
    is_verified: int
    is_deleted: bool
    created_at: datetime
    total_events: int = 0
    events: List[EventInfo] = []


class UsersListResponse(BaseModel):
    """Response model for users list"""

    admin_users: List[UserInfo] = []
    organizer_users: List[UserInfo] = []
    total_admin_users: int = 0
    total_organizer_users: int = 0
    total_users: int = 0


# API Response wrapper models
class ApiResponse(BaseModel):
    statusCode: int
    message: str
    timestamp: str
    method: Optional[str] = None
    path: Optional[str] = None


class UsersListApiResponse(ApiResponse):
    data: UsersListResponse
