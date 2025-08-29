# Notification Module Implementation — FastAPI + SQLAlchemy + PostgreSQL

Below is a ready-to-use **implementation specification + engineering prompt** you can use to build (or ask an AI to generate) a production-ready in-app notification module for your Events2Go project. It covers data model, flow logic, services, APIs, WebSocket real-time delivery, background workers, security, deployment notes, and example code snippets. Use this as a blueprint or paste the “Developer Prompt” at the end into an AI to get full code scaffolding.

---

# 1. Goal

Implement **persistent in-app notifications** (no email/SMS) that show in each Next.js app’s header bell icon. Requirements:

* Persist notifications in PostgreSQL.
* Provide REST endpoints to fetch / mark read / paginate.
* Deliver new notifications in real-time using WebSockets.
* Central notification service to create/send notifications.
* Support multiple Next.js frontends (end-user, organizer, admin).
* Use FastAPI, SQLAlchemy ORM (async), Alembic for migrations, PostgreSQL.
* Use Celery + Redis for async processing (recommended) or FastAPI `BackgroundTasks` for small scale.

---

# 2. High-level flow (sequence)

1. Some event occurs (booking created, admin announcement, etc.).
2. Backend calls `NotificationService.create_notification(user_id, payload)`.
3. Service writes notification row to DB.
4. Service pushes the notification to the **WebSocketManager** (if user is connected).
5. WebSocket client in Next.js receives notification JSON and updates UI/unread count.
6. Client loads notifications via `/notifications?limit=20` on initial render.
7. Client marks notification as read via `/notifications/{id}/read`.

---

# 3. Database schema (Postgres)

Simplified and extensible:

```sql
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    actor_id UUID,                -- who triggered the notification (optional)
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb, -- e.g., {"event_id": "...", "type": "booking"}
    channel VARCHAR(20) NOT NULL DEFAULT 'in_app',
    status VARCHAR(20) NOT NULL DEFAULT 'unread', -- unread/read/archived
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_notifications_user_id ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_status ON notifications(status);
```

Notes:

* `metadata` for arbitrary deep-linking (event id, route for front end).
* Use `BIGSERIAL` for scale if you expect many notifications.

---

# 4. SQLAlchemy models (async, Pydantic-ready)

Example `models.py` (SQLAlchemy 1.4+ async):

```python
from sqlalchemy import Column, BigInteger, String, Text, JSON, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    metadata = Column(JSON, default={})
    channel = Column(String(20), nullable=False, default="in_app")
    status = Column(String(20), nullable=False, default="unread")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

Pydantic schema examples for API responses:

```python
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class NotificationOut(BaseModel):
    id: int
    user_id: str
    actor_id: Optional[str]
    title: str
    body: str
    metadata: dict
    channel: str
    status: str
    created_at: datetime
```

---

# 5. Core services (single place to create & dispatch)

Create a `NotificationService` that:

* Writes to DB.
* Sends to WebSocket manager if connected.
* Enqueues extra processing to Celery if needed.

Example interface:

```python
class NotificationService:
    def __init__(self, db_session_factory, websocket_manager, task_queue=None):
        ...

    async def create_notification(self, user_id: UUID, title: str, body: str, metadata: dict = None):
        # 1. persist
        # 2. push to websocket_manager (await websocket_manager.send(user_id, payload))
        # 3. optionally enqueue e.g., audit logs
```

Important: keep business logic out of WebSocket layer; service handles persistence first, then delivery.

---

# 6. WebSocket manager (connection tracking)

A connection manager to map `user_id -> WebSocket` and send messages:

```python
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)
```

WebSocket route:

```python
@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str = Query(...)):
    # 1. authenticate token -> get user_id
    # 2. ws_manager.connect(user_id, websocket)
    # 3. try/except WebSocketDisconnect -> ws_manager.disconnect(user_id)
```

Security: authenticate the token (JWT) before accepting connection. Do **not** accept unauthenticated connections.

---

# 7. REST API Endpoints

Keep them simple & paginated.

* `GET /notifications?limit=20&cursor=<timestamp or id>` — list
* `GET /notifications/{id}` — single
* `POST /notifications/{id}/read` — mark single as read
* `POST /notifications/read-all` — mark all as read

Example FastAPI endpoints (dependency-injected DB session + current\_user):

```python
@router.get("/", response_model=List[NotificationOut])
async def list_notifications(current_user=Depends(get_current_user), limit: int = 20, cursor: Optional[int] = None):
    return await notification_service.get_user_notifications(current_user.id, limit, cursor)
```

Important: use cursor-based pagination (by `created_at` or `id`) to avoid offset scaling issues.

---

# 8. Client (Next.js) integration (high level)

* On initial page load / header mount:

  * Call `GET /notifications?limit=20` to fill dropdown and compute unread count.
* Connect to WebSocket at `wss://api/events2go/ws/notifications?token=<JWT>`:

  * `onmessage` push new notification to local state and increment unread count.
* Clicking a notification:

  * Call `POST /notifications/{id}/read` then update local state.
* When user logs out, close WebSocket.

Client security:

* Send a short-lived JWT; validate on server. For refresh, re-authenticate or reconnect.

---

# 9. Async workers (scale / heavy work)

For in-app only you may not need Celery immediately, but recommended for scale or when notification creation is triggered by slow operations:

* **Use Celery + Redis**:

  * Worker tasks: `enqueue_notification(notification_payload)` which writes DB and pushes to WebSocket manager via a redis/pubsub or by calling an internal HTTP endpoint.
* Alternative (small apps): use FastAPI `BackgroundTasks` to write DB & attempt WebSocket push.

