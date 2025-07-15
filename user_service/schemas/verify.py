from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from shared.utils.validators import normalize_whitespace


class RequestEmailVerificationRequest(BaseModel):
    """Request to send email verification link"""

    email: EmailStr = Field(
        ..., description="Email address to send verification link to"
    )


class EmailVerificationRequest(BaseModel):
    """Request to verify email with token"""

    email: str = Field(..., min_length=1, description="email")
    token: str = Field(
        ..., min_length=6, description="Email verification token"
    )


class ResendEmailTokenRequest(BaseModel):
    """Request to resend email verification token"""

    email: EmailStr = Field(
        ..., description="Email address to resend verification link to"
    )


# Phone verification schemas
class UpdatePhoneNumberRequest(BaseModel):
    """Request to update phone number and send OTP"""

    user_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The ID of the user to update phone number for",
    )
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Phone number in international format (e.g., +1234567890)",
    )

    @validator("user_id")
    def validate_user_id(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("User ID cannot be empty")
        if len(v) != 6:
            raise ValueError("User ID must be exactly 6 characters long")
        return v

    @validator("phone_number")
    def validate_phone_number(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Phone number cannot be empty")
        # Basic phone number validation (can be enhanced)
        if not v.startswith("+"):
            raise ValueError("Phone number must start with country code (+)")
        if not v[1:].isdigit():
            raise ValueError(
                "Phone number must contain only digits after country code"
            )
        return v


class PhoneVerificationCodeRequest(BaseModel):
    """Request to verify phone with OTP code"""

    user_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The ID of the user to verify",
    )
    verification_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The 6-digit verification code sent to the user's phone",
    )

    @validator("user_id", "verification_code")
    def validate_fields(cls, v, values, **kwargs):
        v = normalize_whitespace(v)
        if not v:
            field_name = kwargs.get("field", "Field")
            raise ValueError(f"{field_name} cannot be empty")
        return v


class ResendPhoneOTPRequest(BaseModel):
    """Request to resend phone OTP"""

    user_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The ID of the user to resend OTP for",
    )

    @validator("user_id")
    def validate_user_id(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("User ID cannot be empty")
        if len(v) != 6:
            raise ValueError("User ID must be exactly 6 characters long")
        return v


class VerificationResponse(BaseModel):
    user_id: str
    verified: bool
    message: str


class EmailVerificationSentResponse(BaseModel):
    """Response when email verification is sent"""

    user_id: str
    email: str
    message: str
    expires_in_minutes: int


class PhoneOTPSentResponse(BaseModel):
    """Response when phone OTP is sent"""

    user_id: str
    phone_number: str
    message: str
    expires_in_minutes: int
