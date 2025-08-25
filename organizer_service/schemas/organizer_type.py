import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class OrganizerTypeCreateRequest(BaseModel):
    organizer_type: str = Field(
        ...,
        description="Organizer type name, only letters, spaces, hyphens, slashes, and ampersands allowed",
    )

    @field_validator("organizer_type")
    def validate_organizer_type(cls, value: str) -> str:
        value = re.sub(r"\s+", " ", value.strip())
        if not re.fullmatch(r"[A-Za-z\s\-\/&]+", value):
            raise ValueError(
                "organizer_type can only contain letters, spaces, hyphens, forward slashes, and ampersands"
            )
        return value.upper()


class OrganizerTypeUpdateRequest(BaseModel):
    new_name: str = Field(
        ...,
        description="New name for the organizer type, only letters, spaces, hyphens, slashes and ampersands allowed",
    )

    @field_validator("new_name")
    def validate_new_name(cls, value: str) -> str:
        value = re.sub(r"\s+", " ", value.strip())
        if not re.fullmatch(r"[A-Za-z\s\-\/&]+", value):
            raise ValueError(
                "new_name can only contain letters, spaces, hyphens, forward slashes, and ampersands"
            )
        return value.upper()


class OrganizerTypeResponse(BaseModel):
    type_id: str
    organizer_type: str
    type_status: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateStatusRequest(BaseModel):
    status: bool
