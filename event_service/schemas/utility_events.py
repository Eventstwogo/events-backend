from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.db.models import EventStatus


class HealthCheckResponse(BaseModel):
    """Schema for health check response"""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    database: str = Field(..., description="Database status")
    uptime: str = Field(..., description="Service uptime")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EventExistsResponse(BaseModel):
    """Schema for event existence check response"""

    event_id: str = Field(..., description="Event ID")
    exists: bool = Field(..., description="Whether event exists")
    event_status: EventStatus = Field(
        default=EventStatus.INACTIVE,  # Use a valid enum member as default
        description="The status of the event.",
    )
    event_title: Optional[str] = Field(
        None, description="Event title if exists"
    )


class SlotCountResponse(BaseModel):
    """Schema for slot count response"""

    event_id: str = Field(..., description="Event ID")
    total_slots: int = Field(
        ..., description="Total number of EventSlot records"
    )
    active_slots: int = Field(
        ..., description="Number of active EventSlot records"
    )
    inactive_slots: int = Field(
        ..., description="Number of inactive EventSlot records"
    )
    total_dates: int = Field(
        ..., description="Total number of dates across all slots"
    )
    total_individual_slots: int = Field(
        ..., description="Total individual time slots across all dates"
    )
    total_capacity: int = Field(
        ..., description="Total capacity across all individual slots"
    )
    total_revenue_potential: float = Field(
        ..., description="Total potential revenue"
    )
    average_capacity_per_slot: float = Field(
        ..., description="Average capacity per individual slot"
    )
    average_price_per_slot: float = Field(
        ..., description="Average price per individual slot"
    )


class EventMetricsResponse(BaseModel):
    """Schema for overall event metrics"""

    # Event counts
    total_events: int = Field(..., description="Total number of events")
    published_events: int = Field(..., description="Number of published events")
    draft_events: int = Field(..., description="Number of draft events")

    # Slot metrics
    total_slots: int = Field(
        ..., description="Total number of EventSlot records across all events"
    )
    active_slots: int = Field(
        ..., description="Total number of active EventSlot records"
    )
    inactive_slots: int = Field(
        ..., description="Total number of inactive EventSlot records"
    )
    total_individual_slots: int = Field(
        ..., description="Total individual time slots across all events"
    )
    total_capacity: int = Field(
        ..., description="Total capacity across all individual slots"
    )
    total_revenue_potential: float = Field(
        ..., description="Total potential revenue across all slots"
    )

    # Category distribution
    events_by_category: Dict[str, int] = Field(
        ..., description="Event count by category"
    )
    events_by_subcategory: Dict[str, int] = Field(
        ..., description="Event count by subcategory"
    )

    # Organizer metrics
    total_organizers: int = Field(
        ..., description="Total number of unique organizers"
    )
    top_organizers: List[Dict[str, Any]] = Field(
        ..., description="Top organizers by event count"
    )

    # Time-based metrics
    events_created_today: int = Field(..., description="Events created today")
    events_created_this_week: int = Field(
        ..., description="Events created this week"
    )
    events_created_this_month: int = Field(
        ..., description="Events created this month"
    )

    # Engagement metrics
    events_with_hashtags: int = Field(..., description="Events with hashtags")
    events_with_images: int = Field(
        ..., description="Events with card or banner images"
    )
    events_with_extra_data: int = Field(
        ..., description="Events with extra data"
    )

    # Timestamp
    generated_at: datetime = Field(
        ..., description="Metrics generation timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
