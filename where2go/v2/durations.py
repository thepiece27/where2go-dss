"""Visit-duration profiles with explicit source and fallback semantics."""
from .taxonomy import CATEGORIES


DEFAULT_PROFILES = {
    "viewpoint": (15, 30, 45),
    "historic": (20, 45, 75),
    "temple": (20, 45, 90),
    "museum": (30, 60, 120),
    "park": (30, 60, 120),
    "market": (30, 60, 90),
    "old_quarter": (60, 120, 180),
    "craft_village": (60, 120, 180),
    "beach": (45, 90, 150),
    "theme_park": (180, 300, 480),
    "nature_area": (60, 120, 240),
    "zoo": (60, 120, 180),
    "gallery": (30, 60, 90),
    "attraction": (30, 60, 120),
    "performance_venue": (45, 90, 120),
    "restaurant": (45, 60, 90),
    "cafe": (20, 30, 60),
    "food_street": (30, 60, 90),
}

PACE_LEVEL = {"quick": "short", "balanced": "typical", "relaxed": "long"}

if set(DEFAULT_PROFILES) != set(CATEGORIES):
    raise RuntimeError("Mỗi category v2 phải có duration profile mặc định")


def fallback_profile(category):
    short, typical, long = DEFAULT_PROFILES[category]
    return {
        "short_minutes": short,
        "typical_minutes": typical,
        "long_minutes": long,
        "method": "category_default",
        "source": "where2go/v2/durations.py",
        "verified_at": None,
    }


def choose_duration(profile, pace, override=None):
    if override is not None:
        if not isinstance(override, int) or not 5 <= override <= 720:
            raise ValueError("Thời lượng người dùng phải từ 5 đến 720 phút")
        return override, "user_override"
    key = PACE_LEVEL[pace] + "_minutes"
    value = profile.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ValueError("Duration profile không hợp lệ")
    return value, profile.get("method", "unknown")

