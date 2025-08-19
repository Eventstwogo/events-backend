from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.logging_config import get_logger
from shared.db.models.admin_users import AdminUser
from shared.db.models.new_events import (
    BookingStatus,
    NewEvent,
    NewEventBooking,
    NewEventBookingOrder,
    PaymentStatus,
)

logger = get_logger(__name__)


async def get_organizer_events_with_stats(
    db: AsyncSession, organizer_id: str
) -> dict:
    logger.info(f"Fetching events with stats for organizer={organizer_id}")

    # -------------------- Organizer Info -------------------- #
    organizer_query = select(AdminUser).where(AdminUser.user_id == organizer_id)
    organizer_result = await db.execute(organizer_query)
    organizer = organizer_result.scalar_one_or_none()

    if not organizer:
        return {"error": "Organizer not found"}

    # -------------------- Events with booking stats -------------------- #
    events_query = (
        select(
            NewEvent.event_id,
            NewEvent.event_title,
            NewEvent.card_image,
            func.coalesce(func.sum(NewEventBooking.num_seats), 0).label(
                "total_tickets"
            ),
            func.coalesce(func.sum(NewEventBooking.total_price), 0.0).label(
                "total_revenue"
            ),
        )
        .join(
            NewEventBookingOrder,
            NewEventBookingOrder.event_ref_id == NewEvent.event_id,
            isouter=True,
        )
        .join(
            NewEventBooking,
            NewEventBooking.order_id == NewEventBookingOrder.order_id,
            isouter=True,
        )
        .where(
            NewEvent.organizer_id == organizer_id,
            NewEventBookingOrder.booking_status == BookingStatus.APPROVED,
            NewEventBookingOrder.payment_status == PaymentStatus.COMPLETED,
        )
        .group_by(NewEvent.event_id, NewEvent.event_title, NewEvent.card_image)
    )

    events_result = await db.execute(events_query)

    events = [
        {
            "event_id": row.event_id,
            "event_title": row.event_title,
            "card_image": row.card_image,
            "total_tickets": int(row.total_tickets or 0),
            "total_revenue": round(float(row.total_revenue or 0.0), 2),
        }
        for row in events_result.fetchall()
    ]

    return {
        "organizer_id": organizer.user_id,
        "organizer_name": organizer.username or "Unknown Organizer",
        "events": events,
    }
