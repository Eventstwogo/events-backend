from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from shared.db.models.admin_users import AdminUser
from shared.db.models.events import Event  


from shared.db.models.base import EventsBase

class CouponStatus(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"

    def __str__(self):
        return self.name.lower()


class Coupon(EventsBase):
    __tablename__ = "e2gcoupons"

    coupon_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True, nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gevents.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organizer_id: Mapped[str] = mapped_column(
        String(6),
        ForeignKey("e2gadminusers.user_id"),
        nullable=False,
        index=True,
    )
    coupon_name: Mapped[str] = mapped_column(String(100), nullable=False)
    coupon_code: Mapped[str] = mapped_column(String(100), nullable=False)
    coupon_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    number_of_coupons: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_coupons: Mapped[int] = mapped_column(Integer, nullable=False)
    sold_coupons: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coupon_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    event: Mapped["Event"] = relationship("Event", lazy="selectin")
    organizer: Mapped["AdminUser"] = relationship("AdminUser", lazy="selectin")

    # Constraints
    __table_args__ = (
        CheckConstraint("coupon_percentage >= 0 AND coupon_percentage <= 100", name="valid_coupon_percentage"),
        CheckConstraint("number_of_coupons > 0", name="positive_number_of_coupons"),
        CheckConstraint("sold_coupons >= 0", name="non_negative_sold_coupons"),
        UniqueConstraint("coupon_name", "event_id", name="uq_event_coupon_name"),
        Index("ix_coupon_event_id", "event_id"),
        Index("ix_coupon_organizer_id", "organizer_id"),
    )
