import json
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional


def filter_slot_data(
    slot_data: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Remove past-dated entries from slot_data"""
    if not slot_data:
        return slot_data

    today_str = date.today().isoformat()
    return {
        slot_date: slots
        for slot_date, slots in slot_data.items()
        if slot_date >= today_str
    }


def normalize_tags(tags):
    """Normalize tags: split on '#' or ',', ensure '#' prefix, and return list."""
    if not tags:
        return []

    # If tags is already a list, join into a string for processing
    if isinstance(tags, list):
        tags = ",".join(str(tag) for tag in tags)

    # Split by either '#' or ',' and strip spaces
    parts = re.split(r"[#,]", tags)

    # Normalize: remove empties, strip spaces, add '#' if missing
    return [
        tag if tag.startswith("#") else f"#{tag}"
        for tag in (t.strip() for t in parts)
        if tag.strip()
    ]


def safe_json_parse(json_string, field_name, default_value=None):
    """Safely parse JSON string with better error handling"""
    if not json_string or json_string.strip() == "":
        return default_value

    # Handle common cases where Swagger might send malformed data
    json_string = json_string.strip()

    # Handle cases where Swagger might double-quote the JSON string
    if json_string.startswith('"') and json_string.endswith('"'):
        json_string = json_string[1:-1]
        # Unescape any escaped quotes
        json_string = json_string.replace('\\"', '"')

    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {field_name}: {str(e)}. Received: '{json_string[:50]}"
            f"{'...' if len(json_string) > 50 else ''}'",
            json_string,
            e.pos,
        )


def parse_date(date_string: str) -> datetime:
    """
    Parse date string (YYYY-MM-DD format) to datetime object.

    Args:
        date_string: Date string in YYYY-MM-DD format

    Returns:
        datetime: Parsed datetime object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(
            f"Invalid date format '{date_string}'. Expected YYYY-MM-DD format: {str(e)}"
        )


def parse_duration_to_minutes(duration: str) -> int:
    """
    Convert string like "2 hours", "1 hour 30 minutes" into total minutes
    """
    total_minutes = 0
    parts = duration.lower().split()
    i = 0
    while i < len(parts):
        if parts[i].isdigit():
            num = int(parts[i])
            if i + 1 < len(parts):
                if "hour" in parts[i + 1]:
                    total_minutes += num * 60
                elif "minute" in parts[i + 1]:
                    total_minutes += num
            i += 2
        else:
            i += 1
    return total_minutes


def minutes_to_duration_string(minutes: int) -> str:
    """Convert minutes into a duration string (e.g. 90 -> '1h 30m')."""
    if minutes < 0:
        raise ValueError("Minutes cannot be negative")

    hours, mins = divmod(minutes, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours} hours")
    if mins > 0:
        parts.append(f"{mins}minutes")

    return " ".join(parts) if parts else "0 minutes"


def calculate_end_time(start_time_str: str, duration_str: str) -> str:
    """
    start_time_str: "10:00 AM"
    duration_str: "3 hours" or "2 hours 30 minutes"
    returns: "01:00 PM"
    """
    # Parse start time
    start_dt = datetime.strptime(start_time_str, "%I:%M %p")

    # Parse duration
    hours = 0
    minutes = 0

    hour_match = re.search(r"(\d+)\s*hours?", duration_str)
    if hour_match:
        hours = int(hour_match.group(1))

    minute_match = re.search(r"(\d+)\s*minutes?", duration_str)
    if minute_match:
        minutes = int(minute_match.group(1))

    # Add duration
    end_dt = start_dt + timedelta(hours=hours, minutes=minutes)

    # Return formatted time
    return end_dt.strftime("%I:%M %p")
