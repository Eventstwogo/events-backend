import re
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class PurposeEnum(str, Enum):
    sell_event_tickets = "Sell Event Tickets"
    build_event_community = "Build Event Community"
    promote_brand_events = "Promote Brand Events"
    increase_event_attendance = "Increase Event Attendance"
    manage_event_registrations = "Manage Event Registrations"
    create_recurring_events = "Create Recurring Events"
    corporate_event_planning = "Corporate Event Planning"
    entertainment_events = "Entertainment Events"


class OnboardingRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=6)
    purpose: list[PurposeEnum]
    store_name: str = Field(..., min_length=3, max_length=100)
    store_url: HttpUrl
    location: str = Field(..., min_length=2, max_length=100)
    type_ref_id: str = Field(..., min_length=1, max_length=6)

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v):
        if not v:
            raise ValueError("Purpose cannot be empty")
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
