from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Enum as SQLAlchemyEnum

from shared.db.models.base import EventsBase

if TYPE_CHECKING:
    from shared.db.models.admin_users import AdminUser
    from shared.db.models.categories import Category, SubCategory
    from shared.db.models.users import User


# -------------------- ENUMS -------------------- #


class BookingStatus(str, Enum):
    """Possible statuses for an event booking."""

    PROCESSING = "PROCESSING"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value.lower()


class PaymentStatus(str, Enum):
    """Possible payment statuses for an event booking."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

    def __str__(self) -> str:
        return self.value.lower()


class EventStatus(str, Enum):
    """Possible statuses for an event."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"

    def __str__(self) -> str:
        return self.value.lower()


# -------------------- MAIN EVENT TABLE -------------------- #


class NewEvent(EventsBase):
    """Represents an event with multiple slots and seat categories."""

    __tablename__ = "e2gevents_new"

    event_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey("e2gcategories.category_id"), nullable=False
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

    event_slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    event_title: Mapped[str] = mapped_column(Text, nullable=False)

    event_dates: Mapped[List[date]] = mapped_column(
        PG_ARRAY(Date), nullable=False, default=list
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=True)

    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_online: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    card_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    banner_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_extra_images: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, default=list, nullable=True
    )

    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, default={}, nullable=True
    )
    hash_tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    event_status: Mapped[EventStatus] = mapped_column(
        SQLAlchemyEnum(
            EventStatus, name="new_event_status_enum", native_enum=False
        ),
        default=EventStatus.INACTIVE,
        nullable=False,
        index=True,
    )
    featured_event: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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
    new_category: Mapped["Category"] = relationship(
        "Category", back_populates="new_events", lazy="selectin"
    )
    new_subcategory: Mapped[Optional["SubCategory"]] = relationship(
        "SubCategory", back_populates="new_events", lazy="selectin"
    )
    new_organizer: Mapped["AdminUser"] = relationship(
        "AdminUser",
        back_populates="organized_new_events",
        lazy="selectin",
    )
    new_slots: Mapped[List[NewEventSlot]] = relationship(
        "NewEventSlot",
        back_populates="new_event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    new_booking_orders: Mapped[List["NewEventBookingOrder"]] = relationship(
        "NewEventBookingOrder",
        back_populates="new_booked_event",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_new_events_organizer_created", "organizer_id", "created_at"),
        Index("ix_new_events_title_search", "event_title"),
    )


# -------------------- EVENT SLOT TABLE -------------------- #


class NewEventSlot(EventsBase):
    """Represents a specific date/time slot for an event."""

    __tablename__ = "e2geventslots_new"

    slot_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    event_ref_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gevents_new.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[str] = mapped_column(
        String(8), nullable=False
    )  # e.g., "10:00 AM"
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    slot_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    new_event: Mapped[NewEvent] = relationship(
        "NewEvent", back_populates="new_slots"
    )
    new_seat_categories: Mapped[List[NewEventSeatCategory]] = relationship(
        "NewEventSeatCategory",
        back_populates="new_slot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    new_booking_orders: Mapped[List["NewEventBookingOrder"]] = relationship(
        "NewEventBookingOrder", back_populates="new_slot", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint(
            "event_ref_id",
            "slot_date",
            "start_time",
            name="uq_event_slot_datetime",
        ),
    )


# -------------------- SEAT CATEGORY TABLE -------------------- #


class NewEventSeatCategory(EventsBase):
    """Represents a category of seats within an event slot."""

    __tablename__ = "e2gevent_seat_categories_new"

    seat_category_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    slot_ref_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("e2geventslots_new.slot_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_label: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    booked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    held: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seat_category_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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
    new_slot: Mapped["NewEventSlot"] = relationship(
        "NewEventSlot", back_populates="new_seat_categories"
    )
    new_bookings: Mapped[List["NewEventBooking"]] = relationship(
        "NewEventBooking", back_populates="new_seat_category", lazy="selectin"
    )

    # __table_args__ = (
    #     UniqueConstraint("slot_ref_id", "category_label", name="uq_slot_category"),
    # )


# -------------------- EVENT BOOKING ORDER TABLE -------------------- #


class NewEventBookingOrder(EventsBase):
    """Represents a single order for one or more seat category bookings."""

    __tablename__ = "e2gevent_booking_orders"

    order_id: Mapped[str] = mapped_column(
        String(12), primary_key=True, index=True
    )

    user_ref_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gusers.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_ref_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gevents_new.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    slot_ref_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("e2geventslots_new.slot_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    booking_status: Mapped[BookingStatus] = mapped_column(
        SQLAlchemyEnum(
            BookingStatus, name="booking_order_status_enum", native_enum=False
        ),
        default=BookingStatus.PROCESSING,
        nullable=False,
        index=True,
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLAlchemyEnum(
            PaymentStatus, name="payment_order_status_enum", native_enum=False
        ),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )

    payment_reference: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    coupon_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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
    new_user: Mapped["User"] = relationship(
        "User",
        back_populates="new_event_booking_orders",  # ← Add this in User model!
        lazy="selectin",
    )
    new_booked_event: Mapped["NewEvent"] = relationship(
        "NewEvent",
        back_populates="new_booking_orders",  # ← Add this in NewEvent
        lazy="selectin",
    )
    new_slot: Mapped["NewEventSlot"] = relationship(
        "NewEventSlot",
        back_populates="new_booking_orders",  # ← Add this in NewEventSlot
        lazy="selectin",
    )

    # one order → many booking line items
    line_items: Mapped[List["NewEventBooking"]] = relationship(
        "NewEventBooking",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# -------------------- EVENT BOOKING TABLE -------------------- #


class NewEventBooking(EventsBase):
    """Represents a booking line item (specific seat category) within an order."""

    __tablename__ = "e2gevent_bookings_new"

    booking_id: Mapped[str] = mapped_column(
        String(12), primary_key=True, index=True
    )

    order_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("e2gevent_booking_orders.order_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    seat_category_ref_id: Mapped[str] = mapped_column(
        ForeignKey(
            "e2gevent_seat_categories_new.seat_category_id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )

    num_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_seat: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

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
    order: Mapped["NewEventBookingOrder"] = relationship(
        "NewEventBookingOrder", back_populates="line_items"
    )
    new_seat_category: Mapped["NewEventSeatCategory"] = relationship(
        "NewEventSeatCategory", back_populates="new_bookings", lazy="selectin"
    )

    __table_args__ = (
        # Ensure one user can’t double-book same seat category in the same slot
        UniqueConstraint(
            "order_id",
            "seat_category_ref_id",
            name="uq_order_seatcategory_once",
        ),
    )
