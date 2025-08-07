from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from shared.db.models.events import BookingStatus


class BookingCreateRequest(BaseModel):
    """Request schema for creating a new booking"""

    user_id: str = Field(..., min_length=6, max_length=6, description="User ID")
    event_id: str = Field(
        ..., min_length=6, max_length=6, description="Event ID"
    )
    num_seats: int = Field(
        ..., gt=0, le=50, description="Number of seats to book"
    )
    price_per_seat: float = Field(..., ge=0, description="Price per seat")
    total_price: float = Field(
        ..., ge=0, description="Total price for all seats"
    )
    slot: str = Field(
        ..., min_length=1, max_length=100, description="Time slot"
    )
    booking_date: Optional[str] = Field(
        None,
        description="Booking date in YYYY-MM-DD format (defaults to today)",
    )

    @field_validator("num_seats")
    @classmethod
    def validate_num_seats(cls, v):
        if v <= 0:
            raise ValueError("Number of seats must be greater than 0")
        if v > 50:
            raise ValueError("Cannot book more than 50 seats at once")
        return v

    @field_validator("price_per_seat")
    @classmethod
    def validate_price_per_seat(cls, v):
        if v < 0:
            raise ValueError("Price per seat cannot be negative")
        return round(v, 2)

    @field_validator("total_price")
    @classmethod
    def validate_total_price(cls, v):
        if v < 0:
            raise ValueError("Total price cannot be negative")
        return round(v, 2)

    @field_validator("booking_date")
    @classmethod
    def validate_booking_date(cls, v):
        if v is None:
            return None
        try:
            # Parse the date string and return it as string for now
            # Will be converted to date object in the service layer
            parsed_date = datetime.strptime(v, "%Y-%m-%d").date()
            return v
        except ValueError:
            raise ValueError("Booking date must be in YYYY-MM-DD format")

    @model_validator(mode="after")
    def validate_total_price_calculation(self):
        """Validate that total_price matches num_seats * price_per_seat"""
        expected_total = round(self.num_seats * self.price_per_seat, 2)
        if (
            abs(self.total_price - expected_total) > 0.01
        ):  # Allow for small floating point differences
            raise ValueError(
                f"Total price ({self.total_price}) does not match calculated price "
                f"({expected_total}) based on {self.num_seats} seats at {self.price_per_seat} per seat"
            )
        return self


class BookingStatusUpdateRequest(BaseModel):
    """Request schema for updating booking status"""

    booking_status: Literal["failed", "processing", "approved", "cancelled"] = (
        Field(..., description="New booking status")
    )

    def get_booking_status_enum(self) -> BookingStatus:
        """Convert string status to BookingStatus enum"""
        status_map = {
            "failed": BookingStatus.FAILED,
            "processing": BookingStatus.PROCESSING,
            "approved": BookingStatus.APPROVED,
            "cancelled": BookingStatus.CANCELLED,
        }
        return status_map[self.booking_status]


class BookingResponse(BaseModel):
    """Response schema for booking details"""

    booking_id: int
    user_id: str
    event_id: str
    num_seats: int
    price_per_seat: float
    total_price: float
    slot: str
    booking_date: date
    booking_status: BookingStatus
    created_at: datetime
    updated_at: datetime

    # User details
    user_email: Optional[str] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None

    # Event details
    event_title: Optional[str] = None
    event_slug: Optional[str] = None
    event_location: Optional[str] = None
    event_start_date: Optional[date] = None
    event_end_date: Optional[date] = None

    @field_serializer("booking_status")
    def serialize_booking_status(self, value: BookingStatus) -> str:
        """Serialize BookingStatus enum to string"""
        return str(value)

    class Config:
        from_attributes = True


class BookingWithEventResponse(BaseModel):
    """Response schema for booking with event details"""

    booking_id: int
    user_id: str
    event_id: str
    num_seats: int
    price_per_seat: float
    total_price: float
    slot: str
    booking_date: date
    booking_status: BookingStatus
    created_at: datetime
    updated_at: datetime

    # Event details
    event_title: Optional[str] = None
    event_slug: Optional[str] = None
    event_location: Optional[str] = None
    event_start_date: Optional[date] = None
    event_end_date: Optional[date] = None

    @field_serializer("booking_status")
    def serialize_booking_status(self, value: BookingStatus) -> str:
        """Serialize BookingStatus enum to string"""
        return str(value)

    class Config:
        from_attributes = True


class BookingWithUserResponse(BaseModel):
    """Response schema for booking with user details (for organizers)"""

    booking_id: int
    user_id: str
    event_id: str
    num_seats: int
    price_per_seat: float
    total_price: float
    slot: str
    booking_date: date
    booking_status: BookingStatus
    created_at: datetime
    updated_at: datetime

    # User details (encrypted fields will be handled in service layer)
    user_email: Optional[str] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None

    @field_serializer("booking_status")
    def serialize_booking_status(self, value: BookingStatus) -> str:
        """Serialize BookingStatus enum to string"""
        return str(value)

    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    """Response schema for list of bookings"""

    bookings: List[BookingResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class BookingWithEventListResponse(BaseModel):
    """Response schema for list of bookings with event details"""

    bookings: List[BookingWithEventResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class BookingWithUserListResponse(BaseModel):
    """Response schema for list of bookings with user details"""

    bookings: List[BookingWithUserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class BookingStatsResponse(BaseModel):
    """Response schema for booking statistics"""

    total_bookings: int
    approved_bookings: int
    pending_bookings: int
    cancelled_bookings: int
    failed_bookings: int
    total_revenue: float
    total_seats_booked: int
