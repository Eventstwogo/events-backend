from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer

from shared.db.models import EventStatus
from shared.utils.file_uploads import get_media_url


class CategoryEventResponse(BaseModel):
    """Schema for limited event response with category/subcategory context"""

    event_id: str = Field(..., description="Event ID")
    slot_id: str = Field(..., description="Slot ID")
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
    event_status: EventStatus = Field(
        default=EventStatus.INACTIVE,  # Use a valid enum member as default
        description="The status of the event.",
    )
    featured_event: bool = Field(..., description="Event is featured or not")

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True


class CategoryWithEventsResponse(BaseModel):
    """Schema for category with its latest events"""

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    category_slug: str = Field(..., description="Category slug")
    events: List[CategoryEventResponse] = Field(
        ..., description="Latest events in this category"
    )
    events_count: int = Field(..., description="Number of events returned")

    class Config:
        from_attributes = True


class SubCategoryWithEventsResponse(BaseModel):
    """Schema for subcategory with its latest events"""

    subcategory_id: str = Field(..., description="Subcategory ID")
    subcategory_name: str = Field(..., description="Subcategory name")
    subcategory_slug: str = Field(..., description="Subcategory slug")
    category_id: str = Field(..., description="Parent category ID")
    category_name: str = Field(..., description="Parent category name")
    category_slug: str = Field(..., description="Parent category slug")
    events: List[CategoryEventResponse] = Field(
        ..., description="Latest events in this subcategory"
    )
    events_count: int = Field(..., description="Number of events returned")

    class Config:
        from_attributes = True


class CategoryEventsResponse(BaseModel):
    """Schema for the complete response with categories and subcategories"""

    categories: List[CategoryWithEventsResponse] = Field(
        ..., description="Categories with their latest events"
    )
    subcategories: List[SubCategoryWithEventsResponse] = Field(
        ..., description="Subcategories with their latest events"
    )
    total_categories: int = Field(..., description="Total number of categories")
    total_subcategories: int = Field(
        ..., description="Total number of subcategories"
    )


class SimplifiedCategoryEventsResponse(BaseModel):
    """Schema for simplified response with only categories (including subcategory events)"""

    categories: List[CategoryWithEventsResponse] = Field(
        ...,
        description="Categories with their latest events (including events from subcategories)",
    )
    total_categories: int = Field(..., description="Total number of categories")


class PaginatedEventResponse(BaseModel):
    """Schema for paginated event response"""

    event_id: str = Field(..., description="Event ID")
    slot_id: str = Field(..., description="Slot ID")
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
    event_status: EventStatus = Field(
        default=EventStatus.INACTIVE,  # Use a valid enum member as default
        description="The status of the event.",
    )
    featured_event: bool = Field(..., description="Event is featured or not")

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True


class CategoryInfoResponse(BaseModel):
    """Schema for category information"""

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    category_slug: str = Field(..., description="Category slug")

    class Config:
        from_attributes = True


class SubCategoryInfoResponse(BaseModel):
    """Schema for subcategory information with parent category"""

    subcategory_id: str = Field(..., description="Subcategory ID")
    subcategory_name: str = Field(..., description="Subcategory name")
    subcategory_slug: str = Field(..., description="Subcategory slug")
    category_id: str = Field(..., description="Parent category ID")
    category_name: str = Field(..., description="Parent category name")
    category_slug: str = Field(..., description="Parent category slug")

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    """Schema for pagination metadata"""

    current_page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class SlugEventsResponse(BaseModel):
    """Schema for events response by category or subcategory slug"""

    events: List[PaginatedEventResponse] = Field(
        ..., description="List of events"
    )
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    category: Optional[CategoryInfoResponse] = Field(
        None, description="Category information if found by category slug"
    )
    subcategory: Optional[SubCategoryInfoResponse] = Field(
        None, description="Subcategory information if found by subcategory slug"
    )
    slug: str = Field(..., description="The slug that was searched")
    slug_type: str = Field(
        ...,
        description="Type of slug found: 'category', 'subcategory', or 'not_found'",
    )


class UnifiedSlugEventsResponse(BaseModel):
    """
    Schema for unified events response by category or
    subcategory slug (always under category context)
    """

    events: List[PaginatedEventResponse] = Field(
        ..., description="List of events"
    )
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    category: CategoryInfoResponse = Field(
        ...,
        description="Category information (parent category if slug was subcategory)",
    )
    slug: str = Field(..., description="The slug that was searched")
    slug_type: str = Field(
        ...,
        description="Type of slug found: 'category' or 'subcategory'",
    )


class SimplifiedSlugEventsResponse(BaseModel):
    """Schema for simplified slug events response matching categories-with-events format"""

    events: List[PaginatedEventResponse] = Field(
        ..., description="List of events"
    )
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    category: CategoryInfoResponse = Field(
        ...,
        description="Category information (parent category if slug was subcategory)",
    )
    total_events: int = Field(..., description="Total number of events")
    slug: str = Field(..., description="The slug that was searched")
    slug_type: str = Field(
        ...,
        description="Type of slug found: 'category' or 'subcategory'",
    )
