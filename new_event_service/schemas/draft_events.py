from pydantic import BaseModel, EmailStr, Field, computed_field
from typing import Optional, List, Dict
from datetime import date, time, timedelta


# -----------------------
# Organizer Details
# -----------------------
class OrganizerInputData(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
    website: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None


# -----------------------
# Step 1: Basic Event Info
# -----------------------
class EventStepOneData(BaseModel):
    user_id: str
    event_type: str
    event_title: str
    event_slug: str
    category_id: str
    subcategory_id: Optional[str] = None
    custom_subcategory_name: Optional[str] = None
    extra_data: Optional[Dict[str, OrganizerInputData]] = None


# -----------------------
# Location Details
# -----------------------
class LocationInputData(BaseModel):
    address: str
    state: str
    country: str
    venue_name: Optional[str] = None
    city: Optional[str] = None
    suburb: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    google_maps_link: Optional[str] = None


# -----------------------
# Event Dates
# -----------------------
class EventDatesInputData(BaseModel):
    event_dates: List[date] = Field(default_factory=list)
    time_zone: Optional[str] = None
    recurring_dates: Optional[List[date]] = None
    recurring_frequency: Optional[str] = None  # e.g., daily, weekly, monthly
    recurring_end_date: Optional[date] = None

    @computed_field
    @property
    def start_date(self) -> Optional[date]:
        return self.event_dates[0] if self.event_dates else None

    @computed_field
    @property
    def end_date(self) -> Optional[date]:
        return self.event_dates[-1] if self.event_dates else None

# -----------------------
# Extended Event Info (extra_data wrapper)
# -----------------------
class ExtendedEventInfo(BaseModel):
    address: Optional[LocationInputData] = None
    event_dates: Optional[EventDatesInputData] = None
    description: Optional[str] = None
    languages: Optional[List[str]] = None
    age_range: Optional[str] = None
    target_audience: Optional[str] = None
    audience_size: Optional[int] = None
    registration_required: Optional[bool] = None
    registration_instructions: Optional[str] = None
    
class EventStepTwoDataNew(BaseModel):
    event_ref_id: str
    location: Optional[str] = None
    extra_data: Optional[ExtendedEventInfo] = None


# -----------------------
# Step 2: Extended Event Info
# -----------------------
class EventStepTwoData(BaseModel):
    event_ref_id: str
    location: Optional[str] = None
    extra_data: Dict = Field(default_factory=dict)
    # Recommended keys inside extra_data:
    # - address: LocationInputData
    # - event_dates: EventDatesInputData
    # - description: str
    # - languages: List[str]
    # - age_range: str
    # - target_audience: str
    # - audience_size: int
    # - registration_required: bool
    # - registration_instructions: Optional[str]


# -----------------------
# Step 3: Event Images
# -----------------------
class EventStepThreeData(BaseModel):
    event_ref_id: str
    card_image: bytes
    banner_image: bytes
    extra_images: Optional[List[bytes]] = None


# -----------------------
# Step 4: Event Slots
# -----------------------
class EventStepFourData(BaseModel):
    event_ref_id: str
    slot_date: date
    start_time: time
    end_time: time
    duration: Optional[timedelta] = None


# -----------------------
# Step 5: Ticketing Info
# -----------------------
class EventStepFiveData(BaseModel):
    event_ref_id: str
    slot_ref_id: str
    category_name: str
    price_per_seat: float
    capacity: int


# -----------------------
# Event Organizer Output
# -----------------------
class OrganizerOutputData(BaseModel):
    id: str
    name: str
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
    website: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None


# -----------------------
# Event Location Output
# -----------------------
class LocationOutputData(LocationInputData):
    pass


# -----------------------
# Event Dates Output
# -----------------------
class EventDatesOutputData(EventDatesInputData):
    pass


# -----------------------
# Event Images Output
# -----------------------
class EventImagesOutputData(BaseModel):
    card_image_url: str
    banner_image_url: str
    extra_images_urls: Optional[List[str]] = None


# -----------------------
# Ticketing Info Output
# -----------------------
class TicketingInfoOutputData(BaseModel):
    slot_ref_id: str
    category_name: str
    price_per_seat: float
    capacity: int


# -----------------------
# Event Full Output
# -----------------------
class EventOutputData(BaseModel):
    event_id: str
    event_title: str
    event_slug: str
    organizer: OrganizerOutputData
    location: LocationOutputData
    event_dates: EventDatesOutputData
    images: EventImagesOutputData
    description: Optional[str] = None
    languages: Optional[List[str]] = None
    age_range: Optional[str] = None
    target_audience: Optional[str] = None
    audience_size: Optional[int] = None
    registration_required: Optional[bool] = None
    registration_instructions: Optional[str] = None
    ticketing_info: Optional[List[TicketingInfoOutputData]] = None