**Important**: WebSocketManager lives in the FastAPI process. If you have multiple worker/process instances, use a **pub/sub** (Redis) channel to broadcast new notifications to all API instances; each instance picks and pushes to its connected sockets.

Pattern:

1. `create_notification` -> push record to DB.
2. Add a Redis `PUBLISH channel` message containing `{user_id, notification_id}`.
3. All FastAPI instances subscribe; if user is connected locally, deliver.

---

# 10. Multi-instance delivery (production)

If you run multiple FastAPI replicas (k8s, docker), you must broadcast notifications across instances:

* Use Redis pub/sub or a message broker to broadcast: when service creates notification it `PUBLISH`es a message. All app instances subscribed receive the message and call `ws_manager.send_to_user`.
* This guarantees that whichever instance holds the socket can forward it.

---

# 11. Edge cases & best practices

* Persist first, deliver second. Never rely only on socket delivery.
* Use cursor-based pagination and proper DB indexes.
* Limit per-user rate (throttle) to protect clients.
* Provide encryption/auth for WebSocket connections (wss + JWT).
* Provide `metadata` with a `url` or `route` so frontends can deep-link.
* Add `notification_preferences` later so users can opt out of types.
* Add retention policy (archive or delete > 6-12 months).
* Test reconnection logic on the client; show missed notifications using `/notifications` fetch when reconnecting.
* Atomicity: If using distributed brokers, make sure duplicate delivery is idempotent on client.

---

# 12. Example minimal code snippets

**Create & dispatch notification (service):**

```python
async def create_and_dispatch(db: AsyncSession, ws_manager: WebSocketManager, user_id, title, body, metadata=None):
    notif = Notification(user_id=user_id, title=title, body=body, metadata=metadata or {})
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    payload = NotificationOut.from_orm(notif).dict()
    # publish to redis channel (optional)
    await ws_manager.send_to_user(str(user_id), payload)
    return notif
```

**Client WebSocket (simplified):**

```ts
const ws = new WebSocket(`wss://api.events2go.com/ws/notifications?token=${jwt}`);
ws.onmessage = (ev) => {
  const notification = JSON.parse(ev.data);
  // add to UI state
};
```

---

# 13. Deployment & infra notes

* Use HTTPS & WSS (TLS).
* If behind a proxy (NGINX, Caddy), configure WebSocket pass-through.
* If scaling horizontally, use Redis pub/sub for delivering messages across app instances.
* Use a connection limit per user to prevent abuse.
* Use Alembic to manage DB migrations for the `notifications` table.

---

# 14. Monitoring & metrics

* Track number of notifications created/sec, delivery failures, unread counts distribution.
* Track WebSocket connection counts.
* Log notification create/send errors separately.

---

# 15. Testing

* Unit test `NotificationService.create_notification` (DB write + returns object).
* Integration test WebSocket flow: connect, create notification, assert message received.
* Test reconnection and fetch-on-reconnect.

---

# 16. Security checklist

* Authenticate and validate JWT for both REST & WebSocket endpoints.
* Limit message size. Sanitize metadata before sending.
* Rate-limit creation endpoints for potentially spammy actions.
* Ensure only authorized systems can create certain notification types (e.g., admin notifications).

---

# 17. Migration & setup (commands)

* Alembic migration to create `notifications` table.
* Environment variables (example):

```
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/events2go
REDIS_URL=redis://redis:6379/0
SECRET_KEY=...
JWT_ALGORITHM=HS256
```

---

# 18. Developer Prompt (paste to generate full code)

> I want a complete implementation for an **in-app notification module** for Events2Go using **FastAPI (async)**, **SQLAlchemy (async ORM)** and **PostgreSQL**. The requirements:
>
> * Persist notifications in a `notifications` table (schema with id, user\_id, actor\_id, title, body, metadata JSONB, channel, status, created\_at, updated\_at).
> * Provide async SQLAlchemy models and Alembic migration.
> * Implement a `NotificationService` that creates a notification in DB and dispatches it to connected WebSocket clients.
> * Implement a `WebSocketManager` to manage `user_id -> WebSocket` connections, authenticate connections using JWT (token passed as query param `?token=`), and safely send JSON messages.
> * Provide REST endpoints: `GET /notifications` (paginated cursor-based), `POST /notifications/{id}/read`, `POST /notifications/read-all`.
> * Demonstrate client behavior with a simple Next.js example hook to:
>
>   * Fetch latest 20 notifications,
>   * Connect to `wss://.../ws/notifications?token=...`,
>   * Receive notifications and update unread count,
>   * Mark notification as read.
> * Include instructions for running locally with Docker Compose (Postgres + Redis + FastAPI), and a small recommendation for scaling (Redis pub/sub for distributing notifications across instances).
> * Include unit tests for service and integration test for WebSocket delivery.
> * Keep code idiomatic, typed (Python typing), and include comments for each major part.
> * Provide example environment variables, alembic revision, and a readme explaining the flow.
>
> Output: full project skeleton with files: `models.py`, `schemas.py`, `service.py`, `websocket.py`, `routers/notifications.py`, `alembic` migration, `docker-compose.yml`, and a `nextjs` client snippet.

---

# 19. Next step suggestions

* If you want, I can now:

  1. Generate the **full FastAPI project files** (models, routers, service, websockets, Alembic migration) ready-to-run.
  2. Generate the **Next.js hook & bell component** with reconnection & token refresh logic.
  3. Produce a **Docker Compose** for local dev (FastAPI, Postgres, Redis).
     Pick which of the three you'd like me to produce first and I’ll generate it immediately.
