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
    SlotCreateRequest,
    SlotFilters,
    SlotListResponse,
    SlotResponse,
    SlotSimpleResponse,
    SlotStatusUpdateRequest,
    SlotUpdateRequest,
)

__all__ = [
    # Event schemas
    "EventCreateRequest",
    "EventUpdateRequest",
    "EventResponse",
    "EventListResponse",
    # Slot schemas
    "SlotCreateRequest",
    "SlotUpdateRequest",
    "SlotStatusUpdateRequest",
    "SlotResponse",
    "SlotSimpleResponse",
    "SlotListResponse",
    "SlotFilters",
]
