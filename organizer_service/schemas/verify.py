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
