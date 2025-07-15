# Third-Party Library Imports
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.models.base import EventsBase


class Config(EventsBase):
    __tablename__ = "e2gconfig"

    id: Mapped[int] = mapped_column(
        primary_key=True, default=1
    )  # Single config entry
    default_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # plain password (optional)
    default_password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # actual hash used
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    global_180_day_flag: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # flag for all users
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
