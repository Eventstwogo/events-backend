from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from shared.utils.security_validators import contains_xss
from shared.utils.validators import validate_length_range


class EventSlotCreateRequest(BaseModel):
    """
    Schema for creating a new event slot

    Example usage:
    {
        "slot_id": "ABC123",
        "slot_data": {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "duration": 120,
                    "capacity": 50,
                    "price": 25.00,
                },
                "slot_2": {
                    "start_time": "14:00",
                    "end_time": "16:00",
                    "duration": 120,
                    "capacity": 30,
                    "price": 30.00,
                }
            },
            "2024-01-16": {
                "slot_1": {
                    "start_time": "09:00",
                    "end_time": "11:00",
                    "duration": 120,
                    "capacity": 40,
                    "price": 28.00,
                }
            }
        }
    }
    """

    slot_id: str = Field(
        ...,
        min_length=6,
        max_length=8,
        description="Slot ID that references the event's slot_id",
    )
    slot_data: Dict[str, Any] = Field(
        ...,
        description="JSON data with date as key and slots as nested objects. Format: {'2024-01-15': {'slot_1': {'start_time': '10:00', 'end_time': '12:00', 'duration': 120, 'capacity': 50, 'price': 25.00}, 'slot_2': {...}}}",
    )

    @field_validator("slot_id")
    @classmethod
    def validate_slot_id(cls, v: str) -> str:
        """Validate slot ID format and security"""
        if not v or not v.strip():
            raise ValueError("Slot ID cannot be empty")

        v = v.strip()

        # Security checks
        if contains_xss(v):
            raise ValueError("Slot ID contains potentially malicious content")

        # Length validation (6-8 characters to match Event.slot_id)
        if not validate_length_range(v, 6, 8):
            raise ValueError("Slot ID must be between 6 and 8 characters")

        return v

    @field_validator("slot_data")
    @classmethod
    def validate_slot_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate slot_data dictionary for security and structure"""
        if not isinstance(v, dict):
            raise ValueError("slot_data must be a dictionary")

        if not v:
            raise ValueError("slot_data cannot be empty")

        # Validate each date and its slots
        validated_data = {}
        for date_key, date_slots in v.items():
            # Validate date keys (should be date strings)
            if not isinstance(date_key, str):
                raise ValueError(
                    f"slot_data keys must be strings (dates), got {type(date_key)}"
                )

            if contains_xss(date_key):
                raise ValueError(
                    f"slot_data key '{date_key}' contains potentially malicious content"
                )

            # Validate date format (basic check)
            if len(date_key) > 20:
                raise ValueError(
                    f"slot_data date key '{date_key}' is too long (max 20 characters)"
                )

            # Validate that date_slots is a dictionary
            if not isinstance(date_slots, dict):
                raise ValueError(
                    f"slot_data value for date '{date_key}' must be a dictionary containing slots"
                )

            if not date_slots:
                raise ValueError(
                    f"slot_data for date '{date_key}' cannot be empty"
                )

            # Validate slots for this date
            validated_date_slots = cls._validate_date_slots(
                date_key, date_slots
            )
            validated_data[date_key] = validated_date_slots

        return validated_data

    @staticmethod
    def _validate_date_slots(
        date_key: str, date_slots: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate all slots for a specific date"""
        validated_date_slots = {}

        # Check maximum number of slots per date (up to 10)
        if len(date_slots) > 10:
            raise ValueError(
                f"Too many slots for date '{date_key}' (max 10 slots per date)"
            )

        # Validate each slot
        for slot_key, slot_details in date_slots.items():
            # Validate slot key format (should be slot_1, slot_2, etc.)
            if not isinstance(slot_key, str):
                raise ValueError(
                    f"Slot keys must be strings for date '{date_key}', got {type(slot_key)}"
                )

            if contains_xss(slot_key):
                raise ValueError(
                    f"Slot key '{slot_key}' for date '{date_key}' contains potentially malicious content"
                )

            # Validate slot key format (slot_1, slot_2, etc.)
            if not slot_key.startswith("slot_"):
                raise ValueError(
                    f"Slot key '{slot_key}' for date '{date_key}' must start with 'slot_' (e.g., slot_1, slot_2)"
                )

            try:
                slot_number = int(slot_key.split("_")[1])
                if slot_number < 1 or slot_number > 10:
                    raise ValueError(
                        f"Slot key '{slot_key}' for date '{date_key}' must be between slot_1 and slot_10"
                    )
            except (IndexError, ValueError):
                raise ValueError(
                    f"Invalid slot key format '{slot_key}' for date '{date_key}'. Use format: slot_1, slot_2, etc."
                )

            # Validate slot details
            if not isinstance(slot_details, dict):
                raise ValueError(
                    f"Slot details for '{slot_key}' on date '{date_key}' must be a dictionary"
                )

            validated_slot = EventSlotCreateRequest._validate_slot_details(
                date_key, slot_key, slot_details
            )
            validated_date_slots[slot_key] = validated_slot

        return validated_date_slots

    @staticmethod
    def _validate_slot_details(
        date_key: str, slot_key: str, slot_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate slot details for a specific slot"""
        validated_slot = {}

        for field_name, field_value in slot_details.items():
            # Security check for field names
            if contains_xss(field_name):
                raise ValueError(
                    f"Slot detail field name '{field_name}' for '{slot_key}' on date '{date_key}' contains potentially malicious content"
                )

            if len(field_name) > 50:
                raise ValueError(
                    f"Slot detail field name '{field_name}' for '{slot_key}' on date '{date_key}' is too long (max 50 characters)"
                )

            # Validate field values based on type
            if isinstance(field_value, str):
                if contains_xss(field_value):
                    raise ValueError(
                        f"Slot detail '{field_name}' for '{slot_key}' on date '{date_key}' contains potentially malicious content"
                    )
                if len(field_value) > 1000:
                    raise ValueError(
                        f"Slot detail '{field_name}' for '{slot_key}' on date '{date_key}' is too long (max 1000 characters)"
                    )
                validated_slot[field_name] = field_value.strip()

            elif isinstance(field_value, (int, float)):
                # Validate essential numeric fields
                if field_name in ["capacity"] and field_value < 0:
                    raise ValueError(
                        f"Slot detail '{field_name}' for '{slot_key}' on date '{date_key}' cannot be negative"
                    )
                if field_name in ["price"] and field_value < 0:
                    raise ValueError(
                        f"Slot detail '{field_name}' for '{slot_key}' on date '{date_key}' cannot be negative"
                    )
                if field_name in ["duration"] and field_value <= 0:
                    raise ValueError(
                        f"Slot detail '{field_name}' for '{slot_key}' on date '{date_key}' must be positive"
                    )
                validated_slot[field_name] = field_value

            else:
                # Allow other types (bool, list, dict, etc.)
                validated_slot[field_name] = field_value

        # Limit total number of fields per slot
        if len(validated_slot) > 20:
            raise ValueError(
                f"Too many slot detail fields for '{slot_key}' on date '{date_key}' (max 20 fields)"
            )

        return validated_slot


class EventSlotResponse(BaseModel):
    """Schema for event slot response"""

    id: int = Field(..., description="Auto-generated slot ID")
    slot_id: str = Field(..., description="Event slot ID reference")
    slot_data: Dict[str, Any] = Field(
        ..., description="Slot data with nested slots per date"
    )
    slot_status: bool = Field(..., description="Slot status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class EventSlotCreateResponse(BaseModel):
    """Schema for successful slot creation response"""

    slot: EventSlotResponse = Field(..., description="Created slot details")
    message: str = Field(default="Event slot created successfully")
