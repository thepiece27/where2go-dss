"""Dataset selection, coverage and export helpers for Where2Go v2."""
from collections import Counter
import csv
from functools import lru_cache
import json
from pathlib import Path

from where2go.config import ROOT
from .quality import latest_rating_pair
from .taxonomy import FOOD_CATEGORIES


SEVERE_QUALITY_REASONS = {"weak_or_generic_name", "category_name_conflict"}


@lru_cache(maxsize=1)
def curated_focus_ids():
    path = ROOT / "data/curation/focus_landmarks_v2.csv"
    result = {"Hà Nội": [], "Đà Nẵng": []}
    if not path.exists():
        return result
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = sorted(csv.DictReader(handle), key=lambda row: (int(row.get("priority") or 99), row["record_id"]))
    for row in rows:
        poi_id = str(row.get("canonical_poi_id") or "").strip()
        location = row.get("location_expected")
        if poi_id and location in result:
            result[location].append(poi_id)
    return result


def evidence_score(poi):
    quality = poi.get("serving_quality") or {}
    components = quality.get("components", {})
    return sum({
        "rating_pair": 4,
        "structured_hours": 3,
        "website": 2,
        "description": 1,
        "specific_duration": 3,
        "verified_access": 3,
    }.get(key, 0) for key, present in components.items() if present)


def _priority_pool(pois, location, food):
    pool = []
    for poi in pois:
        if poi.get("location") != location or poi.get("data_status") != "usable":
            continue
        is_food = poi.get("is_food", poi.get("category") in FOOD_CATEGORIES)
        if is_food != food:
            continue
        quality = poi.get("serving_quality") or {}
        reasons = set(quality.get("reasons", []))
        if reasons & SEVERE_QUALITY_REASONS:
            continue
        pool.append(poi)
    return pool


def select_priority(pois, location, food, limit):
    """Select an enrichment queue, preferring serviceable POIs without hiding gaps."""
    pool = _priority_pool(pois, location, food)
    pool.sort(key=lambda poi: (
        not bool((poi.get("serving_quality") or {}).get("eligible")),
        -evidence_score(poi), poi.get("category") or "", poi["poi_id"],
    ))
    by_id = {poi["poi_id"]: poi for poi in pool}
    selected = [] if food else [by_id[poi_id] for poi_id in curated_focus_ids().get(location, []) if poi_id in by_id]
    selected = selected[:limit]
    category_counts = Counter(poi.get("category") for poi in selected)
    while len(selected) < min(limit, len(pool)):
        remaining = [poi for poi in pool if poi not in selected]
        poi = min(remaining, key=lambda item: (
            not bool((item.get("serving_quality") or {}).get("eligible")),
            category_counts[item.get("category")], -evidence_score(item), item["poi_id"],
        ))
        selected.append(poi)
        category_counts[poi.get("category")] += 1
    return selected


def _percent(numerator, denominator):
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def priority_coverage(pois, location):
    attractions = select_priority(pois, location, False, 50)
    food = select_priority(pois, location, True, 20)
    combined = attractions + food
    with_hours = sum(poi.get("hours_weekly") is not None for poi in combined)
    with_full_hours = sum(
        poi.get("hours_weekly") is not None and all(day is not None for day in poi["hours_weekly"])
        for poi in combined
    )
    with_duration = sum(
        bool(poi.get("duration_profile"))
        and poi["duration_profile"].get("method") != "category_default"
        for poi in attractions
    )
    with_verified_duration = sum(
        bool(poi.get("duration_profile")) and bool(poi["duration_profile"].get("verified_at"))
        for poi in attractions
    )
    with_curated_duration = sum(
        bool(poi.get("duration_profile"))
        and poi["duration_profile"].get("method") == "curated_planning_estimate"
        for poi in attractions
    )
    with_rating = sum(bool(latest_rating_pair(poi)) for poi in combined)
    with_access = sum(any(point.get("verified") for point in poi.get("access_points", [])) for poi in combined)
    serviceable = sum(bool((poi.get("serving_quality") or {}).get("eligible")) for poi in combined)
    hours_percent = _percent(with_hours, len(combined))
    duration_percent = _percent(with_duration, len(attractions))
    verified_duration_percent = _percent(with_verified_duration, len(attractions))
    return {
        "selected": len(combined),
        "attractions": len(attractions),
        "food_rest": len(food),
        "serviceable": serviceable,
        "with_structured_hours": with_hours,
        "with_full_week_hours": with_full_hours,
        "with_specific_duration": with_duration,
        "with_verified_duration": with_verified_duration,
        "with_curated_duration_estimate": with_curated_duration,
        "with_rating_pair": with_rating,
        "with_verified_access": with_access,
        "hours_percent": hours_percent,
        "specific_duration_percent": duration_percent,
        "verified_duration_percent": verified_duration_percent,
        "targets": {
            "attractions": 50,
            "food_rest": 20,
            "hours_percent": 80,
            "verified_duration_percent": 80,
        },
        "target_status": {
            "attractions": len(attractions) >= 50,
            "food_rest": len(food) >= 20,
            "hours": hours_percent >= 80,
            # Preserve the old key for clients while applying the real target:
            # a duration reviewed by a human or supported by a source.
            "specific_duration": verified_duration_percent >= 80,
            "verified_duration": verified_duration_percent >= 80,
        },
    }


def dataset_summary(pois, manifest):
    from .catalog import coverage

    locations = []
    for row in coverage(pois):
        row = dict(row)
        row["priority_set"] = priority_coverage(pois, row["location"])
        locations.append(row)
    return {
        "dataset_version": manifest["version"],
        "schema_version": manifest.get("schema_version"),
        "created_at": manifest.get("created_at"),
        "poi_count": len(pois),
        "locations": locations,
        "rights": manifest.get("rights", {}),
        "files": {
            "database": "data/catalog_v2.sqlite",
            "pois": "data/reports/v2/dataset/pois.csv",
            "opening_hours": "data/reports/v2/dataset/opening_hours.csv",
            "ratings": "data/reports/v2/dataset/ratings.csv",
            "duration_profiles": "data/reports/v2/dataset/duration_profiles.csv",
            "access_points": "data/reports/v2/dataset/access_points.csv",
            "sources": "data/reports/v2/dataset/sources.csv",
        },
        "notes": [
            "Google Maps observations are restricted_internal and are not a public redistribution dataset.",
            "category_default duration values are design fallbacks, not verified visit durations.",
            "Structured hours do not imply field verification or holiday accuracy.",
        ],
    }


def json_cell(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
