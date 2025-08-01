from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    DateTime,
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
