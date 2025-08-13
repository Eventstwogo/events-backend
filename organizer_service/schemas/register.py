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
from shared.utils.username_validators import UsernameValidator
from shared.utils.validators import (
    has_excessive_repetition,
    normalize_whitespace,
)


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
        v = UsernameValidator(
            min_length=4, max_length=32, max_spaces=2
        ).validate(v)
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


# Username availability check schemas
class OrganizerUsernameAvailabilityRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        title="Username",
        description="Username to check for availability",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Username cannot be empty.")

        # Process username by removing email and plus parts
        v = v.split("@", 1)[0].split("+", 1)[0]

        v = UsernameValidator(
            min_length=4, max_length=32, max_spaces=2
        ).validate(v)
        return v.lower()


class OrganizerUsernameAvailabilityResponse(BaseModel):
    username: str
    available: bool
    message: str
