import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from shared.db.models import EventStatus
from shared.utils.security_validators import contains_xss
from shared.utils.validators import validate_length_range

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
                    "id": "platinum",
                    "label": "Platinum",
                    "price": 150,
                    "totalTickets": 50,
                    "booked": 0,
                    "held": 0
                },
                {
                    "id": "diamond",
                    "label": "Diamond",
                    "price": 120,
                    "totalTickets": 10050,
                    "booked": 0,
                    "held": 0
                },
                {
                    "id": "gold",
                    "label": "Gold",
                    "price": 80,
                    "totalTickets": 20050,
                    "booked": 0,
                    "held": 0
                },
                {
                    "id": "silver",
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
    id: str
    label: str
    price: float
    totalTickets: int
    booked: Optional[int] = 0
    held: Optional[int] = 0

    @field_validator("booked", "held", mode="before")
    @classmethod
    def default_booked_held(cls, v):
        if v is None:
            return 0
        return v


class EventSlot(BaseModel):
    time: str
    duration: str
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
                "duration must be a string like '1 hour', '20 minutes', or '1 hour 20 minutes'"
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
    id: Optional[str]
    label: Optional[str]
    price: Optional[float]
    totalTickets: Optional[int]
    booked: Optional[int] = 0
    held: Optional[int] = 0

    @field_validator("booked", "held", mode="before")
    @classmethod
    def default_booked_held(cls, v):
        if v is None:
            return 0
        return v


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
    seat_category_id: str
    label: str
    price: float
    totalTickets: int
    booked: int = 0
    held: int = 0


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


# class EventSlotResponse(BaseModel):
#     """Schema for event slot response"""

#     id: int = Field(..., description="Auto-generated slot ID")
#     slot_id: str = Field(..., description="Event slot ID reference")
#     slot_data: Dict[str, Any] = Field(
#         ..., description="Slot data with nested slots per date"
#     )
#     slot_status: bool = Field(..., description="Slot status")
#     created_at: datetime = Field(..., description="Creation timestamp")
#     updated_at: datetime = Field(..., description="Last update timestamp")

#     class Config:
#         from_attributes = True


# class EventSlotCreateResponse(BaseModel):
#     """Schema for successful slot creation response"""

#     slot: EventSlotResponse = Field(..., description="Created slot details")
#     message: str = Field(default="Event slot created successfully")


# class EventSlotListRequest(BaseModel):
#     """Schema for slot list request with pagination and filtering"""

#     page: int = Field(default=1, ge=1, description="Page number (1-based)")
#     limit: int = Field(
#         default=10, ge=1, le=100, description="Number of items per page"
#     )
#     status: Optional[bool] = Field(
#         default=None, description="Filter by slot status (active/inactive)"
#     )
#     event_id: Optional[str] = Field(
#         default=None, description="Filter by event ID"
#     )


# class EventSlotListResponse(BaseModel):
#     """Schema for slot list response with pagination"""

#     slots: list[EventSlotResponse] = Field(..., description="List of slots")
#     pagination: dict = Field(..., description="Pagination information")
#     total_count: int = Field(..., description="Total number of slots")


# class SlotStatisticsResponse(BaseModel):
#     """Schema for slot statistics response"""

#     total_slots: int = Field(..., description="Total number of slots")
#     active_slots: int = Field(..., description="Number of active slots")
#     inactive_slots: int = Field(..., description="Number of inactive slots")
#     total_dates: int = Field(
#         ..., description="Total number of dates across all slots"
#     )
#     total_individual_slots: int = Field(
#         ..., description="Total number of individual time slots"
#     )
#     total_capacity: int = Field(
#         ..., description="Total capacity across all slots"
#     )
#     total_revenue_potential: float = Field(
#         ..., description="Total potential revenue"
#     )
#     average_capacity_per_slot: float = Field(
#         ..., description="Average capacity per individual slot"
#     )
#     average_price_per_slot: float = Field(
#         ..., description="Average price per slot"
#     )


# class SlotAvailabilityResponse(BaseModel):
#     """Schema for slot availability response"""

#     available: bool = Field(..., description="Whether the slot is available")
#     reason: Optional[str] = Field(
#         default=None, description="Reason if not available"
#     )
#     slot_status: Optional[bool] = Field(
#         default=None, description="Current slot status"
#     )
#     total_dates: Optional[int] = Field(
#         default=None, description="Total number of dates"
#     )
#     total_capacity: Optional[int] = Field(
#         default=None, description="Total capacity"
#     )
#     total_individual_slots: Optional[int] = Field(
#         default=None, description="Total individual slots"
#     )
#     dates_info: Optional[Dict[str, Any]] = Field(
#         default=None, description="Detailed date information"
#     )


# class SlotAnalyticsResponse(BaseModel):
#     """Schema for detailed slot analytics response"""

#     slot_id: str = Field(..., description="Slot ID")
#     slot_status: bool = Field(..., description="Slot status")
#     created_at: datetime = Field(..., description="Creation timestamp")
#     updated_at: datetime = Field(..., description="Last update timestamp")
#     dates_analysis: Dict[str, Any] = Field(..., description="Analysis by date")
#     summary: Dict[str, Any] = Field(..., description="Summary statistics")


# class SlotStatusToggleResponse(BaseModel):
#     """Schema for slot status toggle response"""

#     slot: EventSlotResponse = Field(..., description="Updated slot details")
#     message: str = Field(..., description="Success message")
#     previous_status: bool = Field(
#         ..., description="Previous status before toggle"
#     )


# class SlotDateDetailsResponse(BaseModel):
#     """Schema for slot date details response"""

#     slot_id: str = Field(..., description="Event slot ID")
#     event_date: str = Field(..., description="Date in YYYY-MM-DD format")
#     event_title: str = Field(..., description="Event title")
#     event_id: str = Field(..., description="Event ID")
#     slots_count: int = Field(..., description="Number of slots for this date")
#     slots_data: Dict[str, Any] = Field(
#         ..., description="Detailed slot data for the date"
#     )
#     event_status: EventStatus = Field(
#         default=EventStatus.INACTIVE,  # Use a valid enum member as default
#         description="The status of the event.",
#     )
#     slot_status: bool = Field(..., description="Slot status")
#     total_capacity: int = Field(
#         ..., description="Total capacity for all slots on this date"
#     )
#     total_revenue_potential: float = Field(
#         ..., description="Total potential revenue for this date"
#     )
#     event_location: Optional[str] = Field(None, description="Event location")
#     is_online: bool = Field(..., description="Whether the event is online")
#     start_date: date = Field(..., description="Event start date")
#     end_date: date = Field(..., description="Event end date")

#     class Config:
#         from_attributes = True
