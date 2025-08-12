import re
from datetime import date
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
