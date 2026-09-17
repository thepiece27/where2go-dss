"""Conservative weekly OSM subset. Unsupported rules stay unknown, never 24/7."""
import re
from datetime import timedelta
import holidays

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def minutes(value):
    hour, minute = map(int, value.split(":"))
    if hour > 24 or minute > 59 or (hour == 24 and minute):
        raise ValueError("Invalid time")
    return hour * 60 + minute


def parse_week(raw):
    raw = (raw or "").strip()
    if raw == "24/7":
        return [[(0, 1440)] for _ in DAYS]
    if not raw:
        return None
    week = [[] for _ in DAYS]
    assigned = set()
    for rule in raw.split(";"):
        match = re.fullmatch(r"\s*(?:(Mo|Tu|We|Th|Fr|Sa|Su)([^0-9]*?)\s+)?(off|closed|[0-9:,\- ]+)\s*", rule)
        if not match:
            return None
        first, rest, times = match.groups()
        daytext = first + rest.strip() if first else "Mo-Su"
        chosen = []
        try:
            for group in daytext.split(","):
                ends = group.strip().split("-")
                start = DAYS.index(ends[0])
                end = DAYS.index(ends[-1])
                chosen += [(start+i) % 7 for i in range((end-start) % 7 + 1)]
            if assigned.intersection(chosen):
                return None  # OSM overriding/additive semantics not guessed.
            assigned.update(chosen)
            intervals = []
            if times not in ("off", "closed"):
                for span in times.split(","):
                    if not re.fullmatch(r"\s*\d{2}:\d{2}-\d{2}:\d{2}\s*", span):
                        return None
                    a, b = [minutes(x.strip()) for x in span.split("-")]
                    if a >= 1440 or a == b:
                        return None
                    intervals.append((a, b if b > a else b+1440))
            for day in chosen:
                week[day] = sorted(intervals)
        except (ValueError, IndexError):
            return None
    return week


def intervals_on(raw, day):
    week = parse_week(raw)
    if week is None:
        return None
    # Explicit 24/7 is date independent; otherwise holidays need date-specific evidence.
    if raw.strip() != "24/7" and day in holidays.country_holidays("VN", years=day.year):
        return None
    current = [(a, min(b, 1440)) for a, b in week[day.weekday()]]
    for a, b in week[(day-timedelta(days=1)).weekday()]:
        if b > 1440:
            current.append((0, b-1440))
    return sorted(current)
