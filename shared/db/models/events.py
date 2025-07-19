from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
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
    from shared.db.models.categories import Category, SubCategory
    from shared.db.models.users import User


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
        ForeignKey(column="e2gsubcategories.subcategory_id"), nullable=True
    )
    event_slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    event_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    organizer_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gusers.user_id"),
        nullable=False,
        index=True,
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
    organizer: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )
    slots: Mapped[List["EventSlot"]] = relationship(
        "EventSlot",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="EventSlot.slot_order",
    )

    # Table indexes for better performance
    __table_args__ = (
        Index("ix_events_organizer_created", "organizer_id", "created_at"),
        Index("ix_events_title_search", "event_title"),
    )


class EventSlot(EventsBase):
    __tablename__ = "e2geventslots"

    slot_ids: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gevents.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    slot_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
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
        Index("ix_eventslots_event_order", "event_id", "slot_order"),
        Index("ix_eventslots_created", "created_at"),
    )
