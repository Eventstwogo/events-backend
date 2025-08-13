"""
Seat holding service for managing temporary seat reservations during booking process.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.events import Event, EventSlot

logger = logging.getLogger(__name__)

# Constants
SEAT_HOLD_DURATION_MINUTES = 15


async def hold_seats(
    db: AsyncSession,
    event_id: str,
    booking_id: str,
    slot_key: str,
    booking_date: str,
    num_seats: int,
) -> Tuple[bool, str]:
    """
    Hold seats for a specific booking temporarily.

    Args:
        db: Database session
        event_id: Event ID
        booking_id: Booking ID to associate with held seats
        slot_key: Slot identifier (e.g., "slot_1")
        booking_date: Date string (e.g., "2024-01-15")
        num_seats: Number of seats to hold

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get event and its slot data
        event_query = select(Event).where(Event.event_id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            return False, "Event not found"

        # Get event slot
        slot_query = select(EventSlot).where(EventSlot.slot_id == event.slot_id)
        slot_result = await db.execute(slot_query)
        event_slot = slot_result.scalar_one_or_none()

        if not event_slot:
            return False, "Event slot not found"

        # Clean up expired holds first
        await cleanup_expired_holds(db, event_slot.id)

        # Check if we can hold the requested seats
        can_hold, message = await can_hold_seats(
            event_slot, slot_key, booking_date, num_seats
        )

        if not can_hold:
            return False, message

        # Hold the seats
        held_at = datetime.now(timezone.utc).isoformat()

        # Initialize held_seats if None
        if event_slot.held_seats is None:
            event_slot.held_seats = {}

        # Ensure date exists in held_seats
        if booking_date not in event_slot.held_seats:
            event_slot.held_seats[booking_date] = {}

        # Ensure slot_key exists in date
        if slot_key not in event_slot.held_seats[booking_date]:
            event_slot.held_seats[booking_date][slot_key] = {}

        # Add the hold
        event_slot.held_seats[booking_date][slot_key][booking_id] = {
            "seats": num_seats,
            "held_at": held_at,
        }

        # Update the database
        await db.commit()

        logger.info(
            f"Held {num_seats} seats for booking {booking_id} "
            f"in event {event_id}, slot {slot_key}, date {booking_date}"
        )

        return True, f"Successfully held {num_seats} seats"

    except Exception as e:
        await db.rollback()
        logger.error(f"Error holding seats: {str(e)}")
        return False, f"Failed to hold seats: {str(e)}"


async def release_held_seats(
    db: AsyncSession,
    event_id: str,
    booking_id: str,
) -> Tuple[bool, str]:
    """
    Release held seats for a specific booking.

    Args:
        db: Database session
        event_id: Event ID
        booking_id: Booking ID to release seats for

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get event and its slot data
        event_query = select(Event).where(Event.event_id == event_id)
        event_result = await db.execute(event_query)
        event = event_result.scalar_one_or_none()

        if not event:
            return False, "Event not found"

        # Get event slot
        slot_query = select(EventSlot).where(EventSlot.slot_id == event.slot_id)
        slot_result = await db.execute(slot_query)
        event_slot = slot_result.scalar_one_or_none()

        if not event_slot or not event_slot.held_seats:
            return True, "No held seats found"

        # Find and remove the booking's held seats
        seats_released = 0
        for date_key, date_slots in event_slot.held_seats.items():
            for slot_key, slot_holds in date_slots.items():
                if booking_id in slot_holds:
                    seats_released += slot_holds[booking_id].get("seats", 0)
                    del slot_holds[booking_id]

                    # Clean up empty structures
                    if not slot_holds:
                        del date_slots[slot_key]
                    if not date_slots:
                        del event_slot.held_seats[date_key]

        if seats_released > 0:
            await db.commit()
            logger.info(
                f"Released {seats_released} held seats for booking {booking_id} "
                f"in event {event_id}"
            )
            return True, f"Released {seats_released} held seats"
        else:
            return True, "No held seats found for this booking"

    except Exception as e:
        await db.rollback()
        logger.error(f"Error releasing held seats: {str(e)}")
        return False, f"Failed to release held seats: {str(e)}"


async def can_hold_seats(
    event_slot: EventSlot,
    slot_key: str,
    booking_date: str,
    num_seats: int,
) -> Tuple[bool, str]:
    """
    Check if seats can be held for a specific slot and date.

    Args:
        event_slot: EventSlot object
        slot_key: Slot identifier (e.g., "slot_1")
        booking_date: Date string (e.g., "2024-01-15")
        num_seats: Number of seats to hold

    Returns:
        Tuple of (can_hold: bool, message: str)
    """
    try:
        # Find slot capacity from slot_data
        slot_capacity = None
        slot_data = event_slot.slot_data or {}

        for date_key, date_slots in slot_data.items():
            if date_key == booking_date and isinstance(date_slots, dict):
                if slot_key in date_slots:
                    slot_info = date_slots[slot_key]
                    slot_capacity = slot_info.get("capacity", 0)
                    break

        if slot_capacity is None:
            return False, f"Slot {slot_key} not found for date {booking_date}"

        # Calculate currently held seats for this slot and date
        held_seats_count = 0
        if (
            event_slot.held_seats
            and booking_date in event_slot.held_seats
            and slot_key in event_slot.held_seats[booking_date]
        ):
            for hold_info in event_slot.held_seats[booking_date][
                slot_key
            ].values():
                held_seats_count += hold_info.get("seats", 0)

        # Check if we can hold the requested seats
        available_for_hold = slot_capacity - held_seats_count

        if available_for_hold < num_seats:
            return (
                False,
                f"Cannot hold {num_seats} seats. Only {available_for_hold} seats available for holding.",
            )

        return True, f"Can hold {num_seats} seats"

    except Exception as e:
        logger.error(f"Error checking if seats can be held: {str(e)}")
        return False, f"Error checking seat availability: {str(e)}"


async def cleanup_expired_holds(db: AsyncSession, event_slot_id: int) -> int:
    """
    Clean up expired seat holds (older than SEAT_HOLD_DURATION_MINUTES).

    Args:
        db: Database session
        event_slot_id: EventSlot ID to clean up

    Returns:
        Number of expired holds cleaned up
    """
    try:
        # Get the event slot
        slot_query = select(EventSlot).where(EventSlot.id == event_slot_id)
        slot_result = await db.execute(slot_query)
        event_slot = slot_result.scalar_one_or_none()

        if not event_slot or not event_slot.held_seats:
            return 0

        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=SEAT_HOLD_DURATION_MINUTES
        )
        expired_holds = 0

        # Check each held seat for expiration
        for date_key, date_slots in list(event_slot.held_seats.items()):
            for slot_key, slot_holds in list(date_slots.items()):
                for booking_id, hold_info in list(slot_holds.items()):
                    held_at_str = hold_info.get("held_at")
                    if held_at_str:
                        try:
                            held_at = datetime.fromisoformat(
                                held_at_str.replace("Z", "+00:00")
                            )
                            if held_at < cutoff_time:
                                # This hold has expired
                                del slot_holds[booking_id]
                                expired_holds += 1
                                logger.info(
                                    f"Expired hold cleaned up: booking {booking_id}, "
                                    f"held at {held_at_str}"
                                )
                        except (ValueError, TypeError) as e:
                            # Invalid timestamp, remove it
                            del slot_holds[booking_id]
                            expired_holds += 1
                            logger.warning(
                                f"Invalid hold timestamp removed: {held_at_str}, error: {e}"
                            )

                # Clean up empty structures
                if not slot_holds:
                    del date_slots[slot_key]
            if not date_slots:
                del event_slot.held_seats[date_key]

        if expired_holds > 0:
            await db.commit()
            logger.info(f"Cleaned up {expired_holds} expired seat holds")

        return expired_holds

    except Exception as e:
        await db.rollback()
        logger.error(f"Error cleaning up expired holds: {str(e)}")
        return 0


async def get_held_seats_count(
    event_slot: EventSlot,
    slot_key: str,
    booking_date: str,
) -> int:
    """
    Get the total number of currently held seats for a specific slot and date.

    Args:
        event_slot: EventSlot object
        slot_key: Slot identifier (e.g., "slot_1")
        booking_date: Date string (e.g., "2024-01-15")

    Returns:
        Total number of held seats
    """
    try:
        if (
            not event_slot.held_seats
            or booking_date not in event_slot.held_seats
            or slot_key not in event_slot.held_seats[booking_date]
        ):
            return 0

        total_held = 0
        for hold_info in event_slot.held_seats[booking_date][slot_key].values():
            total_held += hold_info.get("seats", 0)

        return total_held

    except Exception as e:
        logger.error(f"Error getting held seats count: {str(e)}")
        return 0


async def cleanup_all_expired_holds(db: AsyncSession) -> int:
    """
    Clean up expired holds across all event slots.
    This function can be called periodically by a background task.

    Args:
        db: Database session

    Returns:
        Total number of expired holds cleaned up
    """
    try:
        # Get all event slots that have held_seats data
        slots_query = select(EventSlot).where(EventSlot.held_seats.isnot(None))
        slots_result = await db.execute(slots_query)
        event_slots = slots_result.scalars().all()

        total_cleaned = 0
        for event_slot in event_slots:
            cleaned = await cleanup_expired_holds(db, event_slot.id)
            total_cleaned += cleaned

        logger.info(
            f"Global cleanup: removed {total_cleaned} expired seat holds"
        )
        return total_cleaned

    except Exception as e:
        logger.error(f"Error in global expired holds cleanup: {str(e)}")
        return 0
