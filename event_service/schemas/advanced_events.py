from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

from event_service.schemas.events import (
    CategoryInfo,
    OrganizerInfo,
    SubCategoryInfo,
)
from event_service.utils.utils import filter_slot_data
from shared.db.models import EventStatus
from shared.utils.file_uploads import get_media_url
from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    normalize_whitespace,
)


def extra_images_media_urls(value: Optional[List[str]]) -> Optional[List[str]]:
    if not value:
        return None
    result = [get_media_url(url) for url in value]
    result = [r for r in result if r is not None]
    return result if result else None


class SlotInfo(BaseModel):
    """Schema for slot information in event response"""

    slot_id: str = Field(..., description="Event slot ID reference")
    slot_data: Optional[Dict[str, Any]] = Field(
        None, description="Slot data with nested slots per date"
    )
    slot_status: bool = Field(..., description="Slot status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_serializer("slot_data")
    def serialize_slot_data(
        self, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Filter out past slot dates from slot_data during serialization"""
        return filter_slot_data(value)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class EventResponse(BaseModel):
    """Schema for event response"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    event_slug: str = Field(..., description="Event slug")
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    location: Optional[str] = Field(
        None, description="Event location (if applicable)"
    )
    is_online: bool = Field(
        ..., description="Whether the event is online or in-person"
    )
    slot_id: str = Field(..., description="Unique slot ID for the event")
    event_status: EventStatus = Field(
        default=EventStatus.INACTIVE,  # Use a valid enum member as default
        description="The status of the event.",
    )
    featured_event: bool = Field(..., description="Event is featured or not")

    # Related entity information
    category: Optional[CategoryInfo] = Field(
        None, description="Category information"
    )
    subcategory: Optional[SubCategoryInfo] = Field(
        None, description="Subcategory information"
    )
    organizer: Optional[OrganizerInfo] = Field(
        None, description="Organizer information"
    )
    slots: Optional[List[SlotInfo]] = Field(
        default_factory=list, description="Event slot information"
    )

    # Event content
    card_image: Optional[str] = Field(None, description="Card image URL")
    banner_image: Optional[str] = Field(None, description="Banner image URL")
    event_extra_images: Optional[List[str]] = Field(
        None, description="List of additional event images"
    )
    extra_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional event data"
    )
    hash_tags: Optional[List[str]] = Field(
        None, description="List of hashtags for the event"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    @field_serializer("banner_image")
    def serialize_banner_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    @field_serializer("event_extra_images")
    def serialize_event_extra_images(
        self, value: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Convert relative paths to full media URLs"""
        if not value:
            return value
        return extra_images_media_urls(value)

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class LimitedEventResponse(BaseModel):
    """Schema for event response"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    event_slug: str = Field(..., description="Event slug")
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    location: Optional[str] = Field(
        None, description="Event location (if applicable)"
    )
    is_online: bool = Field(
        ..., description="Whether the event is online or in-person"
    )
    featured_event: bool = Field(..., description="Event is featured or not")

    # Event content
    card_image: Optional[str] = Field(None, description="Card image URL")

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class EventSimpleResponse(BaseModel):
    """Schema for simplified event response without related entities"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    event_slug: str = Field(..., description="Event slug")
    category_id: str = Field(..., description="Category ID")
    subcategory_id: str = Field(..., description="Subcategory ID")
    organizer_id: str = Field(..., description="Organizer ID")
    card_image: Optional[str] = Field(None, description="Card image URL")
    banner_image: Optional[str] = Field(None, description="Banner image URL")
    event_extra_images: Optional[List[str]] = Field(
        None, description="List of additional event images"
    )
    extra_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional event data"
    )
    hash_tags: Optional[List[str]] = Field(
        None, description="List of hashtags for the event"
    )
    # Status and timestamps - removed as per requirements

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    @field_serializer("banner_image")
    def serialize_banner_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    @field_serializer("event_extra_images")
    def serialize_event_extra_images(
        self, value: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Convert relative paths to full media URLs"""
        if not value:
            return value
        return extra_images_media_urls(value)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class EventListResponse(BaseModel):
    """Schema for paginated event list response"""

    events: List[EventResponse] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class EventMinimalResponse(BaseModel):
    """Schema for minimal event response with only essential fields"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    event_slug: str = Field(..., description="Event slug")
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    location: Optional[str] = Field(
        None, description="Event location (if applicable)"
    )
    is_online: bool = Field(
        ..., description="Whether the event is online or in-person"
    )
    card_image: Optional[str] = Field(None, description="Card image URL")
    featured_event: bool = Field(..., description="Event is featured or not")

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class SubcategoryWithEvents(BaseModel):
    """Schema for subcategory with its events"""

    subcategory: SubCategoryInfo = Field(
        ..., description="Subcategory information"
    )
    events: List[EventMinimalResponse] = Field(
        ..., description="Events in this subcategory"
    )
    event_count: int = Field(
        ..., description="Number of events in this subcategory"
    )


class EventListWithSubcategoriesResponse(BaseModel):
    """Schema for paginated event list response grouped by subcategories"""

    subcategories_with_events: List[SubcategoryWithEvents] = Field(
        ..., description="List of subcategories with their events"
    )
    total_events: int = Field(
        ..., description="Total number of events across all subcategories"
    )
    total_subcategories: int = Field(
        ..., description="Total number of subcategories"
    )
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class SubcategoryEventGroup(BaseModel):
    """Schema for a group of events under a subcategory"""

    subcategory_info: SubCategoryInfo = Field(
        ..., description="Subcategory information"
    )
    events: List[EventMinimalResponse] = Field(
        ..., description="Events in this subcategory"
    )
    total: int = Field(
        ..., description="Total number of events in this subcategory"
    )


class ComprehensiveCategoryEventResponse(BaseModel):
    """Schema for comprehensive category/subcategory event response"""

    slug: str = Field(..., description="The searched slug")
    matched_category_id: Optional[str] = Field(
        None, description="Category ID if slug matched a category"
    )
    matched_subcategory_id: Optional[str] = Field(
        None, description="Subcategory ID if slug matched a subcategory"
    )

    # Category events (events with only category_id, no subcategory_id)
    category_events: Dict[str, Any] = Field(
        ..., description="Category events data"
    )

    # Subcategory events grouped by subcategory
    subcategory_groups: List[SubcategoryEventGroup] = Field(
        default_factory=list, description="Subcategory event groups"
    )

    # Pagination and totals
    total_events: int = Field(..., description="Total events across all groups")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class EventListSimpleResponse(BaseModel):
    """Schema for simple event list response (for subcategory slug)"""

    events: List[EventMinimalResponse] = Field(
        ..., description="List of events"
    )
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class LimitedEventListResponse(BaseModel):
    """Schema for paginated limited event list response"""

    events: List[LimitedEventResponse] = Field(
        ..., description="List of limited events"
    )
    total: int = Field(..., description="Total number of events")


class EventSimpleListResponse(BaseModel):
    """Schema for paginated event list response with simplified event data"""

    events: List[EventSimpleResponse] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class EventFilters(BaseModel):
    """Schema for event filtering parameters"""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(
        default=10, ge=1, le=100, description="Items per page"
    )
    status: Optional[bool] = Field(None, description="Filter by event status")
    category_id: Optional[str] = Field(
        None, description="Filter by category ID"
    )
    subcategory_id: Optional[str] = Field(
        None, description="Filter by subcategory ID"
    )
    organizer_id: Optional[str] = Field(
        None, description="Filter by organizer ID"
    )
    search: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Search in event title"
    )
    sort_by: Optional[str] = Field(
        default="created_at", description="Sort field"
    )
    sort_order: Optional[str] = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort order"
    )

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: Optional[str]) -> Optional[str]:
        """Validate search term for security"""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Search term contains potentially malicious content"
            )

        return normalize_whitespace(v)


class EventSearchRequest(BaseModel):
    """Schema for advanced event search"""

    query: str = Field(
        ..., min_length=1, max_length=200, description="Search query"
    )
    search_fields: Optional[List[str]] = Field(
        default=["title", "slug", "hashtags"],
        description="Fields to search in: title, slug, organizer, hashtags",
    )
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(
        default=10, ge=1, le=100, description="Items per page"
    )
    status: Optional[bool] = Field(None, description="Filter by event status")
    category_id: Optional[str] = Field(
        None, description="Filter by category ID"
    )
    subcategory_id: Optional[str] = Field(
        None, description="Filter by subcategory ID"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query for security"""
        v = v.strip()
        if not v:
            raise ValueError("Search query cannot be empty")

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Search query contains potentially malicious content"
            )

        return normalize_whitespace(v)

    @field_validator("search_fields")
    @classmethod
    def validate_search_fields(cls, v: Optional[List[str]]) -> List[str]:
        """Validate search fields"""
        if v is None:
            return ["title", "slug", "hashtags"]

        allowed_fields = ["title", "slug", "organizer", "hashtags"]
        for field in v:
            if field not in allowed_fields:
                raise ValueError(
                    f"Invalid search field: {field}. Allowed: {allowed_fields}"
                )

        return v


class EventAdvancedFilters(BaseModel):
    """Schema for advanced event filtering"""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(
        default=10, ge=1, le=100, description="Items per page"
    )
    status: Optional[bool] = Field(None, description="Filter by event status")
    category_id: Optional[str] = Field(
        None, description="Filter by category ID"
    )
    subcategory_id: Optional[str] = Field(
        None, description="Filter by subcategory ID"
    )
    organizer_id: Optional[str] = Field(
        None, description="Filter by organizer ID"
    )
    created_after: Optional[datetime] = Field(
        None, description="Filter events created after this date"
    )
    created_before: Optional[datetime] = Field(
        None, description="Filter events created before this date"
    )
    has_slots: Optional[bool] = Field(
        None, description="Filter events that have/don't have slots"
    )
    min_slots: Optional[int] = Field(
        None, ge=0, description="Minimum number of slots"
    )
    max_slots: Optional[int] = Field(
        None, ge=0, description="Maximum number of slots"
    )
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort order"
    )


class EventSlugUpdateRequest(BaseModel):
    """Schema for updating event slug"""

    new_slug: str = Field(
        ..., min_length=1, max_length=100, description="New event slug"
    )

    @field_validator("new_slug")
    @classmethod
    def validate_new_slug(cls, v: str) -> str:
        """Validate new slug for security and format"""
        v = v.strip().lower()
        if not v:
            raise ValueError("New slug cannot be empty")

        # Security checks
        if contains_xss(v):
            raise ValueError("New slug contains potentially malicious content")

        # Basic slug format validation (alphanumeric, hyphens, underscores)
        import re

        if not re.match(r"^[a-z0-9\-_]+$", v):
            raise ValueError(
                "Slug can only contain lowercase letters, numbers, hyphens, and underscores"
            )

        return v


class CategoryEventResponse(BaseModel):
    """Schema for category event response - latest event from each category"""

    event_id: str = Field(..., description="Event ID")
    slot_id: str = Field(..., description="Slot ID associated with the event")
    event_slug: str = Field(..., description="Event slug")
    event_title: str = Field(..., description="Event title")
    card_image: Optional[str] = Field(..., description="Card image URL")
    banner_image: Optional[str] = Field(None, description="Banner image URL")
    description: Optional[str] = Field(
        None, description="Event description from extra_data"
    )

    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    location: Optional[str] = Field(
        None, description="Event location (if applicable)"
    )
    is_online: bool = Field(
        ..., description="Whether the event is online or in-person"
    )
    featured_event: bool = Field(..., description="Event is featured or not")

    @field_serializer("banner_image")
    def serialize_banner_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True


class CategoryEventListResponse(BaseModel):
    """Schema for category events list response"""

    events: List[CategoryEventResponse] = Field(
        ..., description="List of category events"
    )
    total: int = Field(..., description="Total number of events returned")


class EventSummaryResponse(BaseModel):
    """Schema for event summary/analytics"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    # event_status removed as per requirements
    organizer_id: str = Field(..., description="Organizer ID")
    category_id: str = Field(..., description="Category ID")
    subcategory_id: str = Field(..., description="Subcategory ID")

    # Slot statistics
    total_slots: int = Field(..., description="Total number of slots")
    active_slots: int = Field(..., description="Number of active slots")
    inactive_slots: int = Field(..., description="Number of inactive slots")

    # Engagement metrics
    hashtag_count: int = Field(..., description="Number of hashtags")
    has_card_image: bool = Field(
        ..., description="Whether event has card image"
    )
    has_banner_image: bool = Field(
        ..., description="Whether event has banner image"
    )
    has_extra_data: bool = Field(
        ..., description="Whether event has extra data"
    )

    # Timestamps - removed as per requirements

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class EventsByOrganizerResponse(BaseModel):
    """Schema for events by organizer response"""

    organizer_id: str = Field(..., description="Organizer ID")
    organizer_info: Optional[OrganizerInfo] = Field(
        None, description="Organizer information"
    )
    events: List[EventResponse] = Field(..., description="List of events")
    total_events: int = Field(
        ..., description="Total number of events by this organizer"
    )
    active_events: int = Field(..., description="Number of active events")
    inactive_events: int = Field(..., description="Number of inactive events")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
