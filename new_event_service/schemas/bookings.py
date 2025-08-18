import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator

ID_REGEX = re.compile(r"^[A-Za-z0-9]+$")  # Only alphanumeric


class SeatCategoryBooking(BaseModel):
    seat_category_ref_id: str = Field(
        ...,
        min_length=6,
        max_length=12,
        description="Seat category reference ID",
    )
    price_per_seat: float = Field(
        ..., gt=0, description="Price per seat (must be greater than 0)"
    )
    num_seats: int = Field(
        ...,
        gt=0,
        le=20,
        description="Number of seats (must be >0, max 20 per booking)",
    )

    @field_validator("seat_category_ref_id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not ID_REGEX.match(v):
            raise ValueError(
                f"{cls.__name__} ID must be alphanumeric with no spaces or special characters"
            )
        return v

    @field_validator("num_seats")
    @classmethod
    def validate_num_seats(cls, v):
        if v <= 0:
            raise ValueError("Number of seats must be greater than 0")
        if v > 20:
            raise ValueError("Cannot book more than 20 seats at once")
        return v

    @field_validator("price_per_seat")
    @classmethod
    def validate_price_per_seat(cls, v):
        return round(v, 2)

    @computed_field
    @property
    def total_price(self) -> float:
        """Total = price_per_seat × num_seats"""
        return round(self.price_per_seat * self.num_seats, 2)


class BookingCreateRequest(BaseModel):
    user_ref_id: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="User ID (exactly 6 characters)",
    )
    event_ref_id: str = Field(
        ..., min_length=6, max_length=8, description="Event ID (6–8 characters)"
    )
    slot_ref_id: str = Field(
        ...,
        min_length=6,
        max_length=20,
        description="Slot ID (6–20 characters)",
    )
    event_date: date = Field(..., description="Event date in YYYY-MM-DD format")
    seatCategories: List[SeatCategoryBooking] = Field(
        ..., description="List of seat category bookings"
    )

    @field_validator("user_ref_id", "event_ref_id", "slot_ref_id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not ID_REGEX.match(v):
            raise ValueError(
                f"{cls.__name__} ID must be alphanumeric with no spaces or special characters"
            )
        return v

    @field_validator("event_date", mode="before")
    @classmethod
    def validate_booking_date(cls, v):
        if isinstance(v, date):
            return v
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Booking date must be in YYYY-MM-DD format")

    @computed_field
    @property
    def total_booking_price(self) -> float:
        """Sum of all seat categories total price"""
        return round(sum(cat.total_price for cat in self.seatCategories), 2)


class SeatCategoryItem(BaseModel):
    seat_category_id: str
    label: str
    num_seats: int
    price_per_seat: float
    total_price: float


class BookingDetailsResponse(BaseModel):
    order_id: str
    user_ref_id: str
    event_ref_id: str
    slot_ref_id: str
    booking_status: str
    payment_status: str
    payment_reference: Optional[str]
    total_amount: float
    event_title: str
    event_slug: str
    event_category: str
    event_location: Optional[str]
    event_date: str
    event_time: Optional[str]
    duration: Optional[int]
    booking_date: str
    seat_categories: List[SeatCategoryItem]
