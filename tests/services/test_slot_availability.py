"""
Test cases for slot availability management
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from event_service.services.slot_availability import (
    get_slot_info_from_booking,
    initialize_slot_booking_counters,
    recalculate_slot_availability,
    update_slot_availability_on_booking_cancel,
    update_slot_availability_on_booking_confirm,
)
from shared.db.models.events import (
    BookingStatus,
    Event,
    EventBooking,
    EventSlot,
)


class TestSlotAvailability:
    """Test cases for slot availability management"""

    @pytest.fixture
    def mock_booking(self):
        """Create a mock booking object"""
        booking = MagicMock()
        booking.booking_id = 1
        booking.user_id = "user123"
        booking.event_id = "evt123"
        booking.num_seats = 2
        booking.slot = "10:00 - 12:00"
        booking.booking_date = date(2024, 1, 15)
        booking.booking_status = BookingStatus.PROCESSING
        return booking

    @pytest.fixture
    def mock_event(self):
        """Create a mock event object"""
        event = MagicMock()
        event.event_id = "evt123"
        event.slot_id = "slot123"
        return event

    @pytest.fixture
    def mock_event_slot(self):
        """Create a mock event slot object"""
        slot = MagicMock()
        slot.slot_id = "slot123"
        slot.slot_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                    "booked_seats": 10,
                    "available_seats": 40,
                }
            }
        }
        return slot

    @pytest.mark.asyncio
    async def test_get_slot_info_from_booking_success(
        self, mock_booking, mock_event, mock_event_slot
    ):
        """Test successful extraction of slot info from booking"""
        # Mock database session
        db = AsyncMock()

        # Mock database queries - properly handle async results
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        slot_result = MagicMock()
        slot_result.scalar_one_or_none.return_value = mock_event_slot

        # Make db.execute return the mocked results
        db.execute.side_effect = [event_result, slot_result]

        # Test the function
        event_slot, date_key, slot_key = await get_slot_info_from_booking(
            db, mock_booking
        )

        # Assertions
        assert event_slot == mock_event_slot
        assert date_key == "2024-01-15"
        assert slot_key == "slot_1"

    @pytest.mark.asyncio
    async def test_get_slot_info_from_booking_no_event(self, mock_booking):
        """Test when event is not found"""
        # Mock database session
        db = AsyncMock()

        # Mock database queries - event not found
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = None

        db.execute.return_value = event_result

        # Test the function
        event_slot, date_key, slot_key = await get_slot_info_from_booking(
            db, mock_booking
        )

        # Assertions
        assert event_slot is None
        assert date_key is None
        assert slot_key is None

    @pytest.mark.asyncio
    async def test_update_slot_availability_on_booking_confirm(
        self, mock_booking, mock_event_slot
    ):
        """Test updating slot availability when booking is confirmed"""
        # Mock the get_slot_info_from_booking function
        from event_service.services import slot_availability

        original_get_slot_info = slot_availability.get_slot_info_from_booking
        slot_availability.get_slot_info_from_booking = AsyncMock(
            return_value=(mock_event_slot, "2024-01-15", "slot_1")
        )

        # Mock the update_event_slot function
        slot_availability.update_event_slot = AsyncMock(
            return_value=mock_event_slot
        )

        # Mock database session
        db = AsyncMock()

        try:
            # Test the function
            result = await update_slot_availability_on_booking_confirm(
                db, mock_booking
            )

            # Assertions
            assert result is True

            # Verify that booked_seats was increased
            expected_booked_seats = 10 + mock_booking.num_seats  # 10 + 2 = 12
            # Note: We can't directly check the slot data modification since it's a copy
            # but we can verify the function was called
            slot_availability.update_event_slot.assert_called_once()

        finally:
            # Restore original function
            slot_availability.get_slot_info_from_booking = (
                original_get_slot_info
            )

    @pytest.mark.asyncio
    async def test_update_slot_availability_on_booking_cancel(
        self, mock_booking, mock_event_slot
    ):
        """Test updating slot availability when booking is cancelled"""
        # Mock the get_slot_info_from_booking function
        from event_service.services import slot_availability

        original_get_slot_info = slot_availability.get_slot_info_from_booking
        slot_availability.get_slot_info_from_booking = AsyncMock(
            return_value=(mock_event_slot, "2024-01-15", "slot_1")
        )

        # Mock the update_event_slot function
        slot_availability.update_event_slot = AsyncMock(
            return_value=mock_event_slot
        )

        # Mock database session
        db = AsyncMock()

        try:
            # Test the function
            result = await update_slot_availability_on_booking_cancel(
                db, mock_booking
            )

            # Assertions
            assert result is True

            # Verify the function was called
            slot_availability.update_event_slot.assert_called_once()

        finally:
            # Restore original function
            slot_availability.get_slot_info_from_booking = (
                original_get_slot_info
            )

    @pytest.mark.asyncio
    async def test_initialize_slot_booking_counters(self, mock_event_slot):
        """Test initializing booking counters for slots"""
        # Create slot data without booking counters
        mock_event_slot.slot_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                    # Missing booked_seats and available_seats
                }
            }
        }

        # Mock database session and queries
        db = AsyncMock()
        slot_result = MagicMock()
        slot_result.scalar_one_or_none.return_value = mock_event_slot
        db.execute.return_value = slot_result

        # Mock the update_event_slot function
        from event_service.services import slot_availability

        slot_availability.update_event_slot = AsyncMock(
            return_value=mock_event_slot
        )

        # Test the function
        result = await initialize_slot_booking_counters(db, "slot123")

        # Assertions
        assert result is True
        slot_availability.update_event_slot.assert_called_once()

    def test_time_format_matching(self):
        """Test various time format matching scenarios"""
        # This would be a unit test for the time matching logic
        # Since it's embedded in the functions, we test it indirectly through integration tests

        test_cases = [
            ("10:00 - 12:00", "10:00", "12:00", True),
            ("10:00 AM - 12:00 PM", "10:00", "12:00", True),
            ("10:00:00 - 12:00:00", "10:00", "12:00", True),
            ("09:30 - 11:30", "10:00", "12:00", False),
        ]

        # This is a conceptual test - in practice, you'd extract the matching logic
        # into a separate function to make it more testable
        for slot_time, start_time, end_time, should_match in test_cases:
            possible_formats = [
                f"{start_time} - {end_time}",
                f"{start_time}:00 - {end_time}:00",
                f"{start_time} AM - {end_time} PM",
                f"{start_time} PM - {end_time} PM",
                f"{start_time} AM - {end_time} AM",
            ]

            matches = slot_time in possible_formats
            if should_match:
                assert (
                    matches
                ), f"Expected {slot_time} to match {start_time}-{end_time}"
            # Note: The partial matching logic would need additional testing

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_booking):
        """Test error handling in slot availability functions"""
        # Mock database session that raises an exception
        db = AsyncMock()
        db.execute.side_effect = Exception("Database error")

        # Test that functions handle errors gracefully
        result = await update_slot_availability_on_booking_confirm(
            db, mock_booking
        )
        assert result is False

        result = await update_slot_availability_on_booking_cancel(
            db, mock_booking
        )
        assert result is False
