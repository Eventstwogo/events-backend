from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator

from shared.utils.security_validators import contains_xss
from shared.utils.validators import normalize_whitespace


class AboutUsResponse(BaseModel):
    about_us_id: str = Field(
        ...,
        title="About Us ID",
        description="Unique identifier for the about us record.",
    )
    about_us_data: Optional[Dict] = Field(
        None,
        title="About Us Data",
        description="JSON data containing about us information.",
    )
    about_us_status: bool = Field(
        ...,
        title="About Us Status",
        description="Status of the about us record (active/inactive).",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
        description="Timestamp when the about us record was created.",
    )
    updated_at: Optional[datetime] = Field(
        None,
        title="Updated At",
        description="Timestamp when the about us record was last updated.",
    )

    class Config:
        from_attributes = True


class AboutUsCreateRequest(BaseModel):
    about_us_data: Optional[Dict] = Field(
        None,
        title="About Us Data",
        description="JSON data containing about us information.",
    )

    @field_validator("about_us_data")
    @classmethod
    def validate_about_us_data(cls, v):
        if v is None:
            return v

        # Convert dict values to strings for validation if they exist
        if isinstance(v, dict):
            for key, value in v.items():
                if isinstance(value, str):
                    # normalized_value = normalize_whitespace(value)
                    if contains_xss(value):
                        raise ValueError(
                            f"About us data contains potentially malicious content in field '{key}'."
                        )

        return v


class AboutUsUpdateRequest(BaseModel):
    about_us_data: Optional[Dict] = Field(
        None,
        title="About Us Data",
        description="JSON data containing about us information.",
    )
    about_us_status: Optional[bool] = Field(
        default=False,
        title="About Us Status",
        description="Status of the about us record (active/inactive).",
    )

    @field_validator("about_us_data")
    @classmethod
    def validate_about_us_data(cls, v):
        if v is None:
            return v

        # Convert dict values to strings for validation if they exist
        if isinstance(v, dict):
            for key, value in v.items():
                if isinstance(value, str):
                    # normalized_value = normalize_whitespace(value)
                    if contains_xss(value):
                        raise ValueError(
                            f"About us data contains potentially malicious content in field '{key}'."
                        )

        return v
