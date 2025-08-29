from __future__ import annotations

from typing import Optional, List
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from notifications_service.websocket import WebSocketManager
from shared.db.models.notifications import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationTargetApp,
)


class NotificationService:
    """Service to persist, fetch, and dispatch notifications."""

    def __init__(self, db: AsyncSession, websocket_manager: WebSocketManager) -> None:
        self.db = db
        self.ws_manager = websocket_manager

    async def create_notification(
        self,
        *,
        user_id: str,
        title: str,
        body: str,
        metadata: Optional[dict] = None,
        actor_id: Optional[str] = None,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        target_app: NotificationTargetApp = NotificationTargetApp.END_USER_APP,
    ) -> Notification:
        notif = Notification(
            notification_id=str(uuid.uuid4()),
            user_id=user_id,
            actor_id=actor_id,
            title=title,
            body=body,
            extra_metadata=metadata or {},
            channel=channel,
            status=NotificationStatus.UNREAD,
            target_app=target_app,
        )
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)

        # Fire-and-forget send to websocket (best-effort)
        try:
            await self.ws_manager.send_to_user(
                user_id=user_id,
                app_type=notif.target_app,
                message={
                    "type": "notification",
                    "data": {
                        "action": "create",
                        "payload": {
                            "notification_id": notif.notification_id,
                            "user_id": notif.user_id,
                            "actor_id": notif.actor_id,
                            "title": notif.title,
                            "body": notif.body,
                            "extra_metadata": notif.extra_metadata,
                            "channel": notif.channel.value,
                            "status": notif.status.value,
                            "target_app": notif.target_app.value,
                            "created_at": notif.created_at.isoformat(),
                        },
                    },
                },
            )
        except Exception:
            # Do not block on socket failures
            pass

        return notif

    async def get_user_notifications(self, user_id: str, limit: int = 20) -> List[Notification]:
        """Fetch recent notifications for a user."""
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: str) -> None:
        """Mark a notification as read."""
        stmt = (
            update(Notification)
            .where(Notification.notification_id == notification_id)
            .values(status=NotificationStatus.READ)
        )
        await self.db.execute(stmt)
        await self.db.commit()
