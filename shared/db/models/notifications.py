from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, Index, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from .base import EventsBase


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class NotificationTargetApp(str, Enum):
    END_USER_APP = "end_user_app"
    ADMIN = "admin"
    ORGANIZER = "organizer"


class Notification(EventsBase):
    __tablename__ = "notifications"

    notification_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Avoid reserved keyword "metadata"
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel, name="notification_channel", create_constraint=True),
        nullable=False,
        server_default=NotificationChannel.IN_APP.value,
    )

    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus, name="notification_status", create_constraint=True),
        nullable=False,
        server_default=NotificationStatus.UNREAD.value,
    )

    target_app: Mapped[NotificationTargetApp] = mapped_column(
        SQLEnum(NotificationTargetApp, name="notification_target_app", create_constraint=True),
        nullable=False,
        server_default=NotificationTargetApp.END_USER_APP.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_notifications_user_id_notification_id_desc",
            "user_id",
            "notification_id",
            postgresql_using="btree",
        ),
        Index("ix_notifications_status", "status", postgresql_using="btree"),
        Index("ix_notifications_target_app", "target_app", postgresql_using="btree"),
    )
