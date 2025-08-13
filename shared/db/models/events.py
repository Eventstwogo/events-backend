from datetime import date, datetime
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Enum as SQLAlchemyEnum

from shared.db.models.base import EventsBase

if TYPE_CHECKING:
    from shared.db.models.admin_users import AdminUser
    from shared.db.models.categories import Category, SubCategory
    from shared.db.models.users import User


class BookingStatus(str, Enum):
    PROCESSING = "PROCESSING"  # Booking request is being handled
    APPROVED = "APPROVED"  # Booking confirmed and finalized
    CANCELLED = "CANCELLED"  # Booking canceled
    FAILED = "FAILED"  # Booking failed (e.g., no seats)

    def __str__(self):
        return self.name.lower()


class PaymentStatus(str, Enum):
    PENDING = "PENDING"  # Payment not yet made or awaiting confirmation
    APPROVED = "APPROVED"  # Payment successfully processed
    FAILED = "FAILED"  # Payment attempt failed
    REFUNDED = "REFUNDED"  # Payment returned to user
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"  # Partial refund issued
    CANCELLED = "CANCELLED"  # Payment cancelled before completion

    def __str__(self):
        return self.name.lower()


class EventStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"

    def __str__(self):
        return self.name.lower()


class Event(EventsBase):
    __tablename__ = "e2gevents"

    event_id: Mapped[str] = mapped_column(
        String(6),
        primary_key=True,
        unique=True,
        nullable=False,
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey(column="e2gcategories.category_id"), nullable=False
    )
    subcategory_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("e2gsubcategories.subcategory_id", ondelete="SET NULL"),
        nullable=True,
    )
    organizer_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gadminusers.user_id"),
        nullable=False,
        index=True,
    )
    event_slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    event_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(
        Date(), nullable=False, server_default=func.current_date()
    )
    end_date: Mapped[date] = mapped_column(
        Date(), nullable=False, server_default=func.current_date()
    )
    location: Mapped[str] = mapped_column(Text, nullable=True)
    is_online: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    card_image: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    banner_image: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    event_extra_images: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default={},
    )
    hash_tags: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    event_status: Mapped[EventStatus] = mapped_column(
        SQLAlchemyEnum(
            EventStatus, name="event_status_enum", native_enum=False
        ),
        nullable=False,
        default=EventStatus.INACTIVE,
        index=True,
    )
    slot_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        unique=True,
    )
    featured_event: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category",
        lazy="selectin",
    )
    subcategory: Mapped[Optional["SubCategory"]] = relationship(
        "SubCategory",
        lazy="selectin",
    )
    organizer: Mapped["AdminUser"] = relationship(
        "AdminUser",
        lazy="selectin",
    )
    slots: Mapped[List["EventSlot"]] = relationship(
        "EventSlot",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    bookings: Mapped[List["EventBooking"]] = relationship(
        "EventBooking",
        back_populates="booked_event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Table indexes for better performance
    __table_args__ = (
        Index("ix_events_organizer_created", "organizer_id", "created_at"),
        Index("ix_events_title_search", "event_title"),
    )


class EventSlot(EventsBase):
    __tablename__ = "e2geventslots"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    slot_id: Mapped[str] = mapped_column(
        String(8),
        ForeignKey("e2gevents.slot_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    slot_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,  # Contains json data for the slot like date, slots, price, members etc like that
        nullable=False,
    )
    slot_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    event: Mapped["Event"] = relationship(
        "Event", back_populates="slots", lazy="joined"
    )

    # Table indexes and constraints
    __table_args__ = (
        Index("ix_eventslots_slot_id", "slot_id"),
        Index("ix_eventslots_created", "created_at"),
    )


class EventBooking(EventsBase):
    __tablename__ = "e2geventbookings"

    booking_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, index=True
    )

    user_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gusers.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gevents.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    num_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_seat: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )

    slot: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., '10:00 AM - 12:00 PM'
    booking_date: Mapped[date] = mapped_column(
        Date(), server_default=func.current_date(), nullable=False, index=True
    )

    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    booking_status: Mapped[BookingStatus] = mapped_column(
        SQLAlchemyEnum(
            BookingStatus, name="booking_status_enum", native_enum=False
        ),
        nullable=False,
        default=BookingStatus.PROCESSING,
        index=True,
    )

    paypal_order_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    payment_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="event_bookings", lazy="selectin"
    )
    booked_event: Mapped["Event"] = relationship(
        "Event", back_populates="bookings", lazy="selectin"
    )

    # Methods for business logic
    def calculate_total_price(self) -> float:
        """Calculate total price based on number of seats and price per seat."""
        return float(self.num_seats * self.price_per_seat)

    def is_active(self) -> bool:
        """Check if booking is in an active state."""
        return self.booking_status == BookingStatus.APPROVED

    def is_pending(self) -> bool:
        """Check if booking is pending approval."""
        return self.booking_status == BookingStatus.PROCESSING

    def is_cancelled(self) -> bool:
        """Check if booking is cancelled."""
        return self.booking_status == BookingStatus.CANCELLED

    def is_failed(self) -> bool:
        """Check if booking has failed."""
        return self.booking_status == BookingStatus.FAILED

    def update_total_price(self) -> None:
        """Update the total_price field based on current num_seats and price_per_seat."""
        self.total_price = self.calculate_total_price()

    # Business logic constraints and composite indexes
    # Naming convention handled by base class
    __table_args__ = (
        # Composite indexes for common query patterns
        Index("ix_user_booking_date", "user_id", "booking_date"),
        Index("ix_event_booking_date", "event_id", "booking_date"),
        # Business logic constraints
        CheckConstraint("num_seats > 0", name="positive_seats"),
        CheckConstraint("price_per_seat >= 0", name="non_negative_price"),
        CheckConstraint("total_price >= 0", name="non_negative_total"),
        UniqueConstraint(
            "user_id",
            "event_id",
            "slot",
            "booking_date",
            name="uq_user_event_slot_booking_date",
        ),
    )
