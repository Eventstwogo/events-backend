from fastapi import status
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from shared.utils.email_validators import EmailValidator
from shared.utils.password_validator import PasswordValidator
from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    has_excessive_repetition,
    is_valid_username,
    normalize_whitespace,
    validate_length_range,
)

USERNAME_MIN_LENGTH = 4
USERNAME_MAX_LENGTH = 32


class OrganizerRegisterRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=4,
        max_length=32,
        title="Username",
        description=(
            "Unique username for the user. Must be 4-32 characters,"
            " and start with 3 letters. Letters, numbers, spaces, "
            "and hyphens are allowed."
        ),
    )
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Valid email address for the user.",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=14,
        title="Password",
        description=(
            "Strong password for the user. Must be 8-14 characters with "
            "at least one uppercase letter, one lowercase letter, "
            "one number, and one special character."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        if not values.get("username"):
            raise ValueError("Username is required.")
        if not values.get("email"):
            raise ValueError("Email is required.")
        if not values.get("password"):
            raise ValueError("Password is required.")
        return values

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")
        if not is_valid_username(v, allow_spaces=True, allow_hyphens=True):
            raise ValueError(
                "Username can only contain letters, numbers, spaces, and hyphens."
            )
        if not validate_length_range(
            v, USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH
        ):
            raise ValueError(
                f"Username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters long."
            )
        if contains_xss(v):
            raise ValueError("Username contains potentially malicious content.")
        if has_excessive_repetition(v, max_repeats=3):
            raise ValueError("Username contains excessive repeated characters.")
        if len(v) < 3 or not all(c.isalpha() for c in v[:3]):
            raise ValueError(
                "First three characters of username must be letters."
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Email cannot be empty.")
        # Use advanced email validator
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
        if has_excessive_repetition(v, max_repeats=3):
            raise ValueError("Password contains excessive repeated characters.")

        # Use the password validator
        validation_result = PasswordValidator.validate(v)
        if validation_result["status_code"] != status.HTTP_200_OK:
            raise ValueError(validation_result["message"])

        return v


class OrganizerRegisterResponse(BaseModel):
    email: EmailStr
