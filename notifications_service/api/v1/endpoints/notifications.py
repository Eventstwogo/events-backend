from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.notifications import Notification, NotificationStatus
from shared.db.sessions.database import get_db
from shared.dependencies.user import get_current_active_user
from notifications_service.service import NotificationService
from notifications_service.websocket import ws_manager

router = APIRouter()


class NotificationOut(BaseModel):
    notification_id: str
    user_id: str
    actor_id: Optional[str]
    title: str
    body: str
    extra_metadata: dict
    channel: str
    status: str
    target_app: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[NotificationOut])
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Fetch items older than this notification_id"),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(Notification.user_id == current_user.user_id)
    if cursor is not None:
        query = query.where(Notification.notification_id < cursor)
    query = query.order_by(desc(Notification.created_at)).limit(limit)

    res = await db.execute(query)
    return res.scalars().all()


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        update(Notification)
        .where(
            Notification.notification_id == notification_id,
            Notification.user_id == current_user.user_id,
        )
        .values(status=NotificationStatus.READ)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(q)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return {"status": "ok"}


@router.post("/read-all")
async def mark_all_read(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        update(Notification)
        .where(Notification.user_id == current_user.user_id)
        .values(status=NotificationStatus.READ)
        .execution_options(synchronize_session=False)
    )
    await db.execute(q)
    await db.commit()
    return {"status": "ok"}


@router.post("/send-test")
async def send_test_notification(
    title: str = Query("Hello"),
    body: str = Query("Welcome to Events2Go"),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db, ws_manager)
    notif = await service.create_notification(
        user_id=current_user.user_id, title=title, body=body, metadata={}
    )
    return {"notification_id": notif.notification_id}
