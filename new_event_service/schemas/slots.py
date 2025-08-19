import re
from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
)

TIME_REGEX = re.compile(r"^(0?[1-9]|1[0-2]):[0-5][0-9] (AM|PM)$", re.IGNORECASE)
DURATION_REGEX = re.compile(r"^(\d+ (hour|hours))?( ?\d+ (minute|minutes))?$")


class ReferenceInput(BaseModel):
    """
    Schema for creating a new event slot

    Example usage:
    {
        "event_ref_id": "ABC123",
        "event_dates": [
            "2025-08-14",
            "2025-08-15",
            "2025-08-19"
        ],
        "slot_data": {
            "2025-08-14": [
            {
                "time": "10:00 AM",
                "duration": "2 hours",
                "seatCategories": [
                {
                    "seat_category_id": "platinum",
                    "label": "Platinum",
                    "price": 150,
                    "totalTickets": 50,
                    "booked": 0,
                    "held": 0
                },
                {
                    "seat_category_id": "diamond",
                    "label": "Diamond",
                    "price": 120,
                    "totalTickets": 10050,
                    "booked": 0,
                    "held": 0
                },
                {
                    "seat_category_id": "gold",
                    "label": "Gold",
                    "price": 80,
                    "totalTickets": 20050,
                    "booked": 0,
                    "held": 0
                },
                {
                    "seat_category_id": "silver",
                    "label": "Silver",
                    "price": 50,
                    "totalTickets": 30050,
                    "booked": 0,
                    "held": 0
                }
                ],
                # "id": "slot-1755151558481-2025-08-14"
            }
            ]
        }
        }
    """


class SeatCategory(BaseModel):
    """Schema for creating seat categories when creating slots"""

    id: Optional[str]
    label: str = Field(..., description="Category name e.g. Platinum, Gold")
    price: float = Field(..., ge=0, description="Ticket price")
    totalTickets: int = Field(
        ..., ge=0, description="Total seats in this category"
    )
    booked: Optional[int] = 0
    held: Optional[int] = 0

    @field_validator("booked", "held", mode="before")
    @classmethod
    def set_default_zero(cls, v):
        return v or 0


class EventSlot(BaseModel):
    """Schema for creating slots"""

    time: str = Field(..., description="Slot start time e.g. 10:00 AM")
    duration: str = Field(
        ..., description="Duration e.g. 2 hours or 1 hour 30 minutes"
    )
    seatCategories: List[SeatCategory]

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not TIME_REGEX.match(v.strip()):
            raise ValueError(
                "time must be in HH:MM AM/PM format, e.g., 10:00 AM"
            )
        return v.strip()

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: str) -> str:
        if not DURATION_REGEX.match(v.strip()):
            raise ValueError(
                "duration must be like '1 hour', '20 minutes', or '1 hour 20 minutes'"
            )
        return v.strip()


class EventSlotCreateRequest(BaseModel):
    event_ref_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Reference ID for the event",
    )
    event_dates: List[date] = Field(
        ..., description="List of dates when the event will take place"
    )
    slot_data: Dict[str, List[EventSlot]] = Field(
        ..., description="Mapping of date string to list of slot entries"
    )

    @field_validator("event_ref_id")
    @classmethod
    def validate_event_ref_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Event Reference ID cannot be empty")
        return v.strip()

    @field_validator("slot_data")
    @classmethod
    def validate_slot_data(
        cls, v: Dict[str, List[EventSlot]]
    ) -> Dict[str, List[EventSlot]]:
        if not isinstance(v, dict) or not v:
            raise ValueError("slot_data must be a non-empty dictionary")
        for date_key, slots in v.items():
            if not isinstance(slots, list) or not slots:
                raise ValueError(
                    f"slot_data for date '{date_key}' must be a non-empty list"
                )
        return v


