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
