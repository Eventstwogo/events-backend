from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from shared.utils.security_validators import validate_strict_input
from shared.utils.validators import (
    is_valid_name,
    normalize_whitespace,
    validate_length_range,
)


class CreatePermission(BaseModel):
    permission_name: str = Field(
        ..., title="Permission Name", description="The name of the permission."
    )

    @field_validator("permission_name", mode="before")
    @classmethod
    def validate_permission_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Permission name is required.")
        value = normalize_whitespace(value)

        if not value:
            raise ValueError("Permission name cannot be empty.")

        if not is_valid_name(value):
            raise ValueError("Permission name must contain only letters, spaces, or hyphens.")

        if not validate_length_range(value, 3, 50):
            raise ValueError("Permission name must be between 3 and 50 characters.")

        validate_strict_input("permission_name", value)

        return value.upper()


class PermissionDetails(BaseModel):
    permission_id: str = Field(
        ...,
        title="Permission ID",
        description="Unique identifier of the permission.",
    )
    permission_name: str = Field(
        ..., title="Permission Name", description="Name of the permission."
    )
    permission_status: bool = Field(
        ...,
        title="Permission Status",
        description="Indicates whether permission is active.",
    )


class PermissionUpdate(BaseModel):
    permission_name: Optional[str] = Field(
        None,
        title="Permission Name",
        description="Updated name of the permission.",
    )

    @field_validator("permission_name", mode="before")
    @classmethod
    def validate_permission_name(cls, value: Any) -> Optional[str]:
        if value is not None:
            value = normalize_whitespace(value)

            if not value:
                raise ValueError("Permission name cannot be empty.")

            if not is_valid_name(value):
                raise ValueError("Permission name must contain only letters, spaces, or hyphens.")

            if not validate_length_range(value, 3, 50):
                raise ValueError("Permission name must be between 3 and 50 characters.")

            validate_strict_input("permission_name", value)

            return value.upper()
        return value
