from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    DateTime,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from shared.db.models.base import EventsBase

if TYPE_CHECKING:
    from shared.db.models.admin_users import AdminUser


# Enum for Query status
class QueryStatus(Enum):
    """Enum for query status values"""

    QUERY_OPEN = "open"
    QUERY_ANSWERED = "answered"
    QUERY_CLOSED = "close"


class BusinessProfile(EventsBase):
    __tablename__ = "e2gbusinessprofile"

    sno: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    business_id: Mapped[str] = mapped_column(
        String(length=6), ForeignKey("e2gadminusers.business_id"), unique=True
    )
    abn_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    abn_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    profile_details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    business_logo: Mapped[str] = mapped_column(String, nullable=True)
    store_name: Mapped[str] = mapped_column(String, nullable=True)
    store_url: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)

    # Keep this as unique (used in the relationship)
    ref_number: Mapped[str] = mapped_column(String(length=6), unique=True)

    purpose: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_approved: Mapped[int] = mapped_column(
        Integer, default=-2, nullable=False
    )
    reviewer_comment: Mapped[str] = mapped_column(Text, nullable=True)
    approved_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    organizer_login: Mapped["AdminUser"] = relationship(
        "AdminUser",
        back_populates="business_profile",
        uselist=False,
        lazy="joined",
    )


class OrganizerQuery(EventsBase):
    __tablename__ = "e2gorganizerqueries"

    query_id: Mapped[str] = mapped_column(
        String(8), primary_key=True, unique=True
    )
    organizer_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gadminusers.user_id", ondelete="SET NULL"),
        nullable=False,
    )
    admin_user_id: Mapped[Optional[str]] = mapped_column(
        String(6),
        ForeignKey("e2gadminusers.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answers: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )
    query_status: Mapped[QueryStatus] = mapped_column(
        SQLAlchemyEnum(QueryStatus),
        default=QueryStatus.QUERY_OPEN,
        nullable=False,
        server_default="open",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    # Relationships to AdminUser
    organizer: Mapped["AdminUser"] = relationship(
        "AdminUser",
        foreign_keys=[organizer_id],
        back_populates="organizer_queries",
    )

    admin_user: Mapped[Optional["AdminUser"]] = relationship(
        "AdminUser",
        foreign_keys=[admin_user_id],
        back_populates="admin_queries",
    )
