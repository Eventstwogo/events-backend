from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from shared.db.models.enquiry import EnquiryStatus
from shared.utils.email_validators import EmailValidator
from shared.utils.phone_validators import PhoneValidator
from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    has_excessive_repetition,
    is_valid_name,
    normalize_whitespace,
    validate_length_range,
)


class EnquiryResponse(BaseModel):
    enquiry_id: int = Field(
        ...,
        title="Enquiry ID",
        description="Unique identifier for the enquiry.",
    )
    firstname: str = Field(
        ...,
        title="First Name",
        description="First name of the person making the enquiry.",
    )
    lastname: str = Field(
        ...,
        title="Last Name",
        description="Last name of the person making the enquiry.",
    )
    email: str = Field(
        ...,
        title="Email Address",
        description="Email address of the person making the enquiry.",
    )
    phone_number: Optional[str] = Field(
        None,
        title="Phone Number",
        description="Phone number of the person making the enquiry.",
    )
    message: str = Field(
        ...,
        title="Message",
        description="The enquiry message content.",
    )
    enquiry_status: EnquiryStatus = Field(
        ...,
        title="Enquiry Status",
        description="Current status of the enquiry.",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
        description="Timestamp when the enquiry was created.",
    )
    updated_at: datetime = Field(
        ...,
        title="Updated At",
        description="Timestamp when the enquiry was last updated.",
    )

    class Config:
        from_attributes = True


class EnquiryCreateRequest(BaseModel):
    firstname: str = Field(
        ...,
        title="First Name",
        description="First name of the person making the enquiry.",
        min_length=1,
        max_length=100,
    )
    lastname: str = Field(
        ...,
        title="Last Name",
        description="Last name of the person making the enquiry.",
        min_length=1,
        max_length=100,
    )
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Email address of the person making the enquiry.",
    )
    phone_number: Optional[str] = Field(
        None,
        title="Phone Number",
        description="Phone number of the person making the enquiry.",
        max_length=20,
    )
    message: str = Field(
        ...,
        title="Message",
        description="The enquiry message content.",
        min_length=1,
    )

    @field_validator("firstname")
    @classmethod
    def validate_firstname(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("First name cannot be empty.")
        if not validate_length_range(v, 1, 100):
            raise ValueError("First name must be 1-100 characters long.")
        if not is_valid_name(v):
            raise ValueError(
                "First name must contain only letters, spaces, and hyphens."
            )
        if contains_xss(v):
            raise ValueError(
                "First name contains potentially malicious content."
            )
        if has_excessive_repetition(v, max_repeats=3):
            raise ValueError(
                "First name contains excessive repeated characters."
            )
        return v

    @field_validator("lastname")
    @classmethod
    def validate_lastname(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Last name cannot be empty.")
        if not validate_length_range(v, 1, 100):
            raise ValueError("Last name must be 1-100 characters long.")
        if not is_valid_name(v):
            raise ValueError(
                "Last name must contain only letters, spaces, and hyphens."
            )
        if contains_xss(v):
            raise ValueError(
                "Last name contains potentially malicious content."
            )
        if has_excessive_repetition(v, max_repeats=3):
            raise ValueError(
                "Last name contains excessive repeated characters."
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        try:
            # Use EmailValidator to validate and format the email
            validated_email = EmailValidator.validate(str(v))
            return validated_email
        except Exception as e:
            # Convert HTTPException to ValueError for Pydantic
            raise ValueError(f"Invalid email: {str(e)}")

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if v is None:
            return v
        v = normalize_whitespace(v)
        if not v:  # If empty string after normalization, return None
            return None
        try:
            # Use PhoneValidator to validate and format the phone number
            validated_phone = PhoneValidator.validate(v)
            return validated_phone
        except Exception as e:
            # Convert HTTPException to ValueError for Pydantic
            raise ValueError(f"Invalid phone number: {str(e)}")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Message cannot be empty.")
        # if contains_xss(v):
        #     raise ValueError("Message contains potentially malicious content.")
        # if has_excessive_repetition(v, max_repeats=5):
        #     raise ValueError("Message contains excessive repeated characters.")
        return v


class EnquiryUpdateRequest(BaseModel):
    enquiry_status: Optional[EnquiryStatus] = Field(
        None,
        title="Enquiry Status",
        description="New status for the enquiry.",
    )

    @field_validator("enquiry_status")
    @classmethod
    def validate_enquiry_status(cls, v):
        if v is not None and v not in EnquiryStatus:
            raise ValueError("Invalid enquiry status.")
        return v
