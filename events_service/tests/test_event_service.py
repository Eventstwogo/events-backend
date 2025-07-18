"""Test cases for event service functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from events_service.services.event_service import (
    generate_next_event_id,
    check_event_title_exists,
    create_event,
    get_event_by_id,
    get_events,
    update_event,
    soft_delete_event,
    restore_event,
    hard_delete_event,
    get_events_count,
    increment_event_views,
    increment_event_bookings,
    decrement_event_bookings,
    get_featured_events,
    search_events
)
from events_service.schemas.events import EventCreate, EventUpdate
from shared.db.models.admin_users import EventPublic


class TestEventService:
    """Test cases for event service functions."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return EventCreate(
            title="Test Event",
            description="Test Description",
            city="Test City",
            category="Test Category",
            tags="test, event",
            image_url="https://example.com/image.jpg",
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=2),
            location="Test Location",
            is_featured=False
        )
    
    @pytest.fixture
    def sample_event(self):
        """Sample event object for testing."""
        event = EventPublic()
        event.event_id = "event_1"
        event.title = "Test Event"
        event.description = "Test Description"
        event.city = "Test City"
        event.category = "Test Category"
        event.tags = "test, event"
        event.image_url = "https://example.com/image.jpg"
        event.start_time = datetime.now() + timedelta(days=1)
        event.end_time = datetime.now() + timedelta(days=1, hours=2)
        event.location = "Test Location"
        event.is_featured = False
        event.views = 0
        event.bookings_count = 0
        event.is_deleted = False
        event.created_at = datetime.now()
        event.updated_at = None
        return event
    
    async def test_generate_next_event_id(self, mock_db):
        """Test event ID generation."""
        # Mock the database query to return a count
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_db.execute.return_value = mock_result
        
        event_id = await generate_next_event_id(mock_db)
        assert event_id == "event_6"
    
    async def test_check_event_title_exists(self, mock_db):
        """Test checking if event title exists."""
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result
        
        exists = await check_event_title_exists(mock_db, "Test Event")
        assert exists is False
    
    async def test_create_event(self, mock_db, sample_event_data, sample_event):
        """Test event creation."""
        # Mock the ID generation
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_db.execute.return_value = mock_result
        
        # Mock the add and commit operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock the refresh to return our sample event
        async def mock_refresh(event):
            for attr, value in vars(sample_event).items():
                if not attr.startswith('_'):
                    setattr(event, attr, value)
        
        mock_db.refresh.side_effect = mock_refresh
        
        result = await create_event(mock_db, sample_event_data)
        
        assert result.title == sample_event_data.title
        assert result.city == sample_event_data.city
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    async def test_get_event_by_id(self, mock_db, sample_event):
        """Test getting event by ID."""
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_event
        mock_db.execute.return_value = mock_result
        
        result = await get_event_by_id(mock_db, "event_1")
        assert result == sample_event
    
    async def test_increment_event_views(self, mock_db, sample_event):
        """Test incrementing event views."""
        # Mock getting the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_event
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await increment_event_views(mock_db, "event_1")
        
        assert result.views == 1
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    async def test_soft_delete_event(self, mock_db, sample_event):
        """Test soft deleting an event."""
        # Mock getting the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_event
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await soft_delete_event(mock_db, "event_1")
        
        assert result.is_deleted is True
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    async def test_restore_event(self, mock_db, sample_event):
        """Test restoring a soft-deleted event."""
        # Set event as deleted
        sample_event.is_deleted = True
        
        # Mock getting the event
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_event
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await restore_event(mock_db, "event_1")
        
        assert result.is_deleted is False
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


if __name__ == "__main__":
    print("Event service tests created successfully!")
    print("Run with: pytest events_service/tests/test_event_service.py")