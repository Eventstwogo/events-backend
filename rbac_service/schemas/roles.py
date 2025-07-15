from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from shared.utils.security_validators import validate_strict_input
from shared.utils.validators import (
    is_valid_name,
    normalize_whitespace,
    validate_length_range,
)


class CreateRole(BaseModel):
    role_name: str = Field(..., title="Role Name", description="The name of the role.")

    @field_validator("role_name", mode="before")
    @classmethod
    def validate_role_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Role name is required.")

        value = normalize_whitespace(value)

        if not value:
            raise ValueError("Role name cannot be empty.")

        if not is_valid_name(value):
            raise ValueError("Role name must contain only letters and spaces or hyphens.")

        if not validate_length_range(value, 3, 50):
            raise ValueError("Role name must be between 3 and 50 characters long.")

        validate_strict_input("role_name", value)

        return value.upper()


class RoleDetails(BaseModel):
    role_id: str = Field(..., title="Role ID", description="Unique identifier of the role.")
    role_name: str = Field(..., title="Role Name", description="Name of the role.")
    role_status: Optional[bool] = Field(
        None,
        title="Role Status",
        description="Indicates whether role is active.",
    )


class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(
        None, title="Role Name", description="Updated name of the role."
    )

    @field_validator("role_name", mode="before")
    @classmethod
    def validate_role_name(cls, value: Any) -> Optional[str]:
        if value is not None:
            value = normalize_whitespace(value)

            if not value:
                raise ValueError("Role name cannot be empty.")

            if not is_valid_name(value):
                raise ValueError("Role name must contain only letters, spaces, or hyphens.")

            if not validate_length_range(value, 3, 50):
                raise ValueError("Role name must be between 3 and 50 characters.")

            validate_strict_input("role_name", value)

            return value.upper()
        return value
