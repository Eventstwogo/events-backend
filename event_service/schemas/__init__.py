"""
Event service schemas module.

This module exports all Pydantic schemas for the event service.
"""

from .advanced_events import (
    EventListResponse,
    EventResponse,
)

# Event schemas
from .events import (
    EventCreateRequest,
    EventUpdateRequest,
)

# Slot schemas
from .slots import (
    EventSlotCreateRequest,
    EventSlotCreateResponse,
    EventSlotResponse,
)

__all__ = [
    # Event schemas
    "EventCreateRequest",
    "EventUpdateRequest",
    "EventResponse",
    "EventListResponse",
    # Slot schemas
    "EventSlotCreateRequest",
    "EventSlotCreateResponse",
    "EventSlotResponse",
]
