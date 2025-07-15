from fastapi import Form, HTTPException, status
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)

from shared.utils.email_validators import EmailValidator
from shared.utils.password_validator import PasswordValidator
from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    normalize_whitespace,
)

class UserPasswordReset(BaseModel):
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Registered email address for password reset.",
    )
    new_password: str = Field(
        ...,
        title="New Password",
        description="New password for the user. Must be strong.",
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


class UserChangePassword(BaseModel):
    current_password: str = Field(
        ...,
        title="Current Password",
        description="Current password for verification.",
    )
    new_password: str = Field(
        ...,
        title="New Password",
        description="New password for the user. Must be strong.",
        min_length=8,
    )

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Current password cannot be empty.")
        if contains_xss(v):
            raise ValueError("Password contains potentially malicious content.")
        return v

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
        current_password: str = Form(
            ...,
            description="Current password for verification.",
        ),
        new_password: str = Form(
            ...,
            description="New password for the user. Must be strong.",
            min_length=8,
        ),
    ) -> "UserChangePassword":
        try:
            return cls(
                current_password=current_password, new_password=new_password
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input: {str(e)}",
            ) from e


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
    token: str = Field(
        ...,
        title="Reset Token",
        description="Password reset token received via email.",
    )
    new_password: str = Field(
        ...,
        title="New Password",
        description="New password for the user. Must be strong.",
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

    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Reset token cannot be empty.")
        if contains_xss(v):
            raise ValueError("Token contains potentially malicious content.")
        return v

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
        token: str = Form(
            ..., description="Password reset token received via email."
        ),
        new_password: str = Form(
            ..., description="New password for the user. Must be strong."
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

            return cls(email=email, token=token, new_password=new_password)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email format: {str(e)}",
            ) from e
