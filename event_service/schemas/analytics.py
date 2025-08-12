from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CategoryAnalytics(BaseModel):
    """Schema for category-wise analytics"""

    total: int = Field(..., description="Total events in category")
    active: int = Field(..., description="Active events in category")
    draft: int = Field(..., description="Draft events in category")


class EventsAnalytics(BaseModel):
    """Schema for events analytics"""

    total_events: int = Field(..., description="Total number of events")
    active_events: int = Field(..., description="Number of active events")
    draft_events: int = Field(..., description="Number of draft events")
    upcoming_events: int = Field(..., description="Number of upcoming events")
    past_events: int = Field(..., description="Number of past events")
    events_by_category: Dict[str, CategoryAnalytics] = Field(
        default_factory=dict, description="Events grouped by category"
    )
    events_by_month: Optional[Dict[str, int]] = Field(
        default_factory=dict,
        description="Events grouped by month (YYYY-MM format)",
    )


class SlotsAnalytics(BaseModel):
    """Schema for slots analytics"""

    total_slots: int = Field(..., description="Total number of slots")
    active_slots: int = Field(..., description="Number of active slots")
    draft_slots: int = Field(..., description="Number of draft slots")


class TopOrganizer(BaseModel):
    """Schema for top organizer information"""

    organizer_id: str = Field(..., description="Organizer ID")
    event_count: int = Field(..., description="Number of events created")


class OrganizerStatistics(BaseModel):
    """Schema for organizer statistics"""

    total_organizers: int = Field(..., description="Total number of organizers")
    top_organizers: List[TopOrganizer] = Field(
        default_factory=list, description="Top organizers by event count"
    )


class UserStatistics(BaseModel):
    """Schema for user statistics"""

    users_by_role: Dict[str, int] = Field(
        default_factory=dict, description="Number of users by role"
    )
    top_organizers: List[TopOrganizer] = Field(
        default_factory=list, description="Top organizers by event count"
    )
    top_admins: List[TopOrganizer] = Field(
        default_factory=list, description="Top admins by event count"
    )


class AnalyticsSection(BaseModel):
    """Schema for analytics section (used in responses)"""

    events_analytics: EventsAnalytics = Field(
        ..., description="Events analytics"
    )
    slots_analytics: SlotsAnalytics = Field(..., description="Slots analytics")


class OrganizerAnalyticsResponse(BaseModel):
    """Schema for organizer analytics response"""

    events_analytics: EventsAnalytics = Field(
        ..., description="Events analytics"
    )
    slots_analytics: SlotsAnalytics = Field(..., description="Slots analytics")
    organizer_statistics: OrganizerStatistics = Field(
        ..., description="Organizer statistics"
    )


class AdminAnalyticsResponse(BaseModel):
    """Schema for admin analytics response"""

    overall_analytics: AnalyticsSection = Field(
        ..., description="Overall system analytics"
    )
    organizer_created_analytics: AnalyticsSection = Field(
        ..., description="Analytics for organizer-created events"
    )
    admin_created_analytics: AnalyticsSection = Field(
        ..., description="Analytics for admin-created events"
    )
    user_statistics: UserStatistics = Field(..., description="User statistics")


class EventStatsResponse(BaseModel):
    """Schema for simple event statistics response"""

    active_events_count: int = Field(..., description="Number of active events")
    upcoming_events_count: int = Field(
        ..., description="Number of upcoming events"
    )
    monthly_growth_percentage: float = Field(
        ...,
        description="Percentage change in events created this month vs last month",
    )
    current_month_events: int = Field(
        ..., description="Number of events created in current month"
    )
    previous_month_events: int = Field(
        ..., description="Number of events created in previous month"
    )


class BookingAnalytics(BaseModel):
    """Schema for booking analytics"""

    total_bookings: int = Field(..., description="Total number of seats booked")
    total_revenue: float = Field(..., description="Sum of all booking prices")
    approved_bookings: int = Field(
        ..., description="Count of bookings with status 'approved'"
    )
    average_booking_value: float = Field(
        ..., description="Average price per booking"
    )


class BookingAnalyticsResponse(BaseModel):
    """Schema for booking analytics response"""

    booking_analytics: BookingAnalytics = Field(
        ..., description="Booking analytics data"
    )


class EventBookingStats(BaseModel):
    """Schema for event-specific booking statistics"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    total_seats_booked: int = Field(
        ..., description="Total seats booked for event"
    )
    total_revenue: float = Field(..., description="Total revenue from event")


class TimeRangeBookingStats(BaseModel):
    """Schema for time range booking statistics"""

    daily: List[EventBookingStats] = Field(
        default_factory=list, description="Daily booking statistics"
    )
    weekly: List[EventBookingStats] = Field(
        default_factory=list, description="Weekly booking statistics"
    )
    monthly: List[EventBookingStats] = Field(
        default_factory=list, description="Monthly booking statistics"
    )
    yearly: List[EventBookingStats] = Field(
        default_factory=list, description="Yearly booking statistics"
    )
    all_time: List[EventBookingStats] = Field(
        default_factory=list, description="All-time booking statistics"
    )


class EventBookingStatsResponse(BaseModel):
    """Schema for event booking statistics response"""

    event_booking_stats: TimeRangeBookingStats = Field(
        ..., description="Event booking statistics by time range"
    )
