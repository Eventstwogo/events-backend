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


class DashboardAnalytics(BaseModel):
    """Complete dashboard analytics response."""

    categories: CategoriesAnalytics = Field(
        ..., description="Categories analytics data"
    )
    users: UsersAnalytics = Field(..., description="Users analytics data")
    revenue: RevenueAnalytics = Field(..., description="Revenue analytics data")
    settings: SettingsAnalytics = Field(
        ..., description="Settings analytics data"
    )
    generated_at: datetime = Field(
        ..., description="Timestamp when analytics were generated"
    )

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
