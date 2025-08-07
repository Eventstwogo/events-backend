from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.models.base import EventsBase


# Enum for contact_us status
class ContactUsStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# ContactUs model
class ContactUs(EventsBase):
    __tablename__ = "e2gcontactus"

    contact_us_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    firstname: Mapped[str] = mapped_column(String(100), nullable=False)
    lastname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    contact_us_status: Mapped[ContactUsStatus] = mapped_column(
        SQLAlchemyEnum(ContactUsStatus),
        default=ContactUsStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
