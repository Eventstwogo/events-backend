from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from shared.db.models.base import EventsBase

if TYPE_CHECKING:
    from shared.db.models.admin_users import AdminUser
    from shared.db.models.new_events import NewEvent


class EventType(EventsBase):
    __tablename__ = "e2geventtype"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    type_id: Mapped[str] = mapped_column(
        String(6),
        unique=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    type_status: Mapped[bool] = mapped_column(
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


class FeaturedEvents(EventsBase):
    __tablename__ = "e2gfeaturedevents"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    feature_id: Mapped[str] = mapped_column(
        String(6),
        unique=True,
        nullable=False,
    )
    user_ref_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gadminusers.user_id"),
        nullable=False,
    )
    event_ref_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gevents_new.event_id"),
        unique=True,
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(
        Date(), nullable=False, server_default=func.current_date()
    )
    end_date: Mapped[date] = mapped_column(
        Date(), nullable=False, server_default=func.current_date()
    )
    total_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    feature_status: Mapped[bool] = mapped_column(
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

    new_event: Mapped["NewEvent"] = relationship(
        "NewEvent", back_populates="featured_events"
    )
    user_ref: Mapped["AdminUser"] = relationship(
        "AdminUser", back_populates="featured_refs"
    )
