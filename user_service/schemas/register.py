import re
from datetime import datetime
from typing import List, Optional

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

FIRST_LAST_NAME_MIN_LENGTH = 1
FIRST_LAST_NAME_MAX_LENGTH = 100
USERNAME_MIN_LENGTH = 4
USERNAME_MAX_LENGTH = 32
NAME_REGEX = re.compile(r"^[A-Za-z\s\-']+$")


def validate_person_name(value: str, field_name: str) -> str:
    value = normalize_whitespace(value)
    if not value:
        raise ValueError(f"{field_name} cannot be empty.")
    if contains_xss(value):
        raise ValueError(
            f"{field_name} contains potentially malicious content."
        )
    if has_excessive_repetition(value, max_repeats=3):
        raise ValueError(
            f"{field_name} contains excessive repeated characters."
        )
    if not NAME_REGEX.match(value):
        raise ValueError(
            f"{field_name} can only contain letters, spaces, hyphens, and apostrophes."
        )
    if not validate_length_range(
        value, FIRST_LAST_NAME_MIN_LENGTH, FIRST_LAST_NAME_MAX_LENGTH
    ):
        raise ValueError(
            f"{field_name} must be {FIRST_LAST_NAME_MIN_LENGTH}-"
            f"{FIRST_LAST_NAME_MAX_LENGTH} characters long."
        )
    return value


class UserRegisterRequest(BaseModel):
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        title="First Name",
        description=(
            "The first name of the user. Only letters, "
            "spaces, hyphens, and apostrophes are allowed."
        ),
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        title="Last Name",
        description=(
            "The last name of the user. Only letters, spaces, "
            "hyphens, and apostrophes are allowed."
        ),
    )
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

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v):
        return validate_person_name(v, "First name")

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v):
        return validate_person_name(v, "Last name")

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


class AddPhoneNumberRequest(BaseModel):
    email: EmailStr = Field(
        ..., title="Email Address", description="User's email address."
    )
    phone_number: str = Field(
        ...,
        title="Phone Number",
        description="User's phone number in international format (e.g., +1234567890)",
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if v is None:
            return v

        v = normalize_whitespace(v)
        if not v:
            return None

        # Basic phone number validation
        if not v.startswith("+"):
            raise ValueError(
                "Phone number must start with + followed by country code"
            )

        # Remove + and check if the rest are digits
        digits_only = v[1:]
        if not digits_only.isdigit():
            raise ValueError(
                "Phone number must contain only digits after the + sign"
            )

        if len(digits_only) < 7 or len(digits_only) > 15:
            raise ValueError(
                "Phone number must be between 8 and 16 characters long (including + sign)"
            )

        return v


class UserRegisterResponse(BaseModel):
    user_id: str
    email: EmailStr


class User(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    is_deleted: bool = False


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        title="First Name",
        description="Updated first name of the user.",
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        title="Last Name",
        description="Updated last name of the user.",
    )
    email: Optional[EmailStr] = Field(
        None, title="Email Address", description="Updated email address."
    )
    profile_picture: Optional[str] = Field(
        None,
        title="Profile Picture",
        description="URL to the user's profile picture.",
    )

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v):
        return validate_person_name(v, "First name") if v else v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v):
        return validate_person_name(v, "Last name") if v else v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not v:
            return v
        v = normalize_whitespace(v)
        EmailValidator.validate(str(v))
        return v.lower()


class ListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    users: List[User]


# Password change schema
class PasswordChangeRequest(BaseModel):
    current_password: str = Field(
        ...,
        title="Current Password",
        description="User's current password for verification.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=14,
        title="New Password",
        description="New password that meets security requirements.",
    )

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Current password cannot be empty.")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("New password cannot be empty.")

        # Use the password validator
        validation_result = PasswordValidator.validate(v)
        if validation_result["status_code"] != status.HTTP_200_OK:
            raise ValueError(validation_result["message"])

        return v


# Phone number update schema
class PhoneNumberUpdate(BaseModel):
    phone_number: str = Field(
        ...,
        min_length=8,
        max_length=20,
        title="Phone Number",
        description="User's phone number in international format (e.g., +1234567890)",
    )

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Phone number cannot be empty")

        # Basic phone number validation - should start with + and contain only digits
        if not v.startswith("+"):
            raise ValueError(
                "Phone number must start with + followed by country code"
            )

        # Remove + and check if the rest are digits
        digits_only = v[1:]
        if not digits_only.isdigit():
            raise ValueError(
                "Phone number must contain only digits after the + sign"
            )

        if len(digits_only) < 7 or len(digits_only) > 15:
            raise ValueError(
                "Phone number must be between 8 and 16 characters long (including + sign)"
            )

        return v


# Response model for phone number update (OTP sent)
class PhoneNumberUpdateResponse(BaseModel):
    user_id: str
    phone_number: str
    message: str = "OTP sent successfully. Please verify your OTP."


# Schema for OTP verification
class PhoneOTPVerificationRequest(BaseModel):
    user_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        title="User ID",
        description="The ID of the user to verify",
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        title="OTP Code",
        description="The 6-digit OTP code sent to the phone number",
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("User ID cannot be empty")
        if len(v) != 6:
            raise ValueError("User ID must be exactly 6 characters long")
        return v

    @field_validator("otp_code")
    @classmethod
    def validate_otp_code(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("OTP code cannot be empty")
        if not v.isdigit():
            raise ValueError("OTP code must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP code must be exactly 6 digits long")
        return v


# Response model for OTP verification
class PhoneOTPVerificationResponse(BaseModel):
    user_id: str
    phone_number: str
    verified: bool
    message: str
