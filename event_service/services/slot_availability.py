"""
Slot Availability Management Service

This module handles updating slot availability when bookings are confirmed or cancelled.
It manages the JSONB slot_data to track booked seats and available capacity.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.services.slots import update_event_slot
from shared.db.models.events import (
    BookingStatus,
    Event,
    EventBooking,
    EventSlot,
)


async def get_slot_info_from_booking(
    db: AsyncSession, booking: EventBooking
) -> Tuple[Optional[EventSlot], Optional[str], Optional[str]]:
    """
    Extract slot information from a booking.

    Args:
        db: Database session
        booking: EventBooking object

    Returns:
        Tuple of (EventSlot, date_key, slot_key) or (None, None, None) if not found
    """
    try:
        # Get the event to find the slot_id
        event_query = select(Event).where(Event.event_id == booking.event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            return None, None, None

        # Get the event slot
        slot_query = select(EventSlot).where(EventSlot.slot_id == event.slot_id)
        slot_result = await db.execute(slot_query)
        event_slot = slot_result.scalar_one_or_none()

        if not event_slot:
            return None, None, None

        # Parse the slot string to find the matching slot in JSONB data
        # booking.slot format: "10:00 AM - 12:00 PM"
        slot_time = booking.slot
        booking_date = booking.booking_date.strftime("%Y-%m-%d")

        # Find the matching slot in the JSONB data
        slot_data = event_slot.slot_data or {}
        date_slots = slot_data.get(booking_date, {})

        slot_key = None
        for key, slot_info in date_slots.items():
            # Match by time range - handle various time formats
            start_time = slot_info.get("start_time", "")
            end_time = slot_info.get("end_time", "")

            # Create possible time format combinations
            possible_formats = [
                f"{start_time} - {end_time}",
                f"{start_time}:00 - {end_time}:00",
                f"{start_time} AM - {end_time} PM",
                f"{start_time} PM - {end_time} PM",
                f"{start_time} AM - {end_time} AM",
            ]

            if slot_time in possible_formats:
                slot_key = key
                break

        # If no exact match found, try to find by partial matching
        if not slot_key:
            for key, slot_info in date_slots.items():
                start_time = slot_info.get("start_time", "")
                end_time = slot_info.get("end_time", "")

                # Extract time parts for comparison
                if start_time in slot_time and end_time in slot_time:
                    slot_key = key
                    break

        return event_slot, booking_date, slot_key

    except Exception:
        return None, None, None


async def update_slot_availability_on_booking_confirm(
    db: AsyncSession, booking: EventBooking
) -> bool:
    """
    Update slot availability when a booking is confirmed (payment completed).
    Increases the booked_seats count for the specific slot.

    Args:
        db: Database session
        booking: EventBooking object that was confirmed

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        event_slot, date_key, slot_key = await get_slot_info_from_booking(
            db, booking
        )

        if not event_slot or not date_key or not slot_key:
            return False

        # Get current slot data
        current_slot_data = (
            event_slot.slot_data.copy() if event_slot.slot_data else {}
        )

        # Ensure the date and slot exist in the data
        if date_key not in current_slot_data:
            return False

        if slot_key not in current_slot_data[date_key]:
            return False

        # Update the booked_seats count
        slot_info = current_slot_data[date_key][slot_key]
        current_booked = slot_info.get("booked_seats", 0)
        slot_info["booked_seats"] = current_booked + booking.num_seats

        # Calculate available seats
        capacity = slot_info.get("capacity", 0)
        slot_info["available_seats"] = max(
            0, capacity - slot_info["booked_seats"]
        )

        # Update last_booking_update timestamp
        slot_info["last_booking_update"] = datetime.utcnow().isoformat()

        # Update the slot data in database
        updated_slot = await update_event_slot(
            db=db, slot_id=event_slot.slot_id, slot_data=current_slot_data
        )

        return updated_slot is not None

    except Exception as e:
        print(f"Error updating slot availability on booking confirm: {e}")
        return False


