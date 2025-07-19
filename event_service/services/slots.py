from typing import List, Optional, Tuple

from sqlalchemy import and_, asc, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.logging_config import get_logger
from shared.db.models import Event, EventSlot

logger = get_logger(__name__)


async def check_slot_exists(db: AsyncSession, slot_id: int) -> EventSlot | None:
    """Check if slot exists by slot_id"""
    query = select(EventSlot).filter(EventSlot.slot_ids == slot_id)
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_slot_by_id(db: AsyncSession, slot_id: int) -> EventSlot | None:
    """Fetch slot by slot_id"""
    query = select(EventSlot).filter(EventSlot.slot_ids == slot_id)
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_slot_by_event_and_slot_id(
    db: AsyncSession, event_id: str, slot_id: int
) -> EventSlot | None:
    """Fetch slot by event_id and slot_id"""
    query = select(EventSlot).filter(
        and_(EventSlot.event_id == event_id, EventSlot.slot_ids == slot_id)
    )
    result = await db.execute(query)
    return result.scalars().first()


async def fetch_slots_by_event_id(
    db: AsyncSession,
    event_id: str,
    status: Optional[bool] = None,
    sort_by: str = "slot_order",
    sort_order: str = "asc",
) -> List[EventSlot]:
    """Fetch all slots for a specific event with optional filtering and sorting"""

    # Build base query
    query = select(EventSlot).filter(EventSlot.event_id == event_id)

    # Apply status filter if provided
    if status is not None:
        query = query.filter(EventSlot.slot_status == status)

    # Apply sorting
    sort_column = getattr(EventSlot, sort_by, EventSlot.slot_order)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Execute query
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_next_slot_order(db: AsyncSession, event_id: str) -> int:
    """Get the next available slot order for an event"""
    query = select(func.max(EventSlot.slot_order)).filter(
        EventSlot.event_id == event_id
    )
    result = await db.execute(query)
    max_order = result.scalar()
    return (max_order + 1) if max_order is not None else 0


async def check_slot_order_exists(
    db: AsyncSession,
    event_id: str,
    slot_order: int,
    exclude_slot_id: Optional[int] = None,
) -> bool:
    """Check if slot order already exists for an event (excluding specific slot if provided)"""
    query = select(EventSlot).filter(
        and_(EventSlot.event_id == event_id, EventSlot.slot_order == slot_order)
    )

    if exclude_slot_id is not None:
        query = query.filter(EventSlot.slot_ids != exclude_slot_id)

    result = await db.execute(query)
    return result.scalars().first() is not None


async def create_slot(
    db: AsyncSession,
    event_id: str,
    slot_order: int,
    slot_data: dict,
    slot_status: bool = False,
) -> EventSlot:
    """Create a new slot for an event"""

    new_slot = EventSlot(
        event_id=event_id,
        slot_order=slot_order,
        slot_data=slot_data,
        slot_status=slot_status,
    )

    db.add(new_slot)
    await db.commit()
    await db.refresh(new_slot)
    return new_slot


async def update_slot(
    db: AsyncSession, slot_id: int, update_data: dict
) -> EventSlot | None:
    """Update slot with provided data"""
    slot = await fetch_slot_by_id(db, slot_id)
    if not slot:
        return None

    # Update only provided fields
    for field, value in update_data.items():
        if hasattr(slot, field) and value is not None:
            setattr(slot, field, value)

    await db.commit()
    await db.refresh(slot)
    return slot


async def update_slot_status(
    db: AsyncSession, slot_id: int, status: bool
) -> EventSlot | None:
    """Update slot status"""
    slot = await fetch_slot_by_id(db, slot_id)
    if not slot:
        return None

    slot.slot_status = status
    await db.commit()
    await db.refresh(slot)
    return slot


async def delete_slot(db: AsyncSession, slot_id: int) -> bool:
    """Delete slot by slot_id"""
    slot = await fetch_slot_by_id(db, slot_id)
    if not slot:
        return False

    await db.delete(slot)
    await db.commit()
    return True


async def count_slots_by_event(db: AsyncSession, event_id: str) -> int:
    """Count total slots for an event"""
    query = select(func.count(EventSlot.slot_ids)).filter(
        EventSlot.event_id == event_id
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def reorder_slots(
    db: AsyncSession, event_id: str, slot_orders: List[Tuple[int, int]]
) -> bool:
    """
    Reorder multiple slots at once
    slot_orders: List of tuples (slot_id, new_order)
    """
    try:
        for slot_id, new_order in slot_orders:
            slot = await fetch_slot_by_id(db, slot_id)
            if slot and slot.event_id == event_id:
                slot.slot_order = new_order

        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error reordering slots: {e}")
        await db.rollback()
        return False


async def get_slot_statistics(db: AsyncSession, event_id: str) -> dict:
    """Get statistics about slots for an event"""

    # Total slots
    total_query = select(func.count(EventSlot.slot_ids)).filter(
        EventSlot.event_id == event_id
    )
    total_result = await db.execute(total_query)
    total_slots = total_result.scalar() or 0

    # Active slots
    active_query = select(func.count(EventSlot.slot_ids)).filter(
        and_(EventSlot.event_id == event_id, EventSlot.slot_status == True)
    )
    active_result = await db.execute(active_query)
    active_slots = active_result.scalar() or 0

    # Inactive slots
    inactive_slots = total_slots - active_slots

    return {
        "total_slots": total_slots,
        "active_slots": active_slots,
        "inactive_slots": inactive_slots,
        "event_id": event_id,
    }
