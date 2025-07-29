import re
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class PurposeEnum(str, Enum):
    feedback = "Collect feedback"
    roadmap = "Prioritize my roadmap"
    announcements = "Product announcements"
    sales = "Increase Sales"
    awareness = "Brand Awareness"
    reach = "Expand Reach"
    efficiency = "Operational Efficiency"
    other = "Other"


class PaymentPreferenceEnum(str, Enum):
    product_listing = "Payments for Product Listing"
    orders = "Payments for Orders"


class OnboardingRequest(BaseModel):
    profile_ref_id: str = Field(..., min_length=1, max_length=6)
    purpose: list[PurposeEnum]
    payment_preference: list[PaymentPreferenceEnum]
    store_name: str = Field(..., min_length=3, max_length=100)
    store_url: HttpUrl
    location: str = Field(..., min_length=2, max_length=100)
    industry_id: str = Field(
        ..., min_length=6, max_length=6
    )  # must be exactly 6 characters

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v):
        if not v:
            raise ValueError("Purpose cannot be empty")
        return v

    @field_validator("payment_preference")
    @classmethod
    def validate_payment(cls, v):
        if not v:
            raise ValueError("Payment preference cannot be empty")
        return v

    @field_validator("store_name")
    @classmethod
    def validate_store_name(cls, v):
        if not re.match(r"^[a-zA-Z0-9 _\-']+$", v):
            raise ValueError("Store name contains invalid characters")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        if not re.match(r"^[a-zA-Z0-9 ,]+$", v):
            raise ValueError("Location contains invalid characters")
        return v
