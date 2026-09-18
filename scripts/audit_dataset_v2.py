"""Audit the merged v2 catalog and its readable exports without changing source data."""
import argparse
from collections import Counter, defaultdict
import csv
from contextlib import closing
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from where2go.config import ROOT
from where2go.ranking import normalize
from where2go.v2.catalog import CATALOG_V2, load_catalog
from where2go.v2.dataset import dataset_summary
from where2go.v2.quality import latest_rating_pair, weak_name
from where2go.v2.storage import connect
from where2go.v2.taxonomy import CATEGORIES, FOOD_CATEGORIES


def finite_coordinate(latitude, longitude):
    return (
        isinstance(latitude, (int, float))
        and isinstance(longitude, (int, float))
        and math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def csv_rows(path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def sample(values, limit=10):
    return list(values)[:limit]


def audit(pois, manifest, catalog_path=CATALOG_V2, dataset_dir=None):
    dataset_dir = Path(dataset_dir or ROOT / "data/reports/v2/dataset")
    errors = []
    warnings = []

    def error(code, count, examples=()):
        if count:
            errors.append({"code": code, "count": count, "examples": sample(examples)})

    def warning(code, count, examples=()):
        if count:
            warnings.append({"code": code, "count": count, "examples": sample(examples)})

    ids = [poi["poi_id"] for poi in pois]
    duplicates = [ident for ident, count in Counter(ids).items() if count > 1]
    error("duplicate_canonical_id", len(duplicates), duplicates)

    by_id = {poi["poi_id"]: poi for poi in pois}
    invalid_category = [poi["poi_id"] for poi in pois if poi.get("category") not in CATEGORIES]
    error("invalid_category", len(invalid_category), invalid_category)

    invalid_coordinates = []
    invalid_access = []
    missing_service_access = []
    invalid_duration = []
    invalid_hours = []
    overlapping_hours = []
    invalid_ratings = []
    serviceable_weak_names = []
    serviceable_closed = []
    serviceable = []

    for poi in pois:
        quality = poi.get("serving_quality") or {}
        if quality.get("eligible"):
            serviceable.append(poi)
            if weak_name(poi.get("name", "")):
                serviceable_weak_names.append(poi["poi_id"])
            if poi.get("business_status") in ("temporarily_closed", "permanently_closed"):
                serviceable_closed.append(poi["poi_id"])

        latitude, longitude = poi.get("latitude"), poi.get("longitude")
        if not finite_coordinate(latitude, longitude):
            invalid_coordinates.append(poi["poi_id"])

        access_points = poi.get("access_points", [])
        if quality.get("eligible") and not access_points:
            missing_service_access.append(poi["poi_id"])
        for point in access_points:
            minutes = point.get("access_minutes")
            if (
                not finite_coordinate(point.get("latitude"), point.get("longitude"))
                or not isinstance(minutes, (int, float))
                or not 0 <= minutes <= 240
            ):
                invalid_access.append(point.get("access_id") or poi["poi_id"])

        profile = poi.get("duration_profile") or {}
        durations = [profile.get(key) for key in ("short_minutes", "typical_minutes", "long_minutes")]
        if (
            len(durations) != 3
            or not all(isinstance(value, int) for value in durations)
            or not (5 <= durations[0] <= durations[1] <= durations[2] <= 720)
        ):
            invalid_duration.append(poi["poi_id"])

        weekly = poi.get("hours_weekly")
        if weekly is not None:
            if not isinstance(weekly, list) or len(weekly) != 7:
                invalid_hours.append(poi["poi_id"])
            else:
                for day_index, day in enumerate(weekly):
                    if day is None:
                        continue
                    previous_close = None
                    for interval in sorted(day):
                        if (
                            not isinstance(interval, (tuple, list))
                            or len(interval) != 2
                            or not all(isinstance(value, int) for value in interval)
                            or not (0 <= interval[0] < 1440)
                            or not (interval[0] < interval[1] <= 2880)
                        ):
                            invalid_hours.append(f"{poi['poi_id']}:{day_index}")
                            continue
                        if previous_close is not None and interval[0] < previous_close:
                            overlapping_hours.append(f"{poi['poi_id']}:{day_index}")
                        previous_close = max(previous_close or 0, interval[1])

        for rating in poi.get("ratings", []):
            if not rating.get("same_observation"):
                continue
            value, count = rating.get("rating"), rating.get("review_count")
            if (
                not isinstance(value, (int, float))
                or not 1 <= value <= 5
                or not isinstance(count, int)
                or count < 0
            ):
                invalid_ratings.append(poi["poi_id"])

    error("invalid_poi_coordinate", len(invalid_coordinates), invalid_coordinates)
    error("invalid_access_point", len(invalid_access), invalid_access)
    error("serviceable_without_access", len(missing_service_access), missing_service_access)
    error("invalid_duration_profile", len(invalid_duration), invalid_duration)
    error("invalid_opening_interval", len(invalid_hours), invalid_hours)
    error("overlapping_opening_intervals", len(overlapping_hours), overlapping_hours)
    error("invalid_rankable_rating", len(invalid_ratings), invalid_ratings)
    error("serviceable_weak_name", len(serviceable_weak_names), serviceable_weak_names)
    error("serviceable_closed_business", len(serviceable_closed), serviceable_closed)

    missing_parents = [
        poi["poi_id"] for poi in pois
        if poi.get("parent_poi_id") and poi["parent_poi_id"] not in by_id
    ]
    self_parents = [poi["poi_id"] for poi in pois if poi.get("parent_poi_id") == poi["poi_id"]]
    error("missing_parent_poi", len(missing_parents), missing_parents)
    error("self_parent_poi", len(self_parents), self_parents)

    parent_cycles = []
    for poi in pois:
        seen = set()
        current = poi
        while current.get("parent_poi_id"):
            parent_id = current["parent_poi_id"]
            if parent_id in seen:
                parent_cycles.append(poi["poi_id"])
                break
            seen.add(parent_id)
            current = by_id.get(parent_id, {})
    error("parent_cycle", len(set(parent_cycles)), sorted(set(parent_cycles)))

    name_groups = defaultdict(list)
    coordinate_groups = defaultdict(list)
    for poi in serviceable:
        # Repeated restaurant/cafe chain names are valid branches, not enough
        # evidence of a duplicate entity. Attraction names are expected to be
        # unique within a focus location and remain useful review signals.
        if poi.get("category") not in FOOD_CATEGORIES:
            name_groups[(poi.get("location"), normalize(poi.get("name", "")))].append(poi["poi_id"])
        if finite_coordinate(poi.get("latitude"), poi.get("longitude")):
            coordinate_groups[(round(poi["latitude"], 6), round(poi["longitude"], 6))].append(poi["poi_id"])
    duplicate_names = {str(key): value for key, value in name_groups.items() if len(value) > 1}
    coordinate_clusters = {str(key): value for key, value in coordinate_groups.items() if len(value) >= 5}
    warning("duplicate_serviceable_attraction_name_in_location", len(duplicate_names), duplicate_names.items())
    warning("serviceable_coordinate_cluster_ge_5", len(coordinate_clusters), coordinate_clusters.items())

    no_hours = [poi["poi_id"] for poi in serviceable if poi.get("hours_weekly") is None]
    no_rating = [poi["poi_id"] for poi in serviceable if latest_rating_pair(poi) is None]
    unverified_duration = [
        poi["poi_id"] for poi in serviceable
        if not (poi.get("duration_profile") or {}).get("verified_at")
    ]
    unverified_access = [
        poi["poi_id"] for poi in serviceable
        if not any(point.get("verified") for point in poi.get("access_points", []))
    ]
    warning("serviceable_hours_unknown", len(no_hours), no_hours)
    warning("serviceable_rating_missing", len(no_rating), no_rating)
    warning("serviceable_duration_unverified", len(unverified_duration), unverified_duration)
    warning("serviceable_access_unverified", len(unverified_access), unverified_access)

    with closing(connect(catalog_path, readonly=True)) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = [tuple(row) for row in db.execute("PRAGMA foreign_key_check")]
    if integrity != "ok":
        error("sqlite_integrity", 1, [integrity])
    error("sqlite_foreign_key", len(foreign_keys), foreign_keys)

    summary_path = dataset_dir / "summary.json"
    export_mismatches = []
    if summary_path.exists():
        exported = json.loads(summary_path.read_text(encoding="utf-8"))
        if exported.get("dataset_version") != manifest.get("version"):
            export_mismatches.append("dataset_version")
        if exported.get("poi_count") != len(pois):
            export_mismatches.append("poi_count")
        expected = {
            "pois.csv": len(pois),
            "opening_hours.csv": exported.get("export_counts", {}).get("opening_hours.csv"),
            "ratings.csv": exported.get("export_counts", {}).get("ratings.csv"),
            "duration_profiles.csv": exported.get("export_counts", {}).get("duration_profiles.csv"),
            "access_points.csv": exported.get("export_counts", {}).get("access_points.csv"),
            "sources.csv": exported.get("export_counts", {}).get("sources.csv"),
        }
        for filename, expected_count in expected.items():
            actual = csv_rows(dataset_dir / filename)
            if actual is None or expected_count is None or actual != expected_count:
                export_mismatches.append(f"{filename}:{actual}!={expected_count}")
    else:
        export_mismatches.append("summary.json:missing")
    error("dataset_export_mismatch", len(export_mismatches), export_mismatches)

    rights = manifest.get("rights", {})
    if rights.get("Google Maps") != "restricted_internal" or rights.get("OpenStreetMap") != "ODbL-1.0":
        error("source_rights_manifest", 1, [rights])

    summary = dataset_summary(pois, manifest)
    unmet_targets = []
    for location in summary["locations"]:
        for target, passed in location["priority_set"]["target_status"].items():
            if target == "specific_duration":
                continue
            if not passed:
                unmet_targets.append(f"{location['location']}:{target}")
    warning("priority_target_not_met", len(unmet_targets), unmet_targets)

    return {
        "status": "PASS" if not errors else "FAIL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": manifest.get("version"),
        "catalog_path": str(Path(catalog_path).relative_to(ROOT)).replace("\\", "/"),
        "poi_count": len(pois),
        "serviceable_count": len(serviceable),
        "hard_error_count": sum(item["count"] for item in errors),
        "warning_count": sum(item["count"] for item in warnings),
        "errors": errors,
        "warnings": warnings,
        "coverage": summary["locations"],
        "notes": [
            "Unknown opening hours are allowed and are not treated as an error.",
            "Warnings identify enrichment and review work; they do not mean the SQLite catalog is corrupt.",
            "Google Maps observations remain restricted_internal.",
        ],
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_V2)
    parser.add_argument("--dataset-dir", type=Path, default=ROOT / "data/reports/v2/dataset")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reports/v2/dataset/audit.json")
    args = parser.parse_args()
    pois, manifest = load_catalog(args.catalog)
    report = audit(pois, manifest, args.catalog, args.dataset_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "hard_errors": report["hard_error_count"],
        "warnings": report["warning_count"],
        "output": str(args.output),
    }, ensure_ascii=False))
    raise SystemExit(1 if report["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
