"""
Integration tests for booking and slot availability functionality
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from event_service.services.slot_availability import (
    update_slot_availability_on_booking_cancel,
    update_slot_availability_on_booking_confirm,
)
from shared.db.models.events import BookingStatus, EventBooking


class TestBookingSlotIntegration:
    """Integration tests for booking and slot availability"""

    @pytest.fixture
    def sample_booking(self):
        """Create a sample booking for testing"""
        booking = MagicMock()
        booking.booking_id = 1
        booking.user_id = "user123"
        booking.event_id = "evt123"
        booking.num_seats = 3
        booking.slot = "10:00 - 12:00"
        booking.booking_date = date(2024, 1, 15)
        booking.booking_status = BookingStatus.APPROVED
        return booking

    @pytest.fixture
    def sample_event_slot(self):
        """Create a sample event slot with availability data"""
        slot = MagicMock()
        slot.slot_id = "slot123"
        slot.slot_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                    "booked_seats": 15,
                    "available_seats": 35,
                }
            }
        }
        return slot

    @pytest.mark.asyncio
    async def test_booking_confirm_updates_slot_availability(
        self, sample_booking, sample_event_slot
    ):
        """Test that confirming a booking updates slot availability"""
        db = AsyncMock()

        # Mock the slot availability functions
        with patch(
            "event_service.services.slot_availability.get_slot_info_from_booking"
        ) as mock_get_slot:
            with patch(
                "event_service.services.slot_availability.update_event_slot"
            ) as mock_update_slot:

                # Setup mocks
                mock_get_slot.return_value = (
                    sample_event_slot,
                    "2024-01-15",
                    "slot_1",
                )
                mock_update_slot.return_value = sample_event_slot

                # Test the function
                result = await update_slot_availability_on_booking_confirm(
                    db, sample_booking
                )

                # Assertions
                assert result is True
                mock_get_slot.assert_called_once_with(db, sample_booking)
                mock_update_slot.assert_called_once()

                # Verify the slot data was updated correctly
                call_args = mock_update_slot.call_args
                updated_slot_data = call_args[1][
                    "slot_data"
                ]  # keyword argument

                # Check that booked_seats was increased
                slot_info = updated_slot_data["2024-01-15"]["slot_1"]
                expected_booked_seats = (
                    15 + sample_booking.num_seats
                )  # 15 + 3 = 18
                assert slot_info["booked_seats"] == expected_booked_seats

                # Check that available_seats was decreased
                expected_available_seats = (
                    50 - expected_booked_seats
                )  # 50 - 18 = 32
                assert slot_info["available_seats"] == expected_available_seats

    @pytest.mark.asyncio
    async def test_booking_cancel_updates_slot_availability(
        self, sample_booking, sample_event_slot
    ):
        """Test that cancelling a booking updates slot availability"""
        db = AsyncMock()

        # Mock the slot availability functions
        with patch(
            "event_service.services.slot_availability.get_slot_info_from_booking"
        ) as mock_get_slot:
            with patch(
                "event_service.services.slot_availability.update_event_slot"
            ) as mock_update_slot:

                # Setup mocks
                mock_get_slot.return_value = (
                    sample_event_slot,
                    "2024-01-15",
                    "slot_1",
                )
                mock_update_slot.return_value = sample_event_slot

                # Test the function
                result = await update_slot_availability_on_booking_cancel(
                    db, sample_booking
                )

                # Assertions
                assert result is True
                mock_get_slot.assert_called_once_with(db, sample_booking)
                mock_update_slot.assert_called_once()

                # Verify the slot data was updated correctly
                call_args = mock_update_slot.call_args
                updated_slot_data = call_args[1][
                    "slot_data"
                ]  # keyword argument

                # Check that booked_seats was decreased
                slot_info = updated_slot_data["2024-01-15"]["slot_1"]
                expected_booked_seats = (
                    15 - sample_booking.num_seats
                )  # 15 - 3 = 12
                assert slot_info["booked_seats"] == expected_booked_seats

                # Check that available_seats was increased
                expected_available_seats = (
                    50 - expected_booked_seats
                )  # 50 - 12 = 38
                assert slot_info["available_seats"] == expected_available_seats

    @pytest.mark.asyncio
    async def test_booking_cancel_handles_insufficient_booked_seats(
        self, sample_booking, sample_event_slot
    ):
        """Test that cancelling handles case where booked_seats < num_seats"""
        db = AsyncMock()

        # Modify slot to have fewer booked seats than the booking
        sample_event_slot.slot_data["2024-01-15"]["slot_1"][
            "booked_seats"
        ] = 2  # Less than booking.num_seats (3)

        # Mock the slot availability functions
        with patch(
            "event_service.services.slot_availability.get_slot_info_from_booking"
        ) as mock_get_slot:
            with patch(
                "event_service.services.slot_availability.update_event_slot"
            ) as mock_update_slot:

                # Setup mocks
                mock_get_slot.return_value = (
                    sample_event_slot,
                    "2024-01-15",
                    "slot_1",
                )
                mock_update_slot.return_value = sample_event_slot

                # Test the function
                result = await update_slot_availability_on_booking_cancel(
                    db, sample_booking
                )

                # Assertions
                assert result is True

                # Verify the slot data was updated correctly (should be set to 0)
                call_args = mock_update_slot.call_args
                updated_slot_data = call_args[1]["slot_data"]

                slot_info = updated_slot_data["2024-01-15"]["slot_1"]
                assert (
                    slot_info["booked_seats"] == 0
                )  # Should be set to 0, not negative
                assert (
                    slot_info["available_seats"] == 50
                )  # Full capacity available

    def test_slot_data_structure_validation(self):
        """Test that slot data structure is as expected"""
        # This test validates our understanding of the slot data structure
        expected_structure = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                    "booked_seats": 0,
                    "available_seats": 50,
                }
            }
        }

        # Verify structure keys
        assert "2024-01-15" in expected_structure
        assert "slot_1" in expected_structure["2024-01-15"]

        slot_info = expected_structure["2024-01-15"]["slot_1"]
        required_fields = [
            "start_time",
            "end_time",
            "capacity",
            "price",
            "booked_seats",
            "available_seats",
        ]

        for field in required_fields:
            assert (
                field in slot_info
            ), f"Required field '{field}' missing from slot structure"
