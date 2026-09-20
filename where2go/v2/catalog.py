"""Read the merged v2 catalog and expose typed POI dictionaries."""
from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path

from where2go.config import ROOT
from .storage import connect
from .taxonomy import FOOD_CATEGORIES
from .quality import serving_quality, explorable, itinerary_eligible, access_sort_key


CATALOG_V2 = ROOT / "data/catalog_v2.sqlite"


def load_catalog(path=CATALOG_V2):
    path = Path(path)
    with closing(connect(path, readonly=True)) as db:
        manifest = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        pois = {row["poi_id"]: {
            "poi_id": row["poi_id"], "data_status": row["status"], "name": row["display_name"],
            "location": row["location"], "parent_poi_id": row["parent_poi_id"],
            "business_status": row["business_status"], "aliases": [],
        } for row in db.execute("SELECT * FROM pois ORDER BY poi_id")}
        confirmed = {row[0] for row in db.execute("SELECT DISTINCT poi_id FROM source_links WHERE status='confirmed'")}
        for row in db.execute("SELECT * FROM selected_fields ORDER BY poi_id,field_name"):
            pois[row["poi_id"]][row["field_name"]] = json.loads(row["value_json"])
        for row in db.execute("""SELECT s.poi_id,s.field_name,s.selection_reason,o.observed_at,o.verification_method,
                              o.use_status,r.source_key,f.logical_path FROM selected_fields s
                              LEFT JOIN field_observations o USING(observation_id)
                              LEFT JOIN source_records r USING(source_record_id)
                              LEFT JOIN source_files f USING(source_file_id)"""):
            pois[row["poi_id"]].setdefault("provenance", {})[row["field_name"]] = {
                key: row[key] for key in ("selection_reason", "observed_at", "verification_method", "use_status", "source_key", "logical_path")}
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "poi_aliases" in tables:
            for row in db.execute("SELECT poi_id,name FROM poi_aliases ORDER BY normalized"):
                pois[row["poi_id"]]["aliases"].append(row["name"])
        if "external_ids" in tables:
            for row in db.execute("SELECT * FROM external_ids"):
                pois[row["poi_id"]].setdefault("external_ids", []).append({"provider": row["provider"], "id": row["external_id"]})
        for row in db.execute("SELECT * FROM duration_profiles"):
            pois[row["poi_id"]]["duration_profile"] = {
                "short_minutes": row["short_minutes"], "typical_minutes": row["typical_minutes"],
                "long_minutes": row["long_minutes"], "method": row["method"],
                "verified_at": row["verified_at"],
            }
        for row in db.execute("SELECT * FROM access_points ORDER BY poi_id,verified DESC,access_id"):
            pois[row["poi_id"]].setdefault("access_points", []).append({
                "access_id": row["access_id"], "latitude": row["latitude"], "longitude": row["longitude"],
                "kind": row["kind"], "access_minutes": row["access_minutes"],
                "verified": bool(row["verified"]), "method": row["method"],
            })
        for row in db.execute("SELECT * FROM ratings ORDER BY poi_id,observed_at"):
            pois[row["poi_id"]].setdefault("ratings", []).append({
                "provider": row["provider"], "rating": row["rating"], "review_count": row["review_count"],
                "observed_at": row["observed_at"], "same_observation": bool(row["same_observation"]),
            })
        category_rows = defaultdict(list)
        for row in db.execute("SELECT * FROM poi_categories ORDER BY poi_id,is_primary DESC,category"):
            category_rows[row["poi_id"]].append((row["category"], bool(row["is_primary"])))
        for poi_id, rows in category_rows.items():
            primary = next(category for category, is_primary in rows if is_primary)
            pois[poi_id]["category"] = primary
            pois[poi_id]["tags"] = [category[4:] for category, is_primary in rows if not is_primary and category.startswith("tag:")]
        hours = defaultdict(lambda: [None] * 7)
        for row in db.execute("SELECT * FROM opening_intervals WHERE specific_date IS NULL ORDER BY poi_id,day_of_week,open_minute"):
            day = row["day_of_week"]
            current = hours[row["poi_id"]][day]
            if row["status"] == "unknown":
                hours[row["poi_id"]][day] = None
            elif row["status"] == "closed":
                if current is None:
                    hours[row["poi_id"]][day] = []
            else:
                if current is None:
                    current = hours[row["poi_id"]][day] = []
                close = row["close_minute"] + (1440 if row["closes_next_day"] else 0)
                current.append((row["open_minute"], close))
        for poi_id, weekly in hours.items():
            pois[poi_id]["hours_weekly"] = weekly
        for poi in pois.values():
            from .discovery import requires_boat
            poi["requires_boat"] = requires_boat(poi)
            poi.setdefault("description", "")
            poi.setdefault("hours_raw", "")
            poi.setdefault("hours_weekly", None)
            poi.setdefault("hours_exceptions", {})
            poi.setdefault("duration_profile", None)
            poi.setdefault("access_points", [])
            poi["access_points"].sort(key=access_sort_key)
            poi.setdefault("ratings", [])
            poi.setdefault("tags", [])
            poi["entity_confirmed"] = poi["poi_id"] in confirmed
            poi["is_food"] = poi.get("category") in FOOD_CATEGORIES
            poi["serving_quality"] = serving_quality(poi)
            poi["explorable"] = explorable(poi)
            poi["itinerary_eligible"] = itinerary_eligible(poi)
    return list(pois.values()), manifest


