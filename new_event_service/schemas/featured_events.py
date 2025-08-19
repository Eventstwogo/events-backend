from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer

from shared.utils.file_uploads import get_media_url


class FeaturedEventUpdateRequest(BaseModel):
    """Request model for updating featured event status"""

    featured_event: bool = Field(..., description="Featured event status")


class OldFeaturedEventResponse(BaseModel):
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


class OldFeaturedEventListResponse(BaseModel):
    """Response model for list of featured events"""

    success: bool = Field(True, description="Success status")
    message: str = Field(
        "Featured events retrieved successfully", description="Response message"
    )
    data: List[OldFeaturedEventResponse] = Field(
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


class FeaturedEventBase(BaseModel):
    user_ref_id: str
    event_ref_id: str
    start_date: date
    end_date: date
    total_weeks: int
    price: float


class FeaturedEventCreate(FeaturedEventBase):
    """Request schema for creating a Featured Event"""

    pass


class FeaturedEventResponse(BaseModel):
    """Response schema for Featured Event"""

    id: int
    feature_id: str
    start_date: date
    end_date: date
    total_weeks: int
    price: float
    feature_status: bool

    # Optional enriched fields
    event_ref_id: Optional[str] = None  # keep if you want to show FK
    user_ref_id: Optional[str] = None
    event_slug: Optional[str] = None
    event_title: Optional[str] = None
    organizer_name: Optional[str] = None
    card_image: Optional[str] = None

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True
