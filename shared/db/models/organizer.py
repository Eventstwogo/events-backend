from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
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


class QueryStatus(str, Enum):
    QUERY_OPEN = "open"
    QUERY_IN_PROGRESS = "in-progress"
    QUERY_ANSWERED = "resolved"
    QUERY_CLOSED = "closed"


class BusinessProfile(EventsBase):
    __tablename__ = "e2gbusinessprofile"

    sno: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    business_id: Mapped[str] = mapped_column(
        String(length=6), ForeignKey("e2gadminusers.business_id"), unique=True
    )
    type_ref_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gorganizertype.type_id", ondelete="SET NULL"),
        nullable=True,
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
    is_approved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    organizer_type: Mapped["OrganizerType"] = relationship(
        "OrganizerType",
        back_populates="business_profiles",
        lazy="joined",
    )


class OrganizerQuery(EventsBase):
    __tablename__ = "e2gorganizerqueries"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    sender_user_id: Mapped[str] = mapped_column(
        String, nullable=False
    )  # who raised the query
    receiver_user_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # admin who handles
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # The full threaded messages between vendor <-> admin
    thread: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,  # using JSONB for PostgreSQL
        default=list,
        nullable=False,
    )

    query_status: Mapped[QueryStatus] = mapped_column(
        SQLAlchemyEnum(QueryStatus),
        default=QueryStatus.QUERY_OPEN,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )


class OrganizerType(EventsBase):
    __tablename__ = "e2gorganizertype"

    type_id: Mapped[str] = mapped_column(
        String(6),
        primary_key=True,
        unique=True,
        nullable=False,
    )
    organizer_type: Mapped[str] = mapped_column(
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

    # Back relationship to BusinessProfile
    business_profiles: Mapped[list["BusinessProfile"]] = relationship(
        "BusinessProfile",
        back_populates="organizer_type",
        cascade="all, delete-orphan",
    )
