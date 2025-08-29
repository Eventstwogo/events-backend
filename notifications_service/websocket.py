from __future__ import annotations

from typing import Dict, Tuple

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.notifications import NotificationTargetApp
from shared.dependencies.user import get_current_user_from_token
from shared.db.sessions.database import get_db



class WebSocketManager:
    def __init__(self) -> None:
        # Key = (user_id, app_type), Value = WebSocket
        self.active_connections: Dict[Tuple[str, NotificationTargetApp], WebSocket] = {}

    async def connect(self, user_id: str, app_type: NotificationTargetApp, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[(user_id, app_type)] = websocket

    def disconnect(self, user_id: str, app_type: NotificationTargetApp) -> None:
        self.active_connections.pop((user_id, app_type), None)

    async def send_to_user(self, user_id: str, app_type: NotificationTargetApp, message: dict) -> None:
        ws = self.active_connections.get((user_id, app_type))
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id, app_type)

    async def broadcast_to_app(self, app_type: NotificationTargetApp, message: dict) -> None:
        """Send message to all connected users of a specific app type."""
        to_remove = []
        for (uid, atype), ws in self.active_connections.items():
            if atype == app_type:
                try:
                    await ws.send_json(message)
                except Exception:
                    to_remove.append((uid, atype))
        for key in to_remove:
            self.active_connections.pop(key, None)


ws_manager = WebSocketManager()
router = APIRouter()


@router.websocket("/ws/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token as query param"),
    app_type: NotificationTargetApp = Query(..., description="App type (end_user_app, admin, organizer)"),
    db: AsyncSession = Depends(get_db),
):
    # Authenticate token and get user
    user = await get_current_user_from_token(token, db)
    user_id = str(user.user_id)

    await ws_manager.connect(user_id, app_type, websocket)

    try:
        while True:
            # Keep alive – ignore incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, app_type)
