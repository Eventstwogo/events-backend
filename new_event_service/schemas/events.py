from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
)

from new_event_service.utils.utils import calculate_end_time
from shared.db.models.new_events import EventStatus
from shared.utils.file_uploads import get_media_url


def extra_images_media_urls(value: Optional[List[str]]) -> Optional[List[str]]:
    if not value:
        return None
    result = [get_media_url(url) for url in value]
    result = [r for r in result if r is not None]
    return result if result else None


class EventResponse(BaseModel):
    event_id: str
    event_title: str
    event_slug: str
    event_type: Optional[str]
    card_image: Optional[str]
    location: Optional[str]
    extra_data: Optional[dict]
    category_title: Optional[str]
    subcategory_title: Optional[str]
    organizer_name: Optional[str]
    event_status: str
    created_at: datetime
    featured: bool

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)


class EventListResponse(BaseModel):
    events: List[EventResponse]
    page: int
    limit: int
    total: int


# Related entity schemas
class CategoryInfo(BaseModel):
    """Schema for category information in event response"""

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    category_slug: str = Field(..., description="Category slug")
    category_img_thumbnail: Optional[str] = Field(
        None, description="Category thumbnail image"
    )

    @field_serializer("category_img_thumbnail")
    def serialize_category_img_thumbnail(
        self, value: Optional[str]
    ) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    model_config = ConfigDict(from_attributes=True)


class SubCategoryInfo(BaseModel):
    """Schema for subcategory information in event response"""

    subcategory_id: str = Field(..., description="Subcategory ID")
    subcategory_name: str = Field(..., description="Subcategory name")
    subcategory_slug: str = Field(..., description="Subcategory slug")
    subcategory_img_thumbnail: Optional[str] = Field(
        None, description="Subcategory thumbnail image"
    )

    @field_serializer("subcategory_img_thumbnail")
    def serialize_subcategory_img_thumbnail(
        self, value: Optional[str]
    ) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    model_config = ConfigDict(from_attributes=True)


class OrganizerInfo(BaseModel):
    """Schema for organizer information in event response"""

    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    profile_picture: Optional[str] = Field(
        None, description="Profile picture URL"
    )

    @field_serializer("profile_picture")
    def serialize_profile_picture(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    model_config = ConfigDict(from_attributes=True)


class SeatCategoryResponse(BaseModel):
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
    end_time: Optional[str] = None
    seatCategories: List[SeatCategoryResponse]

    @field_serializer("end_time", mode="plain")
    def serialize_end_time(self, value, info):
        # If not already set, compute from time + duration
        if not value:
            return calculate_end_time(self.time, self.duration)
        return value


class SlotAnalyticsPerDay(BaseModel):
    total_slots: int
    total_tickets: int
    booked_tickets: int
    held_tickets: int
    available_tickets: int


class SlotAnalytics(BaseModel):
    overall_slots: int
    overall_tickets: int
    overall_booked: int
    overall_held: int
    overall_available: int
    per_day: Dict[str, SlotAnalyticsPerDay]


class EventSlotResponseWrapper(BaseModel):
    event_ref_id: str
    event_dates: List[date]
    slot_data: Dict[str, List[EventSlotResponse]]
    slot_analytics: Optional[SlotAnalytics] = None  # New field

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

        # Analytics accumulators
        overall_slots = 0
        overall_tickets = 0
        overall_booked = 0
        overall_held = 0
        per_day_analytics = {}

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

            day_total_tickets = 0
            day_booked = 0
            day_held = 0

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

                # Aggregate per-slot ticket info
                for s in seat_categories:
                    day_total_tickets += s.totalTickets
                    day_booked += s.booked
                    day_held += s.held

                slot_resp = EventSlotResponse(
                    slot_id=slot["slot_id"],
                    time=slot["time"],
                    duration=slot["duration"],
                    seatCategories=seat_categories,
                    end_time=calculate_end_time(slot["time"], slot["duration"]),
                )
                slot_list.append(slot_resp)

            # Store slots per day
            slot_data_response[event_date_str] = slot_list

            # Update per-day analytics
            per_day_analytics[event_date_str] = SlotAnalyticsPerDay(
                total_slots=len(slots),
                total_tickets=day_total_tickets,
                booked_tickets=day_booked,
                held_tickets=day_held,
                available_tickets=day_total_tickets - day_booked - day_held,
            )

            # Update overall accumulators
            overall_slots += len(slots)
            overall_tickets += day_total_tickets
            overall_booked += day_booked
            overall_held += day_held

        slot_analytics = SlotAnalytics(
            overall_slots=overall_slots,
            overall_tickets=overall_tickets,
            overall_booked=overall_booked,
            overall_held=overall_held,
            overall_available=overall_tickets - overall_booked - overall_held,
            per_day=per_day_analytics,
        )

        return cls(
            event_ref_id=event_ref_id,
            event_dates=event_dates_parsed,
            slot_data=slot_data_response,
            slot_analytics=slot_analytics,
        )


class NewEventSlotResponse(BaseModel):
    """Schema for event response"""

    event_id: str = Field(..., description="Event ID")
    event_title: str = Field(..., description="Event title")
    event_slug: str = Field(..., description="Event slug")
    event_type: Optional[str] = Field(None, description="Event type")
    event_dates: List[date] = Field(..., description="Event dates")
    location: Optional[str] = Field(
        None, description="Event location (if applicable)"
    )
    is_online: bool = Field(
        ..., description="Whether the event is online or in-person"
    )
    event_status: EventStatus = Field(
        default=EventStatus.INACTIVE,  # Use a valid enum member as default
        description="The status of the event.",
    )
    featured_event: bool = Field(..., description="Event is featured or not")

    # Related entity information
    category: Optional[CategoryInfo] = Field(
        None, description="Category information"
    )
    subcategory: Optional[SubCategoryInfo] = Field(
        None, description="Subcategory information"
    )
    organizer: Optional[OrganizerInfo] = Field(
        None, description="Organizer information"
    )
    slots: Optional[List[EventSlotResponseWrapper]] = Field(
        None, description="Event slot information"
    )

    # Event content
    card_image: Optional[str] = Field(None, description="Card image URL")
    banner_image: Optional[str] = Field(None, description="Banner image URL")
    event_extra_images: Optional[List[str]] = Field(
        None, description="List of additional event images"
    )
    extra_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional event data"
    )
    hash_tags: Optional[List[str]] = Field(
        None, description="List of hashtags for the event"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    @field_serializer("banner_image")
    def serialize_banner_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    @field_serializer("event_extra_images")
    def serialize_event_extra_images(
        self, value: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Convert relative paths to full media URLs"""
        if not value:
            return value
        return extra_images_media_urls(value)

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        },
    )


class EventSearchResponse(BaseModel):
    event_id: str
    event_title: str
    event_slug: str
    card_image: Optional[str]
    location: Optional[str]
    category_title: str
    subcategory_title: Optional[str] = None
    next_event_date: Optional[date] = None

    @field_serializer("card_image")
    def serialize_card_image(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)
