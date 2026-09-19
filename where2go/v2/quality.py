"""Serving-quality gates separate catalog presence from itinerary eligibility."""
import re
import math

from where2go.ranking import normalize


GENERIC_EXACT = {
    "results", "0 km", "pont main", "hard to climb", "crowd watching",
    "rao chan", "art gallery", "nha bia", "cho dem", "abandoned van",
    "military blockhouse ruins",
}
GENERIC_PATTERNS = (
    r"^(group )?[a-k]\d*$",
    r"^diem \d+$",
    r"^point \d+$",
    r"^\d+(?:\s+\d+)?\s*km$",
    r"^unnamed",
)

CATEGORY_CONFLICTS = {
    "historic": ("trai ga", "chicken farm", "poultry"),
    "park": ("trung tam van hoa", "the thao", "cultural center", "sports center"),
    "zoo": ("tiem cay", "plant shop", "design"),
    "viewpoint": ("rao chan", "barrier", "hard to climb"),
}


def latest_rating_pair(poi):
    rows = [row for row in poi.get("ratings", []) if row.get("same_observation")]
    return max(rows, key=lambda row: row.get("observed_at") or "") if rows else None


def evidence_components(poi):
    duration = poi.get("duration_profile") or {}
    description = normalize(poi.get("description", ""))
    name = normalize(poi.get("name", ""))
    website = str(poi.get("website") or "").strip().lower()
    return {
        "rating_pair": bool(latest_rating_pair(poi)),
        "structured_hours": poi.get("hours_weekly") is not None,
        "website": website.startswith(("http://", "https://")),
        "description": len(description) >= 20 and description != name,
        "specific_duration": duration.get("method") not in (None, "category_default"),
        "verified_access": any(point.get("verified") for point in poi.get("access_points", [])),
    }


def weak_name(name):
    text = normalize(name)
    if not text or text in GENERIC_EXACT or len(text) < 4:
        return True
    if any(re.fullmatch(pattern, text) for pattern in GENERIC_PATTERNS):
        return True
    return False


def serving_quality(poi):
    components = evidence_components(poi)
    reasons = []
    if poi.get("data_status", "usable") != "usable":
        reasons.append("identity_needs_review")
    if poi.get("entity_confirmed") is False:
        reasons.append("entity_unconfirmed")
    name = normalize(poi.get("name", ""))
    if weak_name(poi.get("name", "")):
        reasons.append("weak_or_generic_name")
    if poi.get("business_status") in ("temporarily_closed", "permanently_closed"):
        reasons.append("business_closed")
    if any(token in name for token in CATEGORY_CONFLICTS.get(poi.get("category"), ())):
        reasons.append("category_name_conflict")
    weights = {"rating_pair": 2, "structured_hours": 2, "website": 2, "description": 1,
               "specific_duration": 3, "verified_access": 3}
    score = sum(weights[key] for key, present in components.items() if present)
    # A free-text description alone is not enough to recommend a meal stop.
    # Score 2 requires at least structured hours, a valid rating pair, or a
    # website; attractions already used the same minimum.
    minimum = 2
    if score < minimum:
        reasons.append("insufficient_service_evidence")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "components": components,
        "evidence_count": sum(components.values()),
        "evidence_score": score,
    }


def explorable(poi):
    """Identity and position are required; missing itinerary metadata is allowed."""
    if poi.get("data_status") != "usable" or poi.get("entity_confirmed") is False or weak_name(poi.get("name")):
        return False
    quality = poi.get("serving_quality") or {}
    if any(reason in quality.get("reasons", []) for reason in ("weak_or_generic_name", "category_name_conflict")):
        return False
    lat, lon = poi.get("latitude"), poi.get("longitude")
    return bool(poi.get("location") and isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                and math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180)


def itinerary_eligible(poi):
    return (poi.get("data_status") == "usable" and poi.get("entity_confirmed") is not False
            and bool((poi.get("serving_quality") or serving_quality(poi))["eligible"]))


def access_sort_key(point):
    method = str(point.get("method") or "")
    return (not point.get("verified"), 0 if method == "google_entity_url_not_verified_entrance" else 1,
            point.get("access_id", ""))


def manual_trip_quality(poi, location=None):
    """Missing metadata is allowed; unresolved identity/position/closure is not."""
    reasons = []
    from .discovery import requires_boat
    if requires_boat(poi):
        reasons.append("boat_transfer_required")
    if not explorable(poi):
        reasons.append("identity_or_coordinates_unconfirmed")
    if poi.get("business_status") in ("temporarily_closed", "permanently_closed"):
        reasons.append("business_closed")
    if poi.get("location") not in ("Hà Nội", "Đà Nẵng") or (location and poi.get("location") != location):
        reasons.append("wrong_location")
    return {"eligible": not reasons, "reasons": reasons}


def recommendation_eligible(poi, location=None):
    return manual_trip_quality(poi, location)["eligible"] and itinerary_eligible(poi)
