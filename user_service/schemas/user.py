from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)

from shared.utils.email_validators import EmailValidator
from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    normalize_whitespace,
)


class UserLogin(BaseModel):
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Registered email address of the user.",
    )
    password: str = Field(
        ..., title="Password", description="Account password."
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Password cannot be empty.")
        if contains_xss(v):
            raise ValueError("Password contains potentially malicious content.")
        return v


class UserOut(BaseModel):
    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the user.",
    )
    username: str = Field(..., title="Username", description="User's username.")
    email: EmailStr = Field(
        ..., title="Email Address", description="User's email address."
    )
    profile_picture: Optional[str] = Field(
        None,
        title="Profile Picture",
        description="URL or filename of the user's profile picture.",
    )
    last_login: Optional[datetime] = Field(
        None,
        title="Last Login",
        description="Timestamp of the user's last login.",
    )
    access_token: Optional[str] = Field(
        None,
        title="Access Token",
        description="JWT access token for authentication.",
    )
    refresh_token: Optional[str] = Field(
        None,
        title="Refresh Token",
        description="JWT refresh token for obtaining new access tokens.",
    )
    token_type: Optional[str] = Field(
        None,
        title="Token Type",
        description="Type of token (usually 'bearer').",
    )
    session_id: Optional[int] = Field(
        None,
        title="Session ID",
        description="ID of the user's current device session.",
    )

    class Config:
        from_attributes = True


class UserMeOut(BaseModel):
    """Schema for /me endpoint - returns only essential user information"""

    user_id: str = Field(
        ...,
        title="User ID",
        description="Unique identifier for the user.",
    )
    username: str = Field(..., title="Username", description="User's username.")
    first_name: Optional[str] = Field(
        None, title="First Name", description="User's first name."
    )
    last_name: Optional[str] = Field(
        None, title="Last Name", description="User's last name."
    )
    email: EmailStr = Field(
        ..., title="Email Address", description="User's email address."
    )
    profile_picture: Optional[str] = Field(
        None,
        title="Profile Picture",
        description="URL or filename of the user's profile picture.",
    )
    is_deleted: Optional[bool] = Field(
        False,
        title="Is Deleted",
        description="Indicates if the account is deleted.",
    )
    days_180_flag: Optional[bool] = Field(
        False,
        title="Days 180 Flag",
        description="Flag indicating if the user has been active within the past 180 days.",
    )
    last_login: Optional[datetime] = Field(
        None,
        title="Last Login",
        description="Timestamp of the user's last login.",
    )
    created_at: datetime = Field(
        ..., title="Created At", description="Timestamp of the user's creation."
    )

    class Config:
        from_attributes = True
