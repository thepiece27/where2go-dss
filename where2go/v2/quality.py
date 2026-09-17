"""Serving-quality gates separate catalog presence from itinerary eligibility."""
import re

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
    r"^unnamed",
)

CATEGORY_CONFLICTS = {
    "historic": ("trai ga", "chicken farm", "poultry"),
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
    name = normalize(poi.get("name", ""))
    if weak_name(poi.get("name", "")):
        reasons.append("weak_or_generic_name")
    if any(token in name for token in CATEGORY_CONFLICTS.get(poi.get("category"), ())):
        reasons.append("category_name_conflict")
    weights = {"rating_pair": 2, "structured_hours": 2, "website": 2, "description": 1,
               "specific_duration": 3, "verified_access": 3}
    score = sum(weights[key] for key, present in components.items() if present)
    minimum = 1 if poi.get("category") in ("restaurant", "cafe", "food_street") else 2
    if score < minimum:
        reasons.append("insufficient_service_evidence")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "components": components,
        "evidence_count": sum(components.values()),
        "evidence_score": score,
    }
