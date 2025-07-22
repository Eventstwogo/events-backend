from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from shared.db.models.base import EventsBase

if TYPE_CHECKING:
    from shared.db.models.admin_users import AdminUser
    from shared.db.models.categories import Category, SubCategory


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
    event_slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    event_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    organizer_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gadminusers.user_id"),
        nullable=False,
        index=True,
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
    event_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    slot_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        unique=True,
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
