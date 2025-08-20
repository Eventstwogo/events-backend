from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from new_event_service.schemas.events import SubCategoryInfo
from shared.utils.file_uploads import get_media_url


class EventMinimalResponse(BaseModel):
    """Schema for minimal event response with only essential fields"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    event_slug: str = Field(..., description="Event slug")
    event_type: Optional[str] = Field(None, description="Event type")
    event_dates: List[date] = Field(..., description="Event dates")
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

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


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


class CategoryEventResponse(BaseModel):
    """Schema for category event response - latest event from each category"""

    event_id: str = Field(..., description="Event ID")
    event_slug: str = Field(..., description="Event slug")
    event_type: Optional[str] = Field(None, description="Event type")
    event_title: str = Field(..., description="Event title")
    card_image: Optional[str] = Field(..., description="Card image URL")
    banner_image: Optional[str] = Field(None, description="Banner image URL")
    description: Optional[str] = Field(
        None, description="Event description from extra_data"
    )

    event_dates: List[date] = Field(..., description="Event dates")
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
