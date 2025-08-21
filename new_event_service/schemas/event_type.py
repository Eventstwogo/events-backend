import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class EventTypeCreateRequest(BaseModel):

    event_type: str = Field(
        ...,
        description="Event type name, only letters, spaces, hyphens, and slashes allowed",
    )

    @field_validator("event_type")
    def validate_event_type(cls, value: str) -> str:
        # Trim leading/trailing whitespaces and replace multiple consecutive spaces with a single space
        value = re.sub(r"\s+", " ", value.strip())

        # Check allowed characters (letters, space, hyphen, forward slash)
        if not re.fullmatch(r"[A-Za-z\s\-\/]+", value):
            raise ValueError(
                "event_type can only contain letters, spaces, hyphens, and forward slashes"
            )

        # Convert to uppercase
        return value.upper()


class EventTypeUpdateRequest(BaseModel):
    new_name: str = Field(
        ...,
        description="New name for the event type, only letters, spaces, hyphens, and slashes allowed",
    )

    @field_validator("new_name")
    def validate_new_name(cls, value: str) -> str:
        # Trim leading/trailing whitespaces and replace multiple consecutive spaces with a single space
        value = re.sub(r"\s+", " ", value.strip())

        # Check allowed characters (letters, space, hyphen, forward slash)
        if not re.fullmatch(r"[A-Za-z\s\-\/]+", value):
            raise ValueError(
                "new_name can only contain letters, spaces, hyphens, and forward slashes"
            )

        # Convert to uppercase
        return value.upper()


class EventTypeResponse(BaseModel):
    id: int
    type_id: str
    event_type: str
    type_status: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateStatusRequest(BaseModel):
    status: bool
