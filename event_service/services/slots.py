"""
Event Slot Service Functions

This module contains service functions for managing event slots,
including creation, validation, and database operations.
"""

from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import Event, EventSlot


def deep_merge_slot_data(
    existing_data: Dict[str, Any], new_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deep merge slot data with proper JSONB update logic.

    Merges new dates with existing dates, and merges slots within each date.
    Preserves existing slots and adds new ones. When there are conflicts,
    merges the slot properties (combines both old and new properties).

    Args:
        existing_data: Current slot data from database
        new_data: New slot data from update request

    Returns:
        Merged slot data dictionary

    Raises:
        ValueError: If data types are invalid or merge operation fails
    """
    try:
        # Handle edge cases
        if not existing_data and not new_data:
            return {}

        if not existing_data:
            return new_data.copy() if isinstance(new_data, dict) else {}

        if not new_data:
            return (
                existing_data.copy() if isinstance(existing_data, dict) else {}
            )

        # Ensure both inputs are dictionaries
        if not isinstance(existing_data, dict):
            existing_data = {}

        if not isinstance(new_data, dict):
            return existing_data.copy()

        # Start with a deep copy of existing data
        merged_data = existing_data.copy()

        # Process each date in the new data
        for date_key, new_date_slots in new_data.items():
            if not isinstance(date_key, str):
                continue  # Skip invalid date keys

            if not isinstance(new_date_slots, dict):
                # If new date slots is not a dict, skip it
                continue

            # If date doesn't exist in existing data, add it entirely
            if date_key not in merged_data:
                merged_data[date_key] = new_date_slots.copy()
            else:
                # Date exists, merge slots within this date
                existing_date_slots = merged_data[date_key]
                if not isinstance(existing_date_slots, dict):
                    # If existing date data is not a dict, replace it
                    merged_data[date_key] = new_date_slots.copy()
                    continue

                # Merge slots for this date
                for slot_key, new_slot_details in new_date_slots.items():
                    if not isinstance(slot_key, str):
                        continue  # Skip invalid slot keys

                    if not isinstance(new_slot_details, dict):
                        # If new slot details is not a dict, just set it
                        existing_date_slots[slot_key] = new_slot_details
                        continue

                    # If slot doesn't exist, add it
                    if slot_key not in existing_date_slots:
                        existing_date_slots[slot_key] = new_slot_details.copy()
                    else:
                        # Slot exists, merge properties
                        existing_slot_details = existing_date_slots[slot_key]
                        if isinstance(existing_slot_details, dict):
                            # Deep merge slot properties
                            merged_slot = existing_slot_details.copy()
                            merged_slot.update(new_slot_details)
                            existing_date_slots[slot_key] = merged_slot
                        else:
                            # If existing slot details is not a dict, replace it
                            existing_date_slots[slot_key] = (
                                new_slot_details.copy()
                            )

        return merged_data

    except Exception as e:
        # Log the error and return existing data as fallback
        print(f"Error in deep_merge_slot_data: {str(e)}")
        return existing_data.copy() if isinstance(existing_data, dict) else {}


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
    db: AsyncSession,
    slot_id: str,
    slot_data: dict,
    slot_status: Optional[bool] = None,
) -> Optional[EventSlot]:
    """
    Update an existing event slot with proper JSONB merge logic.

    This function performs a deep merge of the new slot data with existing data:
    - Merges new dates with existing dates
    - Merges slots within each date (preserves existing slots, adds new ones)
    - Merges slot properties when there are conflicts

    Args:
        db: Database session
        slot_id: The event's slot ID
        slot_data: New JSON data to merge with existing slot data
        slot_status: Updated status of the slot (optional, None means don't update)

    Returns:
        Updated EventSlot object if found, None otherwise
    """
    query = select(EventSlot).filter(EventSlot.slot_id == slot_id)
    result = await db.execute(query)
    existing_slot = result.scalar_one_or_none()

    if not existing_slot:
        return None

    # Perform deep merge of slot data
    merged_slot_data = deep_merge_slot_data(
        existing_slot.slot_data or {}, slot_data
    )
    existing_slot.slot_data = merged_slot_data

    # Update slot status only if explicitly provided
    if slot_status is not None:
        existing_slot.slot_status = slot_status

    await db.commit()
    await db.refresh(existing_slot)

    return existing_slot


async def delete_event_slot(db: AsyncSession, slot_id: str) -> bool:
    """
    Delete an event slot.

    Args:
        db: Database session
        slot_id: The event's slot ID

    Returns:
        True if deleted successfully, False if not found
    """
    query = select(EventSlot).filter(EventSlot.slot_id == slot_id)
    result = await db.execute(query)
    existing_slot = result.scalar_one_or_none()

    if not existing_slot:
        return False

    await db.delete(existing_slot)
    await db.commit()
    return True


async def toggle_slot_status(
    db: AsyncSession, slot_id: str
) -> Optional[EventSlot]:
    """
    Toggle the status of an event slot.

    Args:
        db: Database session
        slot_id: The event's slot ID

    Returns:
        Updated EventSlot object if found, None otherwise
    """
    query = select(EventSlot).filter(EventSlot.slot_id == slot_id)
    result = await db.execute(query)
    existing_slot = result.scalar_one_or_none()

    if not existing_slot:
        return None

    existing_slot.slot_status = not existing_slot.slot_status
    await db.commit()
    await db.refresh(existing_slot)
    return existing_slot


async def get_slots_by_event_id(
    db: AsyncSession, event_id: str
) -> list[EventSlot]:
    """
    Get all slots for a specific event.

    Args:
        db: Database session
        event_id: The event ID

    Returns:
        List of EventSlot objects
    """
    # First get the event to get its slot_id
    event_query = select(Event.slot_id).filter(Event.event_id == event_id)
    event_result = await db.execute(event_query)
    slot_id = event_result.scalar_one_or_none()

    if not slot_id:
        return []

    # Get all slots for this event using the slot_id
    slots_query = (
        select(EventSlot)
        .filter(EventSlot.slot_id == slot_id)
        .order_by(EventSlot.created_at.desc())
    )
    slots_result = await db.execute(slots_query)
    return list(slots_result.scalars().all())


async def get_slots_with_pagination(
    db: AsyncSession,
    page: int = 1,
    limit: int = 10,
    status: Optional[bool] = None,
    event_id: Optional[str] = None,
) -> tuple[list[EventSlot], int]:
    """
    Get slots with pagination and optional filtering.

    Args:
        db: Database session
        page: Page number (1-based)
        limit: Number of items per page
        status: Optional status filter (True/False)
        event_id: Optional event ID filter

    Returns:
        Tuple of (slots_list, total_count)
    """
    # Calculate offset
    offset = (page - 1) * limit

    # Build base query
    query = select(EventSlot)
    count_query = select(func.count(EventSlot.id))

    # Apply filters
    if status is not None:
        query = query.filter(EventSlot.slot_status == status)
        count_query = count_query.filter(EventSlot.slot_status == status)

    if event_id:
        # Get event's slot_id first
        event_query = select(Event.slot_id).filter(Event.event_id == event_id)
        event_result = await db.execute(event_query)
        slot_id = event_result.scalar_one_or_none()

        if slot_id:
            query = query.filter(EventSlot.slot_id == slot_id)
            count_query = count_query.filter(EventSlot.slot_id == slot_id)
        else:
            return [], 0

    # Apply pagination and ordering
    query = (
        query.order_by(EventSlot.created_at.desc()).offset(offset).limit(limit)
    )

    # Execute queries
    slots_result = await db.execute(query)
    count_result = await db.execute(count_query)

    slots = list(slots_result.scalars().all())
    total_count = count_result.scalar() or 0

    return slots, total_count


async def get_slot_availability_info(db: AsyncSession, slot_id: str) -> dict:
    """
    Get availability information for a slot.

    Args:
        db: Database session
        slot_id: The event's slot ID

    Returns:
        Dictionary containing availability information
    """
    slot = await get_event_slot(db, slot_id)
    if not slot:
        return {"available": False, "reason": "Slot not found"}

    if not slot.slot_status:
        return {"available": False, "reason": "Slot is inactive"}

    # Calculate availability based on slot_data
    availability_info = {
        "available": True,
        "slot_status": slot.slot_status,
        "total_dates": len(slot.slot_data),
        "dates_info": {},
    }

    total_capacity = 0
    total_individual_slots = 0

    for date_key, date_slots in slot.slot_data.items():
        date_capacity = 0
        individual_slots_count = len(date_slots)

        for slot_key, slot_details in date_slots.items():
            capacity = slot_details.get("capacity", 0)
            date_capacity += capacity

        availability_info["dates_info"][date_key] = {
            "individual_slots": individual_slots_count,
            "total_capacity": date_capacity,
            "slots": date_slots,
        }

        total_capacity += date_capacity
        total_individual_slots += individual_slots_count

    availability_info["total_capacity"] = total_capacity
    availability_info["total_individual_slots"] = total_individual_slots

    return availability_info


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
        return {
            "event_id": event_id,
            "total_slots": 0,
            "active_slots": 0,
            "inactive_slots": 0,
            "total_dates": 0,
            "total_individual_slots": 0,
            "total_capacity": 0,
            "total_revenue_potential": 0.0,
            "average_capacity_per_slot": 0.0,
            "average_price_per_slot": 0.0,
        }

    # Get all slots for this event using the correct relationship
    # Use selectinload or joinedload for better performance if needed
    slots_query = (
        select(EventSlot)
        .filter(EventSlot.slot_id == event.slot_id)
        .order_by(EventSlot.created_at.desc())
    )
    slots_result = await db.execute(slots_query)
    slots = list(slots_result.scalars().all())

    total_slots = len(slots)
    active_slots = sum(1 for slot in slots if slot.slot_status)
    inactive_slots = total_slots - active_slots

    # Calculate detailed statistics
    total_dates = 0
    total_individual_slots = 0
    total_capacity = 0
    total_revenue_potential = 0.0

    for slot in slots:
        if slot.slot_data and isinstance(slot.slot_data, dict):
            total_dates += len(slot.slot_data)

            for date_key, date_slots in slot.slot_data.items():
                if isinstance(date_slots, dict):
                    total_individual_slots += len(date_slots)

                    for slot_key, slot_details in date_slots.items():
                        if isinstance(slot_details, dict):
                            capacity = slot_details.get("capacity", 0)
                            price = slot_details.get("price", 0.0)

                            # Ensure capacity and price are numeric
                            try:
                                capacity = int(capacity) if capacity else 0
                                price = float(price) if price else 0.0
                            except (ValueError, TypeError):
                                capacity = 0
                                price = 0.0

                            total_capacity += capacity
                            total_revenue_potential += capacity * price

    return {
        "event_id": event_id,
        "total_slots": total_slots,
        "active_slots": active_slots,
        "inactive_slots": inactive_slots,
        "total_dates": total_dates,
        "total_individual_slots": total_individual_slots,
        "total_capacity": total_capacity,
        "total_revenue_potential": round(total_revenue_potential, 2),
        "average_capacity_per_slot": (
            round(total_capacity / total_individual_slots, 2)
            if total_individual_slots > 0
            else 0.0
        ),
        "average_price_per_slot": (
            round(total_revenue_potential / total_capacity, 2)
            if total_capacity > 0
            else 0.0
        ),
    }


async def get_slot_date_details(
    db: AsyncSession, slot_id: str, date_str: str
) -> Optional[dict]:
    """
    Get detailed information for a specific slot and date.

    Args:
        db: Database session
        slot_id: The event's slot ID
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Dictionary containing slot date details or None if not found
    """
    # Get the event and slot information
    event = await check_event_exists_by_slot_id(db, slot_id)
    if not event:
        return None

    slot = await get_event_slot(db, slot_id)
    if not slot:
        return None

    # Check if the date exists in slot_data
    if not slot.slot_data or date_str not in slot.slot_data:
        return None

    date_slots = slot.slot_data[date_str]
    if not isinstance(date_slots, dict):
        return None

    # Calculate statistics for this date
    slots_count = len(date_slots)
    total_capacity = 0
    total_revenue_potential = 0.0

    for slot_key, slot_details in date_slots.items():
        if isinstance(slot_details, dict):
            capacity = slot_details.get("capacity", 0)
            price = slot_details.get("price", 0.0)

            # Ensure capacity and price are numeric
            try:
                capacity = int(capacity) if capacity else 0
                price = float(price) if price else 0.0
            except (ValueError, TypeError):
                capacity = 0
                price = 0.0

            total_capacity += capacity
            total_revenue_potential += capacity * price

    return {
        "slot_id": slot_id,
        "event_date": date_str,
        "slots_count": slots_count,
        "slots_data": date_slots,
        "event_title": event.event_title,
        "event_id": event.event_id,
        "event_status": event.event_status,
        "slot_status": slot.slot_status,
        "total_capacity": total_capacity,
        "total_revenue_potential": round(total_revenue_potential, 2),
        "event_location": event.location,
        "is_online": event.is_online,
        "start_date": event.start_date,
        "end_date": event.end_date,
    }


async def get_detailed_slot_analytics(db: AsyncSession, slot_id: str) -> dict:
    """
    Get detailed analytics for a specific slot.

    Args:
        db: Database session
        slot_id: The event's slot ID

    Returns:
        Dictionary containing detailed slot analytics
    """
    slot = await get_event_slot(db, slot_id)
    if not slot:
        return {"error": "Slot not found"}

    analytics = {
        "slot_id": slot_id,
        "slot_status": slot.slot_status,
        "created_at": slot.created_at,
        "updated_at": slot.updated_at,
        "dates_analysis": {},
        "summary": {
            "total_dates": 0,
            "total_individual_slots": 0,
            "total_capacity": 0,
            "total_revenue_potential": 0.0,
            "price_range": {"min": float("inf"), "max": 0},
            "capacity_range": {"min": float("inf"), "max": 0},
            "duration_range": {"min": float("inf"), "max": 0},
        },
    }

    if not slot.slot_data:
        return analytics

    total_capacity = 0
    total_revenue = 0.0
    all_prices = []
    all_capacities = []
    all_durations = []

    for date_key, date_slots in slot.slot_data.items():
        date_analysis = {
            "date": date_key,
            "individual_slots_count": len(date_slots),
            "date_total_capacity": 0,
            "date_total_revenue": 0.0,
            "slots_details": {},
        }

        for slot_key, slot_details in date_slots.items():
            capacity = slot_details.get("capacity", 0)
            price = slot_details.get("price", 0.0)
            duration = slot_details.get("duration", 0)

            slot_revenue = capacity * price

            date_analysis["date_total_capacity"] += capacity
            date_analysis["date_total_revenue"] += slot_revenue
            date_analysis["slots_details"][slot_key] = {
                "capacity": capacity,
                "price": price,
                "duration": duration,
                "revenue_potential": slot_revenue,
                "start_time": slot_details.get("start_time"),
                "end_time": slot_details.get("end_time"),
            }

            # Collect data for summary statistics
            if price > 0:
                all_prices.append(price)
            if capacity > 0:
                all_capacities.append(capacity)
            if duration > 0:
                all_durations.append(duration)

        analytics["dates_analysis"][date_key] = date_analysis
        total_capacity += date_analysis["date_total_capacity"]
        total_revenue += date_analysis["date_total_revenue"]

    # Update summary
    analytics["summary"]["total_dates"] = len(slot.slot_data)
    analytics["summary"]["total_individual_slots"] = sum(
        len(date_slots) for date_slots in slot.slot_data.values()
    )
    analytics["summary"]["total_capacity"] = total_capacity
    analytics["summary"]["total_revenue_potential"] = round(total_revenue, 2)

    # Price range
    if all_prices:
        analytics["summary"]["price_range"]["min"] = min(all_prices)
        analytics["summary"]["price_range"]["max"] = max(all_prices)
        analytics["summary"]["average_price"] = round(
            sum(all_prices) / len(all_prices), 2
        )
    else:
        analytics["summary"]["price_range"] = {"min": 0, "max": 0}
        analytics["summary"]["average_price"] = 0

    # Capacity range
    if all_capacities:
        analytics["summary"]["capacity_range"]["min"] = min(all_capacities)
        analytics["summary"]["capacity_range"]["max"] = max(all_capacities)
        analytics["summary"]["average_capacity"] = round(
            sum(all_capacities) / len(all_capacities), 2
        )
    else:
        analytics["summary"]["capacity_range"] = {"min": 0, "max": 0}
        analytics["summary"]["average_capacity"] = 0

    # Duration range
    if all_durations:
        analytics["summary"]["duration_range"]["min"] = min(all_durations)
        analytics["summary"]["duration_range"]["max"] = max(all_durations)
        analytics["summary"]["average_duration"] = round(
            sum(all_durations) / len(all_durations), 2
        )
    else:
        analytics["summary"]["duration_range"] = {"min": 0, "max": 0}
        analytics["summary"]["average_duration"] = 0

    return analytics
