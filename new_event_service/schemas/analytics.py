from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.db.models.events import EventStatus


class RoleInfo(BaseModel):
    role_id: str
    role_name: str


class OrganizerInfo(BaseModel):
    user_id: str
    username: str
    email: str
    profile_picture: Optional[str] = None
    role: Optional[RoleInfo] = None
    is_verified: int
    is_deleted: bool


class UserProfile(BaseModel):
    profile_id: str
    full_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    social_links: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    profile_bio: Optional[str] = None


class BusinessProfile(BaseModel):
    business_id: str
    abn_id: str
    profile_details: Optional[Dict[str, Any]] = None
    business_logo: Optional[str] = None
    store_name: Optional[str] = None
    store_url: Optional[str] = None
    location: Optional[str] = None
    ref_number: str
    purpose: Optional[List[str]] = None
    is_approved: int
    timestamp: datetime
    error: Optional[str] = None


class CategoryInfo(BaseModel):
    category_id: str
    category_name: str


class SubCategoryInfo(BaseModel):
    subcategory_id: str
    subcategory_name: str


class SeatCategory(BaseModel):
    seat_category_id: str
    category_label: str
    price: float
    total_tickets: int
    booked: int
    held: int
    seat_category_status: bool


class NewEventSlot(BaseModel):
    slot_id: str
    slot_date: date
    start_time: str
    duration_minutes: int
    slot_status: bool
    seat_categories: List[SeatCategory] = []


class NewEventDetails(BaseModel):
    event_id: str
    event_slug: str
    event_title: str
    category: Optional[CategoryInfo] = None
    subcategory: Optional[SubCategoryInfo] = None
    event_dates: List[date] = []
    location: Optional[str] = None
    is_online: bool
    card_image: Optional[str] = None
    banner_image: Optional[str] = None
    event_extra_images: Optional[List[str]] = None
    extra_data: Optional[Dict[str, Any]] = None
    hash_tags: Optional[List[str]] = None
    event_status: EventStatus = EventStatus.INACTIVE
    featured_event: bool
    created_at: datetime
    updated_at: datetime
    slots: List[NewEventSlot] = []
    total_slots: int


class EventsSummary(BaseModel):
    total_events: int
    active_events: int
    inactive_events: int


class NewEventFullDetailsResponse(BaseModel):
    organizer_info: OrganizerInfo
    user_profile: Optional[UserProfile] = None
    business_profile: Optional[BusinessProfile] = None
    events_summary: EventsSummary
    events: List[NewEventDetails] = []


class BusinessProfileStatus(BaseModel):
    has_business_profile: bool
    is_approved: int
    business_id: Optional[str] = None
    store_name: Optional[str] = None


class EventsStatistics(BaseModel):
    total_events: int
    active_events: int
    inactive_events: int


class ProfileCompletion(BaseModel):
    has_user_profile: bool
    has_business_profile: bool
    business_approved: bool
    completion_percentage: int = Field(..., ge=0, le=100)


class OrganizerSummaryInfo(BaseModel):
    user_id: str
    username: str
    email: str
    profile_picture: Optional[str] = None
    role_name: Optional[str] = None
    is_verified: int
    created_at: datetime


class NewEventSummaryResponse(BaseModel):
    organizer_info: OrganizerSummaryInfo
    business_profile_status: BusinessProfileStatus
    events_statistics: EventsStatistics
    profile_completion: ProfileCompletion


# API Response wrapper models
class ApiResponse(BaseModel):
    statusCode: int
    message: str
    timestamp: str
    method: Optional[str] = None
    path: Optional[str] = None


class NewEventFullDetailsApiResponse(ApiResponse):
    data: NewEventFullDetailsResponse


class NewEventSummaryApiResponse(ApiResponse):
    data: NewEventSummaryResponse