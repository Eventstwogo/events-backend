from datetime import date
from enum import Enum
from sqlalchemy import func
from shared.db.models.new_events import NewEvent

class EventTypeStatus(str, Enum):
    COMPLETED = "completed"   # past events
    LIVE = "live"             # ongoing events
    UPCOMING = "upcoming"     # future events
    ALL = "all"               # all events


def get_event_conditions(event_type: EventTypeStatus):
    current_date = date.today()

    # Safely get first and last element from array
    min_date = NewEvent.event_dates[1]
    max_date = NewEvent.event_dates[func.array_length(NewEvent.event_dates, 1)]

    conditions = []

    if event_type == EventTypeStatus.ALL:
        return []  # no filtering; include all events

    elif event_type == EventTypeStatus.COMPLETED:  # past events
        conditions.append(max_date < current_date)

    elif event_type == EventTypeStatus.LIVE:  # ongoing events
        conditions.append(min_date <= current_date)
        conditions.append(max_date >= current_date)

    elif event_type == EventTypeStatus.UPCOMING:  # ongoing + future
        conditions.append(max_date >= current_date)

    else:
        raise ValueError("Invalid event_type")

    return conditions
