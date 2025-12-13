from datetime import datetime, timedelta
from typing import Optional

TIMEZONE_OFFSETS = {
    "UTC+3": 3,
    "UTC+4": 4,
    "UTC+5": 5,
    "UTC+6": 6,
    "UTC+7": 7,
    "UTC+8": 8,
    "UTC+9": 9,
    "UTC+10": 10,
}

def convert_to_utc(local_datetime: datetime, timezone_offset: str) -> datetime:
    offset_hours = TIMEZONE_OFFSETS.get(timezone_offset, 3)
    return local_datetime - timedelta(hours=offset_hours)

def convert_from_utc(utc_datetime: datetime, timezone_offset: str) -> datetime:
    offset_hours = TIMEZONE_OFFSETS.get(timezone_offset, 3)
    return utc_datetime + timedelta(hours=offset_hours)

def get_current_time_for_timezone(timezone_offset: str) -> datetime:
    utc_now = datetime.utcnow()
    return convert_from_utc(utc_now, timezone_offset)