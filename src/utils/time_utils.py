from datetime import datetime, timezone
from typing import Tuple


def to_minutes(dt: datetime, reference: datetime) -> int:
    """Convert datetime to minutes offset from reference time."""
    delta = dt - reference
    return int(delta.total_seconds() / 60)


def from_minutes(minutes: int, reference: datetime) -> datetime:
    """Convert minutes offset back to datetime."""
    from datetime import timedelta
    return reference + timedelta(minutes=minutes)


def parse_iso(date_str: str) -> datetime:
    """Parse ISO datetime string, handling both with/without timezone."""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")


def intervals_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Check if two time intervals overlap."""
    return not (a_end <= b_start or b_end <= a_start)


def is_within_windows(start: int, end: int, windows: list[Tuple[int, int]]) -> bool:
    """Check if interval [start, end) is completely within one of the windows."""
    for w_start, w_end in windows:
        if w_start <= start < end <= w_end:
            return True
    return False
