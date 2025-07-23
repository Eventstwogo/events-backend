"""
Test cases for slot update JSONB merge functionality
"""

import pytest

from event_service.services.slots import deep_merge_slot_data


class TestSlotDataMerge:
    """Test cases for deep_merge_slot_data function"""

    def test_merge_empty_existing_data(self):
        """Test merging when existing data is empty"""
        existing_data = {}
        new_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                }
            }
        }

        result = deep_merge_slot_data(existing_data, new_data)
        assert result == new_data

    def test_merge_empty_new_data(self):
        """Test merging when new data is empty"""
        existing_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                }
            }
        }
        new_data = {}

        result = deep_merge_slot_data(existing_data, new_data)
        assert result == existing_data

    def test_merge_new_date(self):
        """Test adding a new date to existing data"""
        existing_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                }
            }
        }
        new_data = {
            "2024-01-16": {
                "slot_1": {
                    "start_time": "09:00",
                    "end_time": "11:00",
                    "capacity": 40,
                    "price": 28.00,
                }
            }
        }

        result = deep_merge_slot_data(existing_data, new_data)

        # Should have both dates
        assert "2024-01-15" in result
        assert "2024-01-16" in result
        assert result["2024-01-15"] == existing_data["2024-01-15"]
        assert result["2024-01-16"] == new_data["2024-01-16"]

    def test_merge_new_slot_in_existing_date(self):
        """Test adding a new slot to an existing date"""
        existing_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                }
            }
        }
        new_data = {
            "2024-01-15": {
                "slot_2": {
                    "start_time": "14:00",
                    "end_time": "16:00",
                    "capacity": 30,
                    "price": 30.00,
                }
            }
        }

        result = deep_merge_slot_data(existing_data, new_data)

        # Should have both slots for the same date
        assert "2024-01-15" in result
        assert "slot_1" in result["2024-01-15"]
        assert "slot_2" in result["2024-01-15"]
        assert (
            result["2024-01-15"]["slot_1"]
            == existing_data["2024-01-15"]["slot_1"]
        )
        assert (
            result["2024-01-15"]["slot_2"] == new_data["2024-01-15"]["slot_2"]
        )

    def test_merge_slot_properties(self):
        """Test merging properties of an existing slot"""
        existing_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "capacity": 50,
                    "price": 25.00,
                    "description": "Morning session",
                }
            }
        }
        new_data = {
            "2024-01-15": {
                "slot_1": {
                    "capacity": 60,  # Update capacity
                    "price": 30.00,  # Update price
                    "location": "Room A",  # Add new property
                }
            }
        }

        result = deep_merge_slot_data(existing_data, new_data)

        expected_slot = {
            "start_time": "10:00",  # Preserved
            "end_time": "12:00",  # Preserved
            "capacity": 60,  # Updated
            "price": 30.00,  # Updated
            "description": "Morning session",  # Preserved
            "location": "Room A",  # Added
        }

        assert result["2024-01-15"]["slot_1"] == expected_slot

    def test_complex_merge_scenario(self):
        """Test a complex merge scenario with multiple dates and slots"""
        existing_data = {
            "2024-01-15": {
                "slot_1": {
                    "start_time": "10:00",
                    "capacity": 50,
                    "price": 25.00,
                },
                "slot_2": {
                    "start_time": "14:00",
                    "capacity": 30,
                    "price": 30.00,
                },
            },
            "2024-01-16": {
                "slot_1": {
                    "start_time": "09:00",
                    "capacity": 40,
                    "price": 28.00,
                }
            },
        }

        new_data = {
            "2024-01-15": {
                "slot_1": {
                    "capacity": 55,  # Update existing slot
                    "location": "Hall A",  # Add new property
                },
                "slot_3": {  # Add new slot
                    "start_time": "18:00",
                    "capacity": 25,
                    "price": 35.00,
                },
            },
            "2024-01-17": {  # Add new date
                "slot_1": {
                    "start_time": "11:00",
                    "capacity": 45,
                    "price": 32.00,
                }
            },
        }

        result = deep_merge_slot_data(existing_data, new_data)

        # Verify 2024-01-15 has all three slots with proper merging
        assert len(result["2024-01-15"]) == 3
        assert result["2024-01-15"]["slot_1"]["capacity"] == 55  # Updated
        assert (
            result["2024-01-15"]["slot_1"]["start_time"] == "10:00"
        )  # Preserved
        assert result["2024-01-15"]["slot_1"]["location"] == "Hall A"  # Added
        assert (
            result["2024-01-15"]["slot_2"]
            == existing_data["2024-01-15"]["slot_2"]
        )  # Unchanged
        assert (
            result["2024-01-15"]["slot_3"] == new_data["2024-01-15"]["slot_3"]
        )  # Added

        # Verify 2024-01-16 is unchanged
        assert result["2024-01-16"] == existing_data["2024-01-16"]

        # Verify 2024-01-17 is added
        assert result["2024-01-17"] == new_data["2024-01-17"]

    def test_merge_with_invalid_data_types(self):
        """Test merge behavior with invalid data types"""
        existing_data = {"2024-01-15": {"slot_1": "invalid_data"}}  # Not a dict
        new_data = {
            "2024-01-15": {"slot_1": {"start_time": "10:00", "capacity": 50}}
        }

        result = deep_merge_slot_data(existing_data, new_data)

        # Should replace invalid existing data with new valid data
        assert (
            result["2024-01-15"]["slot_1"] == new_data["2024-01-15"]["slot_1"]
        )

    def test_merge_preserves_original_data(self):
        """Test that merge doesn't modify original data structures"""
        existing_data = {"2024-01-15": {"slot_1": {"capacity": 50}}}
        new_data = {"2024-01-15": {"slot_1": {"price": 25.00}}}

        original_existing = existing_data.copy()
        original_new = new_data.copy()

        result = deep_merge_slot_data(existing_data, new_data)

        # Original data should be unchanged
        assert existing_data == original_existing
        assert new_data == original_new

        # Result should have merged data
        assert result["2024-01-15"]["slot_1"]["capacity"] == 50
        assert result["2024-01-15"]["slot_1"]["price"] == 25.00


if __name__ == "__main__":
    pytest.main([__file__])
