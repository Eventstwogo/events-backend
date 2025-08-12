from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from shared.utils.email_validators import EmailValidator
from shared.utils.username_validators import UsernameValidator
from shared.utils.validators import (
    normalize_whitespace,
    validate_length_range,
)


class AdminRegisterRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=255,
        title="Username",
        description=(
            "Unique username for the admin. Must be 4-32 characters, "
            "and start with 3 letters. Letters, numbers, spaces, and hyphens are allowed."
        ),
    )
    email: EmailStr = Field(
        ...,
        title="Email Address",
        description="Valid email address for the admin.",
    )
    role_id: str = Field(
        ...,
        min_length=1,
        max_length=6,
        title="Role ID",
        description="The role identifier assigned to the admin. Must be exactly 6 characters long.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values):
        if not values.get("username"):
            raise ValueError("Username is required.")
        if not values.get("email"):
            raise ValueError("Email is required.")
        if not values.get("role_id"):
            raise ValueError("Role ID is required.")
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
        # Use your advanced email validator
        EmailValidator.validate(str(v))
        return v.lower()

    @field_validator("role_id")
    @classmethod
    def validate_role_id(cls, v):
        v = normalize_whitespace(v)
        if not v:
            raise ValueError("Role ID cannot be empty.")
        # Ensure role_id is exactly 6 characters long
        if not validate_length_range(v, 6, 6):
            raise ValueError("Role ID must be exactly 6 characters long.")
        return v


class AdminRegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    username: str
