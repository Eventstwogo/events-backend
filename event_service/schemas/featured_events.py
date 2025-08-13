from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer

from shared.utils.file_uploads import get_media_url


class FeaturedEventUpdateRequest(BaseModel):
    """Request model for updating featured event status"""

    featured_event: bool = Field(..., description="Featured event status")


class FeaturedEventResponse(BaseModel):
    """Response model for featured event data"""

    event_id: str = Field(..., description="Event ID")
    slot_id: str = Field(..., description="Slot ID")
    event_title: str = Field(..., description="Event title")
    card_image: Optional[str] = Field(None, description="Card image URL")
    event_slug: str = Field(..., description="Event slug")
    category_title: str = Field(..., description="Category title")
    sub_category_title: Optional[str] = Field(
        None, description="Sub category title"
    )
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    featured_event: bool = Field(..., description="Featured event status")
    is_online: bool = Field(..., description="Is online event")

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)


class FeaturedEventListResponse(BaseModel):
    """Response model for list of featured events"""

    success: bool = Field(True, description="Success status")
    message: str = Field(
        "Featured events retrieved successfully", description="Response message"
    )
    data: List[FeaturedEventResponse] = Field(
        ..., description="List of featured events"
    )
    total: int = Field(..., description="Total number of featured events")


class FeaturedEventUpdateResponse(BaseModel):
    """Response model for featured event update"""

    success: bool = Field(True, description="Success status")
    message: str = Field(
        "Event featured status updated successfully",
        description="Response message",
    )
    data: dict = Field(..., description="Updated event data")
