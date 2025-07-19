from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    normalize_whitespace,
    validate_length_range,
)


class SlotCreateRequest(BaseModel):
    """Schema for creating a new event slot"""

    slot_order: int = Field(
        ..., ge=0, le=1000, description="Order of the slot (0-1000)"
    )
    slot_data: Dict[str, Any] = Field(..., description="Slot data as JSON")
    slot_status: bool = Field(
        default=False, description="Slot status (active/inactive)"
    )

    @field_validator("slot_data")
    @classmethod
    def validate_slot_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate slot_data dictionary for security and structure"""
        if not isinstance(v, dict):
            raise ValueError("slot_data must be a dictionary")

        if not v:
            raise ValueError("slot_data cannot be empty")

        # Validate each key-value pair in slot_data
        validated_data = {}
        for key, value in v.items():
            # Validate keys
            if not isinstance(key, str):
                raise ValueError(
                    f"slot_data keys must be strings, got {type(key)}"
                )

            if contains_xss(key):
                raise ValueError(
                    f"slot_data key '{key}' contains potentially malicious content"
                )

            if len(key) > 100:
                raise ValueError(
                    f"slot_data key '{key}' is too long (max 100 characters)"
                )

            # Validate values (only allow strings, numbers, booleans, lists, and nested dicts)
            if value is not None:
                validated_value = cls._validate_slot_data_value(key, value)
                validated_data[key] = validated_value

        return validated_data

    @staticmethod
    def _validate_slot_data_value(key: str, value: Any) -> Any:
        """Recursively validate slot_data values"""
        if isinstance(value, str):
            if contains_xss(value):
                raise ValueError(
                    f"slot_data value for key '{key}' contains potentially malicious content"
                )
            if len(value) > 10000:
                raise ValueError(
                    f"slot_data string value for key '{key}' is too long (max 10000 characters)"
                )
            return normalize_whitespace(value)

        elif isinstance(value, (int, float, bool)):
            return value

        elif isinstance(value, list):
            if len(value) > 200:
                raise ValueError(
                    f"slot_data list for key '{key}' is too long (max 200 items)"
                )
            return [
                SlotCreateRequest._validate_slot_data_value(f"{key}[{i}]", item)
                for i, item in enumerate(value)
            ]

        elif isinstance(value, dict):
            if len(value) > 100:
                raise ValueError(
                    f"slot_data nested dict for key '{key}' has too many keys (max 100)"
                )
            return {
                k: SlotCreateRequest._validate_slot_data_value(f"{key}.{k}", v)
                for k, v in value.items()
            }

        else:
            raise ValueError(
                f"slot_data value for key '{key}' has unsupported type: {type(value)}"
            )

    @model_validator(mode="after")
    def validate_model(self) -> "SlotCreateRequest":
        """Final model validation"""
        return self


class SlotUpdateRequest(BaseModel):
    """Schema for updating an event slot"""

    slot_order: Optional[int] = Field(
        None, ge=0, le=1000, description="Order of the slot (0-1000)"
    )
    slot_data: Optional[Dict[str, Any]] = Field(
        None, description="Slot data as JSON"
    )
    slot_status: Optional[bool] = Field(
        None, description="Slot status (active/inactive)"
    )

    @field_validator("slot_data")
    @classmethod
    def validate_slot_data(
        cls, v: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Validate slot_data dictionary for security and structure"""
        if v is None:
            return v

        if not isinstance(v, dict):
            raise ValueError("slot_data must be a dictionary")

        if not v:
            raise ValueError("slot_data cannot be empty if provided")

        # Validate each key-value pair in slot_data
        validated_data = {}
        for key, value in v.items():
            # Validate keys
            if not isinstance(key, str):
                raise ValueError(
                    f"slot_data keys must be strings, got {type(key)}"
                )

            if contains_xss(key):
                raise ValueError(
                    f"slot_data key '{key}' contains potentially malicious content"
                )

            if len(key) > 100:
                raise ValueError(
                    f"slot_data key '{key}' is too long (max 100 characters)"
                )

            # Validate values (only allow strings, numbers, booleans, lists, and nested dicts)
            if value is not None:
                validated_value = cls._validate_slot_data_value(key, value)
                validated_data[key] = validated_value

        return validated_data

    @staticmethod
    def _validate_slot_data_value(key: str, value: Any) -> Any:
        """Recursively validate slot_data values"""
        if isinstance(value, str):
            if contains_xss(value):
                raise ValueError(
                    f"slot_data value for key '{key}' contains potentially malicious content"
                )
            if len(value) > 10000:
                raise ValueError(
                    f"slot_data string value for key '{key}' is too long (max 10000 characters)"
                )
            return normalize_whitespace(value)

        elif isinstance(value, (int, float, bool)):
            return value

        elif isinstance(value, list):
            if len(value) > 200:
                raise ValueError(
                    f"slot_data list for key '{key}' is too long (max 200 items)"
                )
            return [
                SlotUpdateRequest._validate_slot_data_value(f"{key}[{i}]", item)
                for i, item in enumerate(value)
            ]

        elif isinstance(value, dict):
            if len(value) > 100:
                raise ValueError(
                    f"slot_data nested dict for key '{key}' has too many keys (max 100)"
                )
            return {
                k: SlotUpdateRequest._validate_slot_data_value(f"{key}.{k}", v)
                for k, v in value.items()
            }

        else:
            raise ValueError(
                f"slot_data value for key '{key}' has unsupported type: {type(value)}"
            )

    @model_validator(mode="after")
    def validate_model(self) -> "SlotUpdateRequest":
        """Final model validation"""
        # Ensure at least one field is being updated
        update_fields = [self.slot_order, self.slot_data, self.slot_status]
        if all(field is None for field in update_fields):
            raise ValueError("At least one field must be provided for update")

        return self


class SlotStatusUpdateRequest(BaseModel):
    """Schema for updating slot status"""

    slot_status: bool = Field(
        ..., description="Slot status (true for active, false for inactive)"
    )


class SlotResponse(BaseModel):
    """Schema for slot response"""

    slot_ids: int = Field(..., description="Slot ID")
    event_id: str = Field(..., description="Event ID")
    slot_order: int = Field(..., description="Order of the slot")
    slot_data: Dict[str, Any] = Field(..., description="Slot data as JSON")
    slot_status: bool = Field(..., description="Slot status (active/inactive)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class SlotSimpleResponse(BaseModel):
    """Schema for simplified slot response without timestamps"""

    slot_ids: int = Field(..., description="Slot ID")
    event_id: str = Field(..., description="Event ID")
    slot_order: int = Field(..., description="Order of the slot")
    slot_data: Dict[str, Any] = Field(..., description="Slot data as JSON")
    slot_status: bool = Field(..., description="Slot status (active/inactive)")

    class Config:
        from_attributes = True


class SlotListResponse(BaseModel):
    """Schema for slot list response"""

    slots: List[SlotResponse] = Field(..., description="List of slots")
    total: int = Field(..., description="Total number of slots")
    event_id: str = Field(..., description="Event ID")


class SlotFilters(BaseModel):
    """Schema for slot filtering parameters"""

    status: Optional[bool] = Field(None, description="Filter by slot status")
    sort_by: Optional[str] = Field(
        default="slot_order", description="Sort field"
    )
    sort_order: Optional[str] = Field(
        default="asc", pattern="^(asc|desc)$", description="Sort order"
    )
