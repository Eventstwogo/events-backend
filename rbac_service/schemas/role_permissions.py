from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from shared.utils.security_validators import validate_strict_input
from shared.utils.validators import (
    is_valid_name,
    normalize_whitespace,
    validate_length_range,
)


class CreateRolePermission(BaseModel):
    role_id: str = Field(..., title="Role ID", description="ID of the role.")
    permission_id: str = Field(
        ...,
        title="Permission ID",
        description="ID of the permission to be assigned.",
    )


class RolePermissionDetails(BaseModel):
    id: int = Field(
        ...,
        title="Record ID",
        description="Unique identifier for the role-permission mapping.",
    )
    role_id: str = Field(..., title="Role ID", description="ID of the role.")
    permission_id: str = Field(
        ..., title="Permission ID", description="ID of the permission."
    )


class RolePermissionUpdate(BaseModel):
    role_id: str = Field(..., title="Role ID", description="Updated role ID.")
    permission_id: str = Field(
        ..., title="Permission ID", description="Updated permission ID."
    )
