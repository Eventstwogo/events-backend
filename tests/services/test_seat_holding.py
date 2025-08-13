"""
Tests for seat holding functionality.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from event_service.services.seat_holding import (
    can_hold_seats,
    cleanup_expired_holds,
    get_held_seats_count,
    hold_seats,
    release_held_seats,
)
from shared.db.models import Event, EventSlot, EventStatus


@pytest.fixture
def mock_event_slot():
    """Create a mock EventSlot for testing."""
    slot = EventSlot()
    slot.id = 1
    slot.slot_id = "TEST123"
    slot.slot_data = {
        "2024-01-15": {
            "slot_1": {
                "start_time": "10:00",
                "end_time": "12:00",
                "capacity": 50,
                "price": 25.00,
            },
            "slot_2": {
                "start_time": "14:00",
                "end_time": "16:00",
                "capacity": 30,
                "price": 30.00,
            },
        }
    }
    slot.held_seats = {}
    slot.slot_status = False
    return slot


@pytest.fixture
def mock_event():
    """Create a mock Event for testing."""
    event = Event()
    event.event_id = "EVT001"
    event.slot_id = "TEST123"
    event.event_status = EventStatus.ACTIVE  # Active
    event.end_date = datetime.now(timezone.utc).date() + timedelta(days=30)
    return event


class TestSeatHolding:
    """Test cases for seat holding functionality."""

    @pytest.mark.asyncio
    async def test_can_hold_seats_success(self, mock_event_slot):
        """Test successful seat holding check."""
        can_hold, message = await can_hold_seats(
            mock_event_slot, "slot_1", "2024-01-15", 5
        )

        assert can_hold is True
        assert "Can hold 5 seats" in message

    @pytest.mark.asyncio
    async def test_can_hold_seats_insufficient_capacity(self, mock_event_slot):
        """Test seat holding check when insufficient capacity."""
        can_hold, message = await can_hold_seats(
            mock_event_slot,
            "slot_1",
            "2024-01-15",
            60,  # More than capacity of 50
        )

        assert can_hold is False
        assert "Cannot hold 60 seats" in message

    @pytest.mark.asyncio
    async def test_can_hold_seats_slot_not_found(self, mock_event_slot):
        """Test seat holding check when slot not found."""
        can_hold, message = await can_hold_seats(
            mock_event_slot, "slot_3", "2024-01-15", 5  # Non-existent slot
        )

        assert can_hold is False
        assert "Slot slot_3 not found" in message

    @pytest.mark.asyncio
    async def test_get_held_seats_count_empty(self, mock_event_slot):
        """Test getting held seats count when no seats are held."""
        count = await get_held_seats_count(
            mock_event_slot, "slot_1", "2024-01-15"
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_held_seats_count_with_holds(self, mock_event_slot):
        """Test getting held seats count when seats are held."""
        # Add some held seats
        mock_event_slot.held_seats = {
            "2024-01-15": {
                "slot_1": {
                    "BOOK001": {
                        "seats": 5,
                        "held_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "BOOK002": {
                        "seats": 3,
                        "held_at": datetime.now(timezone.utc).isoformat(),
                    },
                }
            }
        }

        count = await get_held_seats_count(
            mock_event_slot, "slot_1", "2024-01-15"
        )

        assert count == 8  # 5 + 3

    @pytest.mark.asyncio
    @patch("event_service.services.seat_holding.select")
    async def test_hold_seats_success(
        self, mock_select, mock_event, mock_event_slot
    ):
        """Test successful seat holding."""
        # Mock database session
        mock_db = AsyncMock()

        # Mock query results
        mock_event_result = AsyncMock()
        mock_event_result.scalar_one_or_none = AsyncMock(
            return_value=mock_event
        )

        mock_slot_result = AsyncMock()
        mock_slot_result.scalar_one_or_none = AsyncMock(
            return_value=mock_event_slot
        )

        mock_db.execute = AsyncMock(
            side_effect=[mock_event_result, mock_slot_result]
        )
        mock_db.commit = AsyncMock()

        # Mock cleanup function
        with patch(
            "event_service.services.seat_holding.cleanup_expired_holds"
        ) as mock_cleanup:
            mock_cleanup.return_value = 0

            # Mock can_hold_seats function
            with patch(
                "event_service.services.seat_holding.can_hold_seats"
            ) as mock_can_hold:
                mock_can_hold.return_value = (True, "Can hold 5 seats")

                success, message = await hold_seats(
                    mock_db, "EVT001", "BOOK001", "slot_1", "2024-01-15", 5
                )

                assert success is True
                assert "Successfully held 5 seats" in message
                assert mock_db.commit.called

    @pytest.mark.asyncio
    @patch("event_service.services.seat_holding.select")
    async def test_release_held_seats_success(
        self, mock_select, mock_event, mock_event_slot
    ):
        """Test successful seat release."""
        # Add held seats to mock
        mock_event_slot.held_seats = {
            "2024-01-15": {
                "slot_1": {
                    "BOOK001": {
                        "seats": 5,
                        "held_at": datetime.now(timezone.utc).isoformat(),
                    }
                }
            }
        }

        # Mock database session
        mock_db = AsyncMock()

        # Mock query results
        mock_event_result = AsyncMock()
        mock_event_result.scalar_one_or_none = AsyncMock(
            return_value=mock_event
        )

        mock_slot_result = AsyncMock()
        mock_slot_result.scalar_one_or_none = AsyncMock(
            return_value=mock_event_slot
        )

        mock_db.execute = AsyncMock(
            side_effect=[mock_event_result, mock_slot_result]
        )
        mock_db.commit = AsyncMock()

        success, message = await release_held_seats(
            mock_db, "EVT001", "BOOK001"
        )

        assert success is True
        assert "Released 5 held seats" in message
        assert mock_db.commit.called

    @pytest.mark.asyncio
    @patch("event_service.services.seat_holding.select")
    async def test_cleanup_expired_holds(self, mock_select, mock_event_slot):
        """Test cleanup of expired holds."""
        # Add expired and non-expired holds
        expired_time = (
            datetime.now(timezone.utc) - timedelta(minutes=20)
        ).isoformat()
        recent_time = datetime.now(timezone.utc).isoformat()

        mock_event_slot.held_seats = {
            "2024-01-15": {
                "slot_1": {
                    "BOOK001": {"seats": 5, "held_at": expired_time},  # Expired
                    "BOOK002": {
                        "seats": 3,
                        "held_at": recent_time,
                    },  # Not expired
                }
            }
        }

        # Mock database session
        mock_db = AsyncMock()

        # Mock query result
        mock_slot_result = AsyncMock()
        mock_slot_result.scalar_one_or_none = AsyncMock(
            return_value=mock_event_slot
        )

        mock_db.execute = AsyncMock(return_value=mock_slot_result)
        mock_db.commit = AsyncMock()

        cleaned_count = await cleanup_expired_holds(mock_db, 1)

        # Should have cleaned up 1 expired hold
        assert cleaned_count == 1

        # Check that only the non-expired hold remains
        assert (
            "BOOK001" not in mock_event_slot.held_seats["2024-01-15"]["slot_1"]
        )
        assert "BOOK002" in mock_event_slot.held_seats["2024-01-15"]["slot_1"]

        assert mock_db.commit.called


if __name__ == "__main__":
    pytest.main([__file__])