def coverage(pois):
    rows = []
    for location in ("Hà Nội", "Đà Nẵng"):
        group = [poi for poi in pois if poi.get("location") == location]
        usable = [poi for poi in group if poi["data_status"] == "usable"]
        serviceable = [
            poi for poi in usable
            if (poi.get("serving_quality") or serving_quality(poi))["eligible"]
        ]
        with_rating = sum(any(r["same_observation"] for r in poi["ratings"]) for poi in usable)
        with_hours = sum(poi["hours_weekly"] is not None for poi in usable)
        with_full_hours = sum(
            poi["hours_weekly"] is not None and all(day is not None for day in poi["hours_weekly"])
            for poi in usable
        )
        with_duration = sum(
            poi["duration_profile"] and poi["duration_profile"]["method"] != "category_default"
            for poi in usable
        )
        with_verified_duration = sum(
            poi["duration_profile"] and bool(poi["duration_profile"].get("verified_at"))
            for poi in usable
        )
        with_curated_duration = sum(
            poi["duration_profile"] and poi["duration_profile"].get("method") == "curated_planning_estimate"
            for poi in usable
        )
        with_access = sum(any(a["verified"] for a in poi["access_points"]) for poi in usable)
        denominator = len(usable) or 1
        rows.append({
            "location": location,
            "total": len(group),
            "usable": len(usable),
            "attractions": sum(not poi["is_food"] for poi in usable),
            "food_rest": sum(poi["is_food"] for poi in usable),
            "serviceable": len(serviceable),
            "serviceable_attractions": sum(not poi["is_food"] for poi in serviceable),
            "serviceable_food_rest": sum(poi["is_food"] for poi in serviceable),
            "with_rating_pair": with_rating,
            "with_structured_hours": with_hours,
            "with_full_week_hours": with_full_hours,
            "with_specific_duration": with_duration,
            "with_verified_duration": with_verified_duration,
            "with_curated_duration_estimate": with_curated_duration,
            "with_verified_access": with_access,
            "coverage_percent": {
                "rating_pair": round(100 * with_rating / denominator, 2),
                "structured_hours": round(100 * with_hours / denominator, 2),
                "full_week_hours": round(100 * with_full_hours / denominator, 2),
                "specific_duration": round(100 * with_duration / denominator, 2),
                "verified_duration": round(100 * with_verified_duration / denominator, 2),
                "verified_access": round(100 * with_access / denominator, 2),
            },
        })
    return rows
