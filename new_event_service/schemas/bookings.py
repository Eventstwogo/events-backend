import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

# Regex for alphanumeric IDs
ID_REGEX = re.compile(r"^[A-Za-z0-9]+$")  # Only alphanumeric


class SeatCategoryBooking(BaseModel):
    seat_category_ref_id: str = Field(
        ...,
        min_length=6,
        max_length=12,
        description="Seat category reference ID",
    )
    price_per_seat: float = Field(..., gt=0, description="Price per seat (must be greater than 0)")
    num_seats: int = Field(
        ..., gt=0, le=20, description="Number of seats (must be >0, max 20 per booking)"
    )
    # Coupon details
    coupon_id: Optional[str] = Field(None, description="Applied coupon ID (nullable)")
    # Financials
    subtotal: Optional[float] = Field(None, description="Subtotal before discount")
    discount_amount: Optional[float] = Field(0, description="Discount applied")
    total_amount: Optional[float] = Field(None, description="Total after discount")

    # --- Validators ---
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
    def validate_num_seats(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Number of seats must be greater than 0")
        if v > 20:
            raise ValueError("Cannot book more than 20 seats at once")
        return v

    @field_validator("price_per_seat")
    @classmethod
    def validate_price_per_seat(cls, v: float) -> float:
        return round(v, 2)

    # --- Model-level validator to compute totals ---
    @model_validator(mode="after")
    def compute_totals(self):
        subtotal = round(self.price_per_seat * self.num_seats, 2)
        discount = self.discount_amount or 0
        self.subtotal = subtotal
        self.total_amount = round(subtotal - discount, 2)
        return self


class BookingCreateRequest(BaseModel):
    user_ref_id: str = Field(
        ..., min_length=6, max_length=6, description="User ID (exactly 6 characters)"
    )
    event_ref_id: str = Field(
        ..., min_length=6, max_length=8, description="Event ID (6–8 characters)"
    )
    slot_ref_id: str = Field(
        ..., min_length=6, max_length=20, description="Slot ID (6–20 characters)"
    )
    event_date: date = Field(..., description="Event date in YYYY-MM-DD format")
    seatCategories: List[SeatCategoryBooking] = Field(
        ..., description="List of seat category bookings"
    )
    coupon_status: Optional[bool] = Field(
        False, description="Indicates if a coupon was applied (default is False)"
    )

    # --- Validators ---
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

    # --- Computed field for total booking price ---
    @computed_field
    def total_booking_price(self) -> float:
        """Sum of all seat categories total price"""
        return round(sum(cat.total_amount or 0 for cat in self.seatCategories), 2)


class SeatCategoryItem(BaseModel):
    seat_category_id: str
    label: str
    num_seats: int
    price_per_seat: float
    subtotal: float
    discount_amount: float
    total_amount: float
    coupon_id: Optional[str] = None


class BookingDetailsResponse(BaseModel):
    order_id: str
    user_ref_id: str
    event_ref_id: str
    slot_ref_id: str
    booking_status: str
    payment_status: str
    payment_reference: Optional[str]
    total_amount: float
    total_discount: float
    event_title: str
    event_slug: str
    event_category: str
    event_location: Optional[str]
    event_date: str
    event_time: Optional[str]
    duration: Optional[int]
    booking_date: str
    seat_categories: List[SeatCategoryItem]


class EventStats(BaseModel):
    event_id: str
    event_title: str
    card_image: Optional[str] = None
    total_tickets: int
    total_revenue: float

    class Config:
        from_attributes = True


class OrganizerEventsStatsResponse(BaseModel):
    organizer_id: str
    organizer_name: str
    events: List[EventStats]

    class Config:
        from_attributes = True


class BarcodeResponse(BaseModel):
    """Response model for barcode generation"""

    barcode_image: str = Field(..., description="Base64 encoded barcode image")
    barcode_type: str = Field(..., description="Type of barcode generated (code128, code39, etc.)")
    encoded_value: str = Field(..., description="Value encoded in the barcode")


class BookingBarcodeResponse(BaseModel):
    """Complete response model for booking with barcode"""

    booking_details: BookingDetailsResponse
    payment_details: dict = Field(..., description="Payment information")
    barcode: BarcodeResponse
    booking_info: dict = Field(..., description="Formatted booking information for display")

    class Config:
        json_encoders = {float: lambda x: round(x, 2)}