async def update_slot_availability_on_booking_cancel(
    db: AsyncSession, booking: EventBooking
) -> bool:
    """
    Update slot availability when a booking is cancelled.
    Decreases the booked_seats count for the specific slot.

    Args:
        db: Database session
        booking: EventBooking object that was cancelled

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        event_slot, date_key, slot_key = await get_slot_info_from_booking(
            db, booking
        )

        if not event_slot or not date_key or not slot_key:
            return False

        # Get current slot data
        current_slot_data = (
            event_slot.slot_data.copy() if event_slot.slot_data else {}
        )

        # Ensure the date and slot exist in the data
        if date_key not in current_slot_data:
            return False

        if slot_key not in current_slot_data[date_key]:
            return False

        # Update the booked_seats count
        slot_info = current_slot_data[date_key][slot_key]
        current_booked = slot_info.get("booked_seats", 0)

        # Only decrease if we have booked seats to decrease
        if current_booked >= booking.num_seats:
            slot_info["booked_seats"] = current_booked - booking.num_seats
        else:
            # This shouldn't happen, but handle gracefully
            slot_info["booked_seats"] = 0

        # Calculate available seats
        capacity = slot_info.get("capacity", 0)
        slot_info["available_seats"] = max(
            0, capacity - slot_info["booked_seats"]
        )

        # Update last_booking_update timestamp
        slot_info["last_booking_update"] = datetime.utcnow().isoformat()

        # Update the slot data in database
        updated_slot = await update_event_slot(
            db=db, slot_id=event_slot.slot_id, slot_data=current_slot_data
        )

        return updated_slot is not None

    except Exception as e:
        print(f"Error updating slot availability on booking cancel: {e}")
        return False


async def recalculate_slot_availability(
    db: AsyncSession, event_id: str, slot_time: str, booking_date: date
) -> bool:
    """
    Recalculate slot availability by counting all approved bookings.
    This is useful for data consistency checks or recovery.

    Args:
        db: Database session
        event_id: Event ID
        slot_time: Slot time string (e.g., "10:00 AM - 12:00 PM")
        booking_date: Date of the booking

    Returns:
        bool: True if recalculation was successful, False otherwise
    """
    try:
        # Get the event to find the slot_id
        event_query = select(Event).where(Event.event_id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            return False

        # Get the event slot
        slot_query = select(EventSlot).where(EventSlot.slot_id == event.slot_id)
        slot_result = await db.execute(slot_query)
        event_slot = slot_result.scalar_one_or_none()

        if not event_slot:
            return False

        # Count all approved bookings for this slot
        booking_query = select(EventBooking).where(
            EventBooking.event_id == event_id,
            EventBooking.slot == slot_time,
            EventBooking.booking_date == booking_date,
            EventBooking.booking_status == BookingStatus.APPROVED,
        )
        booking_result = await db.execute(booking_query)
        bookings = booking_result.scalars().all()

        total_booked_seats = sum(booking.num_seats for booking in bookings)

        # Update slot data
        current_slot_data = (
            event_slot.slot_data.copy() if event_slot.slot_data else {}
        )
        date_key = booking_date.strftime("%Y-%m-%d")

        if date_key not in current_slot_data:
            return False

        # Find the matching slot
        slot_key = None
        for key, slot_info in current_slot_data[date_key].items():
            start_time = slot_info.get("start_time", "")
            end_time = slot_info.get("end_time", "")

            # Create possible time format combinations
            possible_formats = [
                f"{start_time} - {end_time}",
                f"{start_time}:00 - {end_time}:00",
                f"{start_time} AM - {end_time} PM",
                f"{start_time} PM - {end_time} PM",
                f"{start_time} AM - {end_time} AM",
            ]

            if slot_time in possible_formats:
                slot_key = key
                break

        # If no exact match found, try partial matching
        if not slot_key:
            for key, slot_info in current_slot_data[date_key].items():
                start_time = slot_info.get("start_time", "")
                end_time = slot_info.get("end_time", "")

                if start_time in slot_time and end_time in slot_time:
                    slot_key = key
                    break

        if not slot_key:
            return False

        # Update the slot info
        slot_info = current_slot_data[date_key][slot_key]
        slot_info["booked_seats"] = total_booked_seats

        capacity = slot_info.get("capacity", 0)
        slot_info["available_seats"] = max(0, capacity - total_booked_seats)
        slot_info["last_recalculation"] = datetime.utcnow().isoformat()

        # Update the slot data in database
        updated_slot = await update_event_slot(
            db=db, slot_id=event_slot.slot_id, slot_data=current_slot_data
        )

        return updated_slot is not None

    except Exception as e:
        print(f"Error recalculating slot availability: {e}")
        return False


async def initialize_slot_booking_counters(
    db: AsyncSession, slot_id: str
) -> bool:
    """
    Initialize booking counters for all slots if they don't exist.
    This ensures all slots have booked_seats and available_seats fields.

    Args:
        db: Database session
        slot_id: Slot ID to initialize

    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Get the event slot
        slot_query = select(EventSlot).where(EventSlot.slot_id == slot_id)
        slot_result = await db.execute(slot_query)
        event_slot = slot_result.scalar_one_or_none()

        if not event_slot:
            return False

        # Get current slot data
        current_slot_data = (
            event_slot.slot_data.copy() if event_slot.slot_data else {}
        )

        # Initialize counters for all slots
        for date_key, date_slots in current_slot_data.items():
            for slot_key, slot_info in date_slots.items():
                if "booked_seats" not in slot_info:
                    slot_info["booked_seats"] = 0

                capacity = slot_info.get("capacity", 0)
                slot_info["available_seats"] = max(
                    0, capacity - slot_info.get("booked_seats", 0)
                )

                if "last_booking_update" not in slot_info:
                    slot_info["last_booking_update"] = (
                        datetime.utcnow().isoformat()
                    )

        # Update the slot data in database
        updated_slot = await update_event_slot(
            db=db, slot_id=event_slot.slot_id, slot_data=current_slot_data
        )

        return updated_slot is not None

    except Exception as e:
        print(f"Error initializing slot booking counters: {e}")
        return False
