"""Parse the conservative subset of Google weekly-hour strings used by the pilot."""
import re


DAY_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "thứ hai": 0, "thứ ba": 1, "thứ tư": 2, "thứ năm": 3,
    "thứ sáu": 4, "thứ bảy": 5, "chủ nhật": 6,
}


def clean_google_text(value):
    value = re.sub(r"[\ue000-\uf8ff]", "", str(value or ""))
    return re.sub(r"\s+", " ", value.replace("\u202f", " ").replace("\xa0", " ")).strip()


def _minute(value):
    text = clean_google_text(value).lower().replace(".", "")
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    meridiem = match.group(3)
    if minute >= 60 or (meridiem and not 1 <= hour <= 12) or (not meridiem and not 0 <= hour <= 23):
        return None
    if meridiem:
        hour %= 12
        if meridiem == "pm":
            hour += 12
    return hour * 60 + minute


def parse_google_week(rows):
    """Return seven day slots; missing/unparsed days stay None and 24/7 ends at 1440."""
    if not rows:
        return None
    weekly = [None] * 7
    for raw in rows:
        text = clean_google_text(raw)
        lowered = text.lower()
        matched = next(((day, index) for day, index in DAY_INDEX.items() if lowered.startswith(day)), None)
        if not matched:
            continue
        day_name, index = matched
        value = text[len(day_name):].strip(" :-")
        normalized = value.lower()
        if normalized in ("closed", "đóng cửa"):
            weekly[index] = []
            continue
        if normalized in ("open 24 hours", "mở cửa 24 giờ", "mở cả ngày"):
            weekly[index] = [(0, 1440)]
            continue
        intervals = []
        for part in re.split(r"\s*,\s*", value):
            times = re.split(r"\s*[–—-]\s*", part, maxsplit=1)
            if len(times) != 2:
                intervals = []
                break
            start_text, end_text = times
            start_meridiem = re.search(r"\b(am|pm)\b", start_text, re.I)
            end_meridiem = re.search(r"\b(am|pm)\b", end_text, re.I)
            if not start_meridiem and end_meridiem:
                start_text += " " + end_meridiem.group(1)
            elif start_meridiem and not end_meridiem:
                end_text += " " + start_meridiem.group(1)
            start, end = _minute(start_text), _minute(end_text)
            if start is None or end is None:
                intervals = []
                break
            if end <= start:
                end += 1440
            intervals.append((start, end))
        if intervals:
            weekly[index] = intervals
    return weekly if any(day is not None for day in weekly) else None
