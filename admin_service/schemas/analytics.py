"""
Analytics schemas for admin dashboard.

This module contains Pydantic models for analytics data validation and serialization.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MetricData(BaseModel):
    """Base model for metric data with trend information."""

    total: int = Field(..., description="Total count of the metric")
    percentage_change: float = Field(
        ..., description="Percentage change from previous period"
    )
    trend: Literal["up", "down", "stable"] = Field(
        ..., description="Trend direction"
    )


class CategoriesAnalytics(MetricData):
    """Analytics data for categories."""

    added_this_month: int = Field(
        ..., description="Number of categories added this month"
    )


class UsersAnalytics(MetricData):
    """Analytics data for users."""

    added_this_week: int = Field(
        ..., description="Number of users added this week"
    )


class RevenueAnalytics(BaseModel):
    """Analytics data for revenue."""

    current_month: float = Field(..., description="Current month's revenue")
    last_month: float = Field(..., description="Last month's revenue")
    difference: float = Field(
        ..., description="Revenue difference between months"
    )
    percentage_change: float = Field(
        ..., description="Percentage change from last month"
    )
    trend: Literal["up", "down", "stable"] = Field(
        ..., description="Revenue trend"
    )
    note: Optional[str] = Field(
        None, description="Additional notes about revenue calculation"
    )


class SettingsAnalytics(MetricData):
    """Analytics data for system settings."""

    changes_this_week: int = Field(
        ..., description="Number of configuration changes this week"
    )


class AdminUsersAnalytics(MetricData):
    """Analytics data for admin users."""

    added_this_week: int = Field(
        ..., description="Number of admin users added this week"
    )


class EventsAnalytics(MetricData):
    """Analytics data for events."""

    total_bookings: int = Field(..., description="Total event bookings")
    added_this_month: int = Field(
        ..., description="Number of events added this month"
    )


class OrganizersAnalytics(MetricData):
    """Analytics data for organizers."""

    approved: int = Field(..., description="Number of approved organizers")
    pending: int = Field(..., description="Number of pending organizers")
    registered_this_month: int = Field(
        ..., description="Number of organizers registered this month"
    )


class QueriesAnalytics(MetricData):
    """Analytics data for queries."""

    resolved: int = Field(..., description="Number of resolved queries")
    pending: int = Field(..., description="Number of pending queries")
    created_this_week: int = Field(
        ..., description="Number of queries created this week"
    )


class ContactUsAnalytics(MetricData):
    """Analytics data for contact us submissions."""

    resolved: int = Field(..., description="Number of resolved submissions")
    pending: int = Field(..., description="Number of pending submissions")
    submitted_this_week: int = Field(
        ..., description="Number of submissions this week"
    )


class DashboardAnalytics(BaseModel):
    """Complete dashboard analytics response."""

    categories: CategoriesAnalytics = Field(
        ..., description="Categories analytics data"
    )
    admin_users: AdminUsersAnalytics = Field(
        ..., description="Admin users analytics data"
    )
    users: UsersAnalytics = Field(..., description="Users analytics data")
    events: EventsAnalytics = Field(..., description="Events analytics data")
    organizers: OrganizersAnalytics = Field(
        ..., description="Organizers analytics data"
    )
    revenue: RevenueAnalytics = Field(..., description="Revenue analytics data")
    queries: QueriesAnalytics = Field(..., description="Queries analytics data")
    contact_us: ContactUsAnalytics = Field(
        ..., description="Contact us analytics data"
    )
    settings: SettingsAnalytics = Field(
        ..., description="Settings analytics data"
    )
    generated_at: str = Field(
        ..., description="Timestamp when analytics were generated"
    )


class RecentQuery(BaseModel):
    """Recent query information."""

    id: int = Field(..., description="Query ID")
    title: str = Field(..., description="Query title")
    category: str = Field(..., description="Query category")
    status: str = Field(..., description="Query status")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class RecentQueriesResponse(BaseModel):
    """Response for recent queries endpoint."""

    queries: list[RecentQuery] = Field(
        ..., description="List of recent queries"
    )
    total: int = Field(..., description="Total number of queries returned")


class RecentContact(BaseModel):
    """Recent contact us submission information."""

    id: int = Field(..., description="Contact submission ID")
    name: str = Field(..., description="Contact person name")
    email: str = Field(..., description="Contact email")
    status: str = Field(..., description="Submission status")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class RecentContactsResponse(BaseModel):
    """Response for recent contact us submissions endpoint."""

    contacts: list[RecentContact] = Field(
        ..., description="List of recent contacts"
    )
    total: int = Field(..., description="Total number of contacts returned")


class SystemHealth(BaseModel):
    """System health status information."""

    database: str = Field(..., description="Database connection status")
    api_services: str = Field(..., description="API services status")
    last_backup: str = Field(..., description="Last backup information")
    overall_status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Health check timestamp")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class DailyRegistration(BaseModel):
    """Daily registration data point."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    count: int = Field(..., description="Number of registrations on this date")


class UserAnalyticsSummary(BaseModel):
    """Summary analytics for admin users."""

    total_users: int = Field(..., description="Total number of admin users")
    active_users: int = Field(..., description="Number of active admin users")
    inactive_users: int = Field(
        ..., description="Number of inactive admin users"
    )
    locked_users: int = Field(..., description="Number of locked admin users")
    with_expiry_flag: int = Field(
        ..., description="Users with 180-day expiry flag"
    )
    expired_passwords: int = Field(
        ..., description="Users with expired passwords"
    )
    high_failed_attempts: int = Field(
        ..., description="Users with high failed login attempts"
    )
    earliest_user: datetime = Field(
        ..., description="Creation date of earliest user"
    )
    latest_user: datetime = Field(
        ..., description="Creation date of latest user"
    )


class UserAnalyticsResponse(BaseModel):
    """Complete user analytics response."""

    summary: UserAnalyticsSummary = Field(..., description="Summary statistics")
    daily_registrations: list[DailyRegistration] = Field(
        ..., description="Daily registration data"
    )
