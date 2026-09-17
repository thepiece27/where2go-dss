"""Parsers for source observations; ambiguous text remains raw."""
from datetime import date, datetime, time
import hashlib
import math
import re

from where2go.ranking import normalize


def stable_id(prefix, *parts):
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()[:24]}"


def scalar(value):
    """Convert pandas/openpyxl values to strict JSON-compatible scalars."""
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def parse_rating(value):
    text = str(value or "").strip()
    match = re.fullmatch(r"([1-5](?:[.,]\d+)?)\s*(?:stars?|sao|/5)?", text, re.I)
    if not match:
        return None
    result = float(match.group(1).replace(",", "."))
    return result if 1 <= result <= 5 else None


def parse_review_count(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if math.isfinite(value) and value >= 0 and value == int(value) else None
    text = str(value or "").strip().lower()
    match = re.fullmatch(r"([\d.,]+)\s*(?:reviews?|bài đánh giá|lượt đánh giá)?", text)
    if not match:
        return None
    digits = match.group(1)
    if digits.isdigit():
        return int(digits)
    if re.fullmatch(r"\d{1,3}(?:[,.]\d{3})+", digits):
        return int(re.sub(r"[,.]", "", digits))
    return None


def entity_coordinate(url):
    """Use the entity marker pair only; never use the @ viewport center."""
    matches = re.findall(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", str(url or ""))
    if not matches:
        return None
    latitude, longitude = map(float, matches[-1])
    if -90 <= latitude <= 90 and -180 <= longitude <= 180:
        return latitude, longitude
    return None


def focus_location(value):
    text = normalize(value)
    if "ha noi" in text:
        return "Hà Nội"
    if any(token in text for token in ("da nang", "quang nam", "hoi an", "my son")):
        return "Đà Nẵng"
    return None


def normalized_entity_name(row):
    result = str(row.get("maps_result_name") or "").strip()
    seed = str(row.get("Tên địa điểm") or row.get("seed_name") or "").strip()
    if normalize(result) == "results":
        return ""
    return normalize(result or seed)