class SeatCategoryUpdate(BaseModel):
    """Schema for updating seat categories"""

    seat_category_id: Optional[str] = Field(
        None, description="Seat category ID (preferred over label for updates)"
    )
    label: Optional[str]
    price: Optional[float]
    totalTickets: Optional[int]
    booked: Optional[int] = 0
    held: Optional[int] = 0

    @field_validator("booked", "held", mode="before")
    @classmethod
    def set_default_zero(cls, v):
        return v or 0


class EventSlotUpdate(BaseModel):
    time: Optional[str]
    duration: Optional[str]
    seatCategories: Optional[List[SeatCategoryUpdate]]

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not TIME_REGEX.match(v.strip()):
            raise ValueError(
                "time must be in HH:MM AM/PM format, e.g., 10:00 AM"
            )
        return v.strip() if v else v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not DURATION_REGEX.match(v.strip()):
            raise ValueError(
                "duration must be a string like '1 hour', '20 minutes', or '1 hour 20 minutes'"
            )
        return v.strip() if v else v


class EventSlotUpdateRequest(BaseModel):
    event_dates: Optional[List[date]] = Field(
        None, description="List of dates when the event will take place"
    )
    slot_data: Optional[Dict[str, List[EventSlotUpdate]]] = Field(
        None, description="Mapping of date string to list of slot entries"
    )

    @field_validator("slot_data")
    @classmethod
    def validate_slot_data(
        cls, v: Optional[Dict[str, List[EventSlotUpdate]]]
    ) -> Optional[Dict[str, List[EventSlotUpdate]]]:
        if v is None:
            return v
        if not isinstance(v, dict) or not v:
            raise ValueError("slot_data must be a non-empty dictionary")
        for date_key, slots in v.items():
            if not isinstance(slots, list) or not slots:
                raise ValueError(
                    f"slot_data for date '{date_key}' must be a non-empty list"
                )
        return v


class SeatCategoryResponse(BaseModel):
    """Response schema for seat categories"""

    seat_category_id: str
    label: str
    price: float
    totalTickets: int
    booked: int = 0
    held: int = 0

    @computed_field
    @property
    def available(self) -> int:
        """Available seats = total - (booked + held)."""
        return self.totalTickets - (self.booked + self.held)


class EventSlotResponse(BaseModel):
    slot_id: str
    time: str
    duration: str
    seatCategories: List[SeatCategoryResponse]


class EventSlotResponseWrapper(BaseModel):
    event_ref_id: str
    event_dates: List[date]
    slot_data: Dict[str, List[EventSlotResponse]]

    @classmethod
    def from_input(
        cls, event_ref_id: str, slot_data_input: Dict[str, List[dict]]
    ):
        """
        Construct a response object dynamically from the input data.
        Converts date strings to datetime.date objects.
        """
        slot_data_response = {}
        event_dates_parsed: List[date] = []

        for event_date_str, slots in slot_data_input.items():
            # Parse string date to date object
            try:
                event_date_obj = datetime.strptime(
                    event_date_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                raise ValueError(
                    f"Invalid date format for '{event_date_str}', expected YYYY-MM-DD"
                )

            event_dates_parsed.append(event_date_obj)

            slot_list = []
            for slot in slots:
                # Convert seatCategories to response objects
                seat_categories = [
                    SeatCategoryResponse(
                        seat_category_id=s["seat_category_id"],
                        label=s["label"],
                        price=s["price"],
                        totalTickets=s["totalTickets"],
                        booked=s.get("booked", 0),
                        held=s.get("held", 0),
                    )
                    for s in slot.get("seatCategories", [])
                ]

                slot_resp = EventSlotResponse(
                    slot_id=slot["slot_id"],
                    time=slot["time"],
                    duration=slot["duration"],
                    seatCategories=seat_categories,
                )
                slot_list.append(slot_resp)

            slot_data_response[event_date_str] = slot_list

        return cls(
            event_ref_id=event_ref_id,
            event_dates=event_dates_parsed,
            slot_data=slot_data_response,
        )
