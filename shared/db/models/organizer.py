from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from shared.core.security import generate_searchable_hash
from shared.db.models.base import EventsBase
from shared.db.types import EncryptedString

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
    payment_preference: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=True
    )
    store_name: Mapped[str] = mapped_column(String, nullable=True)
    store_url: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)

    # Keep this as unique (used in the relationship)
    ref_number: Mapped[str] = mapped_column(String(length=6), unique=True)

    purpose: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    organizer_login: Mapped["AdminUser"] = relationship(
        "AdminUser",
        back_populates="business_profile",
        uselist=False,
        lazy="joined",
    )
