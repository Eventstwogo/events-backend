from datetime import date, datetime, timedelta
from typing import Any, Dict, Tuple

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.core.api_response import api_response
from shared.db.models import (
    AdminUser,
    BusinessProfile,
    Event,
    EventBooking,
    OrganizerQuery,
    Role,
)
from shared.db.models.events import BookingStatus
from shared.utils.file_uploads import get_media_url


async def validate_user_access(user: AdminUser, db: AsyncSession):
    role_name = (
        await db.execute(
            select(Role.role_name)
            .join(AdminUser, Role.role_id == AdminUser.role_id)
            .where(AdminUser.user_id == user.user_id)
        )
    ).scalar_one_or_none()
    if not role_name or role_name.strip().lower() != "organizer":
        return api_response(
            403,
            "Access denied. This endpoint is restricted to organizers only.",
            None,
        )

    if not user.business_id:
        return api_response(
            400,
            "Business profile required. Please complete your business profile to access dashboard analytics.",
            None,
        )

    business_profile = (
        await db.execute(
            select(BusinessProfile).where(
                BusinessProfile.business_id == user.business_id
            )
        )
    ).scalar_one_or_none()

    if not business_profile:
        return api_response(
            400,
            "Business profile not found. Please complete your business profile to access dashboard analytics.",
            None,
        )

    return None


def calculate_date_range(period: str) -> Tuple[date, date]:
    end_date = date.today()
    period_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    start_date = end_date - timedelta(days=period_map.get(period, 30))
    return start_date, end_date


async def get_event_statistics(
    db: AsyncSession, user_id: str, today: date
) -> Dict[str, Any]:
    events = (
        (await db.execute(select(Event).where(Event.organizer_id == user_id)))
        .scalars()
        .all()
    )

    return {
        "total_events": len(events),
        "active_events": sum(1 for e in events if not e.event_status),
        "upcoming_events": sum(1 for e in events if e.start_date > today),
        "past_events": sum(1 for e in events if e.end_date < today),
    }


async def get_booking_statistics_and_revenue(
    db: AsyncSession, user_id: str, start_date: date, end_date: date
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bookings = (
        (
            await db.execute(
                select(EventBooking)
                .join(Event, EventBooking.event_id == Event.event_id)
                .where(
                    and_(
                        Event.organizer_id == user_id,
                        EventBooking.booking_date >= start_date,
                        EventBooking.booking_date <= end_date,
                    )
                )
            )
        )
        .scalars()
        .all()
    )

    total_bookings = len(bookings)
    approved = [
        b for b in bookings if b.booking_status == BookingStatus.APPROVED
    ]
    completed = [b for b in approved if b.payment_status == "COMPLETED"]
    pending = [
        b for b in bookings if b.booking_status == BookingStatus.PROCESSING
    ]
    cancelled = [
        b for b in bookings if b.booking_status == BookingStatus.CANCELLED
    ]

    total_revenue = sum(float(b.total_price) for b in completed)
    pending_revenue = sum(
        float(b.total_price)
        for b in bookings
        if (b.booking_status == BookingStatus.PROCESSING)
        or (
            b.booking_status == BookingStatus.APPROVED
            and b.payment_status != "COMPLETED"
        )
    )

    booking_stats = {
        "total_bookings": total_bookings,
        "approved_bookings": len(approved),
        "completed_bookings": len(completed),
        "pending_bookings": len(pending),
        "cancelled_bookings": len(cancelled),
        "approval_rate": round(
            (len(approved) / total_bookings * 100) if total_bookings else 0, 2
        ),
        "completion_rate": round(
            (len(completed) / len(approved) * 100) if approved else 0, 2
        ),
    }

    revenue_stats = {
        "total_revenue": round(total_revenue, 2),
        "pending_revenue": round(pending_revenue, 2),
        "average_booking_value": round(
            (total_revenue / len(completed)) if completed else 0, 2
        ),
    }

    return booking_stats, revenue_stats


async def get_query_statistics(
    db: AsyncSession, user_id: str, start_date: date, end_date: date
) -> Dict[str, Any]:
    queries = (
        (
            await db.execute(
                select(OrganizerQuery).where(
                    and_(
                        OrganizerQuery.receiver_user_id == user_id,
                        OrganizerQuery.created_at
                        >= datetime.combine(start_date, datetime.min.time()),
                        OrganizerQuery.created_at
                        <= datetime.combine(end_date, datetime.max.time()),
                    )
                )
            )
        )
        .scalars()
        .all()
    )

    resolved = [q for q in queries if q.query_status.value == "resolved"]
    pending = [q for q in queries if q.query_status.value == "open"]

    return {
        "total_queries": len(queries),
        "pending_queries": len(pending),
        "resolved_queries": len(resolved),
        "resolution_rate": round(
            (len(resolved) / len(queries) * 100) if queries else 0, 2
        ),
    }


async def get_recent_events(db: AsyncSession, user_id: str) -> list:
    events = (
        (
            await db.execute(
                select(Event)
                .options(selectinload(Event.category))
                .where(Event.organizer_id == user_id)
                .order_by(desc(Event.created_at))
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    return [
        {
            "event_id": e.event_id,
            "event_title": e.event_title,
            "category_name": e.category.category_name if e.category else None,
            "start_date": e.start_date,
            "event_status": e.event_status,
            "created_at": e.created_at,
            "card_image": get_media_url(e.card_image),
        }
        for e in events
    ]
