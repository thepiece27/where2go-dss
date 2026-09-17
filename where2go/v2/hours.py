"""Structured opening hours where unknown and closed remain distinct."""
from datetime import timedelta
from functools import lru_cache
import holidays


DAY_CODES = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")


@lru_cache(maxsize=16)
def _vn_holidays(year):
    return holidays.country_holidays("VN", years=year)


def validate_intervals(intervals):
    result = []
    for item in intervals:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("Khoảng giờ phải có open/close")
        start, end = item
        if not all(isinstance(v, int) for v in (start, end)) or not (0 <= start < 1440 and start < end <= 2880):
            raise ValueError("Khoảng giờ không hợp lệ")
        result.append((start, end))
    return sorted(result)


def intervals_on_date(weekly, exceptions, day, holiday_independent=False):
    """Return list for open/closed and None for unknown."""
    exception = (exceptions or {}).get(day.isoformat())
    if exception is not None:
        if exception.get("status") == "unknown":
            return None
        if exception.get("status") == "closed":
            return []
        return validate_intervals(exception.get("intervals", []))
    if weekly is None or len(weekly) != 7:
        return None
    if not holiday_independent and day in _vn_holidays(day.year):
        return None
    own = weekly[day.weekday()]
    if own is None:
        return None
    result = [(start, min(end, 1440)) for start, end in validate_intervals(own)]
    previous = weekly[(day - timedelta(days=1)).weekday()]
    if previous:
        result.extend((0, end - 1440) for _, end in validate_intervals(previous) if end > 1440)
    return sorted(result)
