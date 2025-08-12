from datetime import datetime
from typing import Optional

from fastapi import Form, HTTPException
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)
from starlette import status

from shared.utils.email_validators import EmailValidator
from shared.utils.password_validator import PasswordValidator
from shared.utils.security_validators import contains_xss
from shared.utils.username_validators import UsernameValidator
from shared.utils.validators import (
    normalize_whitespace,
    validate_length_range,
)


class AdminUserResponse(BaseModel):
    user_id: str = Field(
        ...,
        title="User ID",
        description="A unique 6-character identifier for the admin user.",
    )
    username: str = Field(
        ..., title="Username", description="The username used for login."
    )
    email: str = Field(
        ...,
        title="Email Address",
        description="The admin user's email address.",
    )
    role_id: str = Field(
        ...,
        title="Role ID",
        description="Identifier linking the user to a specific role.",
    )
    role_name: str = Field(
        ...,
        title="Role Name",
        description="Human-readable name of the assigned role.",
    )
    profile_picture: Optional[str] = Field(
        None,
        title="Profile Picture",
        description="URL or path to the user's profile picture.",
    )
    is_deleted: bool = Field(
        ...,
        title="Active Status",
        description="Indicates if the account is active (True) or inactive (False).",
    )
    last_login: Optional[datetime] = Field(
        None,
        title="Last Login",
        description="The date and time when the user last logged in.",
    )
    created_at: datetime = Field(
        ...,
        title="Created At",
        description="Timestamp when the user account was created.",
    )

    class Config:
        from_attributes = True


class AdminUserUpdateInput(BaseModel):
    new_username: Optional[str] = None
    new_role_id: Optional[str] = None

    @field_validator("new_username")
    @classmethod
    def validate_username(cls, v):
        if v is None:
            return v
        v = UsernameValidator(
            min_length=4, max_length=32, max_spaces=2
        ).validate(v)
        return v

    @field_validator("new_role_id")
    @classmethod
    def validate_role_id(cls, v):
        if v is None:
            return v
        v = normalize_whitespace(v)
        if not validate_length_range(v, 6, 6):
            raise ValueError("Role ID must be exactly 6 characters long.")
        return v


class ForgotPassword(BaseModel):
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Registered email address for password reset request.",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @classmethod
    def as_form(
        cls,
        email: str = Form(
            ...,
            description="Registered email address for password reset request.",
        ),
    ) -> "ForgotPassword":
        try:
            # Validate email format before creating the model
            EmailValidator.validate(email)
            return cls(email=email)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email format: {str(e)}",
            ) from e


class ResetPasswordWithToken(BaseModel):
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Registered email address for password reset.",
    )
    new_password: str = Field(
        ...,
        title="New Password",
        description="New password for the admin user. Must be strong.",
        min_length=8,
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("New password cannot be empty.")
        if contains_xss(v):
            raise ValueError("Password contains potentially malicious content.")
        password_check = PasswordValidator.validate(v)
        if password_check["status_code"] != 200:
            raise ValueError(password_check["message"])
        return v

    @classmethod
    def as_form(
        cls,
        email: str = Form(
            ..., description="Registered email address for password reset."
        ),
        new_password: str = Form(
            ..., description="New password for the admin user. Must be strong."
        ),
    ) -> "ResetPasswordWithToken":
        try:
            # Validate email format before creating the model
            EmailValidator.validate(email)

            # Validate password strength
            password_check = PasswordValidator.validate(new_password)
            if password_check["status_code"] != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=password_check["message"],
                )

            return cls(email=email, new_password=new_password)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email format: {str(e)}",
            ) from e
