from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class EventSlot(BaseModel):
    id: int
    slot_id: str
    slot_data: Dict[str, Any]
    slot_status: bool
    created_at: datetime
    updated_at: datetime


class EventDetails(BaseModel):
    event_id: str
    event_slug: str
    event_title: str
    category: Optional[CategoryInfo] = None
    subcategory: Optional[SubCategoryInfo] = None
    start_date: date
    end_date: date
    location: Optional[str] = None
    is_online: bool
    card_image: Optional[str] = None
    banner_image: Optional[str] = None
    event_extra_images: Optional[List[str]] = None
    extra_data: Optional[Dict[str, Any]] = None
    hash_tags: Optional[List[str]] = None
    event_status: bool
    slot_id: str
    created_at: datetime
    updated_at: datetime
    slots: List[EventSlot] = []
    total_slots: int


class EventsSummary(BaseModel):
    total_events: int
    active_events: int
    inactive_events: int


class OrganizerFullDetailsResponse(BaseModel):
    organizer_info: OrganizerInfo
    user_profile: Optional[UserProfile] = None
    business_profile: Optional[BusinessProfile] = None
    events_summary: EventsSummary
    events: List[EventDetails] = []


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


class OrganizerSummaryResponse(BaseModel):
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


class OrganizerFullDetailsApiResponse(ApiResponse):
    data: OrganizerFullDetailsResponse


class OrganizerSummaryApiResponse(ApiResponse):
    data: OrganizerSummaryResponse


# New Dashboard Analytics Schema Models


class EventStatistics(BaseModel):
    total_events: int
    active_events: int
    upcoming_events: int
    past_events: int


class BookingStatistics(BaseModel):
    total_bookings: int
    approved_bookings: int
    pending_bookings: int
    cancelled_bookings: int
    approval_rate: float


class RevenueStatistics(BaseModel):
    total_revenue: float
    pending_revenue: float
    average_booking_value: float


class QueryStatistics(BaseModel):
    total_queries: int
    pending_queries: int
    resolved_queries: int
    resolution_rate: float


class RecentEvent(BaseModel):
    event_id: str
    event_title: str
    category_name: Optional[str] = None
    start_date: date
    event_status: bool
    created_at: datetime
    card_image: Optional[str] = None


class DateRange(BaseModel):
    start_date: date
    end_date: date


class DashboardOverview(BaseModel):
    period: str
    date_range: DateRange
    event_statistics: EventStatistics
    booking_statistics: BookingStatistics
    revenue_statistics: RevenueStatistics
    query_statistics: QueryStatistics
    recent_events: List[RecentEvent]


class EventPerformance(BaseModel):
    event_id: str
    event_title: str
    category_name: str
    start_date: date
    end_date: date
    total_bookings: int
    total_revenue: float
    event_status: bool
    is_online: bool
    card_image: Optional[str] = None


class CategoryStats(BaseModel):
    category_name: str
    event_count: int
    total_bookings: int
    total_revenue: float


class BookingTrend(BaseModel):
    date: date
    bookings: int
    revenue: float


class SuccessMetrics(BaseModel):
    total_events: int
    events_with_bookings: int
    success_rate: float
    average_bookings_per_event: float


class EventAnalytics(BaseModel):
    period: str
    date_range: DateRange
    event_performance: List[EventPerformance]
    popular_categories: List[CategoryStats]
    booking_trends: List[BookingTrend]
    success_metrics: SuccessMetrics


class BookingSummary(BaseModel):
    total_bookings: int
    total_revenue: float
    pending_revenue: float
    average_booking_value: float
    conversion_rate: float


class StatusDistribution(BaseModel):
    approved: int
    pending: int
    cancelled: int
    failed: int


class TopCustomer(BaseModel):
    user_id: str
    total_bookings: int
    total_spent: float
    last_booking: date


class RecentBooking(BaseModel):
    booking_id: int
    event_title: str
    user_id: str
    num_seats: int
    total_price: float
    booking_status: str
    booking_date: date
    created_at: datetime


class BookingAnalytics(BaseModel):
    period: str
    date_range: DateRange
    booking_summary: BookingSummary
    status_distribution: StatusDistribution
    booking_trends: List[BookingTrend]
    top_customers: List[TopCustomer]
    recent_bookings: List[RecentBooking]


class QuerySummary(BaseModel):
    total_queries: int
    resolution_rate: float
    average_resolution_time_hours: float
    pending_queries: int


class QueryTrend(BaseModel):
    date: date
    queries: int


class RecentQuery(BaseModel):
    query_id: str
    subject: str
    status: str
    priority: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class QueryAnalytics(BaseModel):
    period: str
    date_range: DateRange
    query_summary: QuerySummary
    status_distribution: Dict[str, int]
    query_trends: List[QueryTrend]
    recent_queries: List[RecentQuery]


class PeriodMetrics(BaseModel):
    month: str
    events: int
    bookings: int
    revenue: float


class GrowthRates(BaseModel):
    events_growth: float
    bookings_growth: float
    revenue_growth: float


class OverallStatistics(BaseModel):
    total_events: int
    total_bookings: int
    total_revenue: float


class KeyPerformanceIndicators(BaseModel):
    average_bookings_per_event: float
    average_revenue_per_event: float
    average_revenue_per_booking: float


class PerformanceMetrics(BaseModel):
    current_period: PeriodMetrics
    previous_period: PeriodMetrics
    growth_rates: GrowthRates
    overall_statistics: OverallStatistics
    key_performance_indicators: KeyPerformanceIndicators


# API Response wrapper models for new endpoints
class DashboardOverviewApiResponse(ApiResponse):
    data: DashboardOverview


class EventAnalyticsApiResponse(ApiResponse):
    data: EventAnalytics


class BookingAnalyticsApiResponse(ApiResponse):
    data: BookingAnalytics


class QueryAnalyticsApiResponse(ApiResponse):
    data: QueryAnalytics


class PerformanceMetricsApiResponse(ApiResponse):
    data: PerformanceMetrics
