"""
Event Slot Service Functions

This module contains service functions for managing event slots,
including creation, validation, and database operations.
"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import Event, EventSlot


async def check_event_exists_by_slot_id(
    db: AsyncSession, slot_id: str
) -> Optional[Event]:
    """
    Check if an event exists with the given slot_id.

    Args:
        db: Database session
        slot_id: The slot ID to check

    Returns:
        Event object if found, None otherwise
    """
    query = select(Event).filter(Event.slot_id == slot_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_slot_exists_for_event(
    db: AsyncSession, slot_id: str
) -> Optional[EventSlot]:
    """
    Check if any slot already exists for the given event.

    Args:
        db: Database session
        slot_id: The event's slot ID

    Returns:
        EventSlot object if found, None otherwise
    """
    query = select(EventSlot).filter(EventSlot.slot_id == slot_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_event_slot(db: AsyncSession, slot_id: str) -> Optional[EventSlot]:
    """
    Get the slot data for an event.

    Args:
        db: Database session
        slot_id: The event's slot ID

    Returns:
        EventSlot object if found, None otherwise
    """
    query = select(EventSlot).filter(EventSlot.slot_id == slot_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def count_event_slots(db: AsyncSession, slot_id: str) -> int:
    """
    Count the number of slots for a given event.

    Args:
        db: Database session
        slot_id: The event's slot ID

    Returns:
        Number of slots for the event
    """
    query = select(func.count(EventSlot.id)).filter(
        EventSlot.slot_id == slot_id
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def create_event_slot(
    db: AsyncSession, slot_id: str, slot_data: dict, slot_status: bool = False
) -> EventSlot:
    """
    Create a new event slot.

    Args:
        db: Database session
        slot_id: The event's slot ID
        slot_data: JSON data for the slot with nested date/slot structure
        slot_status: Status of the slot

    Returns:
        Created EventSlot object
    """
    new_slot = EventSlot(
        slot_id=slot_id, slot_data=slot_data, slot_status=slot_status
    )

    db.add(new_slot)
    await db.commit()
    await db.refresh(new_slot)

    return new_slot


async def update_event_slot(
    db: AsyncSession, slot_id: str, slot_data: dict, slot_status: bool = False
) -> Optional[EventSlot]:
    """
    Update an existing event slot.

    Args:
        db: Database session
        slot_id: The event's slot ID
        slot_data: Updated JSON data for the slot
        slot_status: Updated status of the slot (optional)

    Returns:
        Updated EventSlot object if found, None otherwise
    """
    query = select(EventSlot).filter(EventSlot.slot_id == slot_id)
    result = await db.execute(query)
    existing_slot = result.scalar_one_or_none()

    if not existing_slot:
        return None

    existing_slot.slot_data = slot_data
    if slot_status is not None:
        existing_slot.slot_status = slot_status

    await db.commit()
    await db.refresh(existing_slot)

    return existing_slot


async def get_slot_statistics(db: AsyncSession, event_id: str) -> dict:
    """
    Get slot statistics for an event.

    Args:
        db: Database session
        event_id: The event ID

    Returns:
        Dictionary containing slot statistics
    """
    # First get the event to get its slot_id
    event_query = select(Event).filter(Event.event_id == event_id)
    event_result = await db.execute(event_query)
    event = event_result.scalar_one_or_none()

    if not event:
        return {"total_slots": 0, "active_slots": 0, "inactive_slots": 0}

    # Get all slots for this event
    slots_query = select(EventSlot).filter(EventSlot.slot_id == event.slot_id)
    slots_result = await db.execute(slots_query)
    slots = slots_result.scalars().all()

    total_slots = len(slots)
    active_slots = sum(1 for slot in slots if slot.slot_status)
    inactive_slots = total_slots - active_slots

    return {
        "total_slots": total_slots,
        "active_slots": active_slots,
        "inactive_slots": inactive_slots,
    }
