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

    booking_status: BookingStatus = Field(..., description="New booking status")


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

    # Payment details
    payment_status: Optional[str] = None
    paypal_order_id: Optional[str] = None

    # User details
    user_email: Optional[str] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_profile_picture: Optional[str] = None

    # Event details
    event_title: Optional[str] = None
    event_slug: Optional[str] = None
    event_location: Optional[str] = None
    event_address: Optional[str] = None
    event_start_date: Optional[date] = None
    event_end_date: Optional[date] = None
    event_card_image: Optional[str] = None

    # Slot details
    slot_time: Optional[str] = None

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

    # Payment details
    payment_status: Optional[str] = None
    paypal_order_id: Optional[str] = None

    # Event details
    event_title: Optional[str] = None
    event_slug: Optional[str] = None
    event_location: Optional[str] = None
    event_address: Optional[str] = None
    event_start_date: Optional[date] = None
    event_end_date: Optional[date] = None
    event_card_image: Optional[str] = None

    # Slot details
    slot_time: Optional[str] = None

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

    # Payment details
    payment_status: Optional[str] = None
    paypal_order_id: Optional[str] = None

    # User details (encrypted fields will be handled in service layer)
    user_email: Optional[str] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_profile_picture: Optional[str] = None

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


class BookingUserDetails(BaseModel):
    """User details for booking response"""

    user_id: str
    email: str
    username: str


class BookingEventDetails(BaseModel):
    """Event details for booking response"""

    event_id: str
    title: str
    slug: str
    location: Optional[str] = None
    address: Optional[str] = None
    start_date: date
    end_date: date
    card_image: Optional[str] = None


class BookingDetailsResponse(BaseModel):
    """Detailed booking response with nested user and event details"""

    booking_id: int
    num_seats: int
    price_per_seat: float
    total_price: float
    slot: str
    slot_time: Optional[str] = None
    booking_date: date
    booking_status: str
    payment_status: Optional[str] = None
    paypal_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: BookingUserDetails
    event: BookingEventDetails

    class Config:
        from_attributes = True


class UserBookingItemResponse(BaseModel):
    """Individual booking item for user bookings list"""

    booking_id: int
    event_title: str
    event_card_image: Optional[str] = None
    slot_time: Optional[str] = None
    num_seats: int
    booking_date: date
    total_price: float
    booking_status: str

    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    """Pagination information"""

    page: int
    per_page: int
    total_items: int
    total_pages: int


class UserBookingsListResponse(BaseModel):
    """Response schema for user bookings list with pagination"""

    events: List[UserBookingItemResponse]
    page: int
    per_page: int
    total_items: int
    total_pages: int

    class Config:
        from_attributes = True


# New schemas for organizer bookings with events and slots structure
class OrganizerBookingDetails(BaseModel):
    """Individual booking details for organizer response"""

    booking_id: int
    booking_date: date
    num_seats: int
    total_price: float
    booking_status: str
    payment_status: Optional[str] = None
    paypal_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    username: str


class OrganizerSlotDetails(BaseModel):
    """Slot details with bookings for organizer response"""

    slot_id: str
    slot_time: str
    total_capacity: int
    booked_seats: int
    remaining_seats: int
    user_bookings_count: int
    bookings: List[OrganizerBookingDetails]


class OrganizerEventDetails(BaseModel):
    """Event details for organizer response"""

    event_id: str
    title: str
    slug: str
    card_image: Optional[str] = None
    start_date: date
    end_date: date
    status: str
    slots_count: int


class OrganizerEventWithSlots(BaseModel):
    """Event with slots and bookings for organizer response"""

    event: OrganizerEventDetails
    slots: List[OrganizerSlotDetails]


class OrganizerEventsCount(BaseModel):
    """Events count summary for organizer"""

    total: int
    active: int
    inactive: int


class OrganizerBookingsResponse(BaseModel):
    """Complete organizer bookings response"""

    events_count: OrganizerEventsCount
    events: List[OrganizerEventWithSlots]
    total_items: int
    page: int
    per_page: int
    total_pages: int


# New schemas for all bookings with complete details
class AllBookingsUserDetails(BaseModel):
    """User details for all bookings response"""

    user_id: str
    username: str
    email: str


class AllBookingsEventDetails(BaseModel):
    """Event details for all bookings response"""

    event_id: str
    event_title: str
    event_slug: str
    start_date: date
    end_date: date
    location: Optional[str] = None
    card_image: Optional[str] = None


class AllBookingsOrganizerDetails(BaseModel):
    """Organizer details for all bookings response"""

    organizer_id: str
    organizer_name: str
    organizer_email: str


class AllBookingsItemResponse(BaseModel):
    """Individual booking item with complete details"""

    booking_id: int
    num_seats: int
    price_per_seat: float
    total_price: float
    slot: str
    booking_date: date
    booking_status: str
    payment_status: Optional[str] = None
    paypal_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Related details
    username: str
    organizer_name: str
    event: AllBookingsEventDetails

    class Config:
        from_attributes = True


class AllBookingsListResponse(BaseModel):
    """Response schema for all bookings list with pagination"""

    bookings: List[AllBookingsItemResponse]
    total_items: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        from_attributes = True


# Simple organizer bookings response for tabular view
class SimpleOrganizerBookingItem(BaseModel):
    """Simple booking item for organizer tabular view"""

    booking_id: int
    event_title: str
    event_id: str
    card_image: Optional[str] = None
    user_name: str
    user_email: str
    slot_time: str
    booking_date: date
    num_seats: int
    total_price: float
    booking_status: str
    payment_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SimpleOrganizerBookingsResponse(BaseModel):
    """Simple response schema for organizer bookings tabular view"""

    bookings: List[SimpleOrganizerBookingItem]
    total_items: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        from_attributes = True
