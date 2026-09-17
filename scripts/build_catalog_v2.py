"""Build the v2 observation database and conservative merged catalog."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from openpyxl import load_workbook

from scripts.create_manual_template_v2 import PLACES
from scripts.inventory_sources_v2 import digest, inventory
from where2go.catalog import haversine, load_catalog
from where2go.config import CATALOG, ROOT
from where2go.ranking import normalize
from where2go.v2 import MODEL_VERSION
from where2go.v2.durations import fallback_profile
from where2go.v2.observations import (
    entity_coordinate, focus_location, normalized_entity_name, parse_rating,
    parse_review_count, scalar, stable_id,
)
from where2go.v2.storage import connect, create_database, json_text
from where2go.v2.taxonomy import canonical_category, refine_category, tags_for


GOOGLE_FILES = (
    "vietnam_destinations_google_maps_browser_hotosm.xlsx",
    "vietnam_destinations_google_maps_browser_hotosm_backup_20260915_163012.xlsx",
    "vietnam_destinations_google_maps_browser_hotosm_backup_20260916_150600.xlsx",
)


def source_time(path):
    match = __import__("re").search(r"_(\d{8})_(\d{6})", path.stem)
    if match:
        return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def add_source(db, path, role, use_status, tool):
    sha = digest(path)
    ident = stable_id("source", path.relative_to(ROOT).as_posix(), sha)
    db.execute("INSERT INTO source_files VALUES (?,?,?,?,?,?,?)", (
        ident, path.relative_to(ROOT).as_posix(), sha, role, source_time(path), tool, use_status,
    ))
    return ident


def add_record(db, source_id, source_key, payload, observed_at):
    ident = stable_id("record", source_id, source_key)
    db.execute("INSERT INTO source_records VALUES (?,?,?,?,?)", (
        ident, source_id, str(source_key), observed_at, json_text(payload),
    ))
    return ident


def observe(db, poi_id, record_id, field, value, observed_at, use_status, method, verified_at=None, notes=None):
    ident = stable_id("obs", record_id, field)
    db.execute("INSERT OR REPLACE INTO field_observations VALUES (?,?,?,?,?,?,?,?,?,?)", (
        ident, poi_id, record_id, field, json_text(value), observed_at, verified_at,
        method, use_status, notes,
    ))
    return ident


def select(db, poi_id, field, observation_id, value, reason, build_version):
    db.execute("INSERT OR REPLACE INTO selected_fields VALUES (?,?,?,?,?,?)", (
        poi_id, field, observation_id, json_text(value), reason, build_version,
    ))


def import_base(db, catalog_path, build_version):
    pois, manifest = load_catalog(catalog_path)
    source_id = add_source(db, catalog_path, "generated_catalog", "open_data", "scripts/build_catalog.py")
    name_index = defaultdict(list)
    for poi in pois:
        effective_category = refine_category(poi["category"], poi["name"], poi.get("description", ""))
        record_id = add_record(db, source_id, poi["poi_id"], poi, manifest.get("created_at"))
        db.execute("INSERT INTO pois VALUES (?,?,?,?,?,?)", (
            poi["poi_id"], poi["data_status"], poi["name"], poi.get("location") or None,
            None, "unknown",
        ))
        db.execute("INSERT INTO source_links VALUES (?,?,?,?,?,?,?)", (
            poi["poi_id"], record_id, "v1_canonical_import", 1.0, None, "confirmed", None,
        ))
        fields = {
            "name": poi["name"], "latitude": poi["latitude"], "longitude": poi["longitude"],
            "location": poi.get("location"), "category": effective_category,
            "description": poi.get("description", ""), "hours_raw": poi.get("hours_raw", ""),
            "website": poi.get("website", ""), "source_url": poi.get("source_url", ""),
        }
        observations = {}
        for field, value in fields.items():
            provenance = poi.get("provenance", {}).get(field, {})
            observations[field] = observe(
                db, poi["poi_id"], record_id, field, value,
                provenance.get("observed_at") or manifest.get("created_at"),
                "open_data", provenance.get("method", "v1_catalog_import"),
                provenance.get("verified_at"),
            )
            select(db, poi["poi_id"], field, observations[field], value, "v1 canonical baseline", build_version)
        db.execute("INSERT INTO poi_categories VALUES (?,?,1,?)", (poi["poi_id"], effective_category, observations["category"]))
        for tag in tags_for(effective_category):
            db.execute("INSERT INTO poi_categories VALUES (?,?,0,?)", (poi["poi_id"], "tag:" + tag, observations["category"]))
        profile = fallback_profile(effective_category)
        db.execute("INSERT INTO duration_profiles VALUES (?,?,?,?,?,?,?)", (
            poi["poi_id"], profile["short_minutes"], profile["typical_minutes"], profile["long_minutes"],
            profile["method"], None, None,
        ))
        db.execute("INSERT INTO access_points VALUES (?,?,?,?,?,?,?,?,?)", (
            stable_id("access", poi["poi_id"], "base"), poi["poi_id"], poi["latitude"], poi["longitude"],
            "poi_coordinate", 10, 0, poi.get("coordinate_status", "v1_coordinate"), observations["latitude"],
        ))
        weekly = poi.get("hours_intervals")
        if weekly is not None:
            for weekday, intervals in enumerate(weekly):
                if not intervals:
                    db.execute("INSERT INTO opening_intervals VALUES (?,?,?,?,?,?,?,?,?)", (
                        stable_id("hours", poi["poi_id"], weekday, "closed"), poi["poi_id"], observations["hours_raw"],
                        weekday, None, "closed", None, None, 0,
                    ))
                for start, end in intervals:
                    db.execute("INSERT INTO opening_intervals VALUES (?,?,?,?,?,?,?,?,?)", (
                        stable_id("hours", poi["poi_id"], weekday, start, end), poi["poi_id"], observations["hours_raw"],
                        weekday, None, "open", start, end if end <= 1440 else end - 1440, int(end > 1440),
                    ))
        if poi.get("location") in ("Hà Nội", "Đà Nẵng"):
            name_index[(normalize(poi["name"]), poi["location"])].append(dict(poi, category=effective_category))
    return pois, manifest, name_index


def import_osm_supplement(db, pbf_path, supplement_path, name_index, build_version):
    if not supplement_path.exists():
        raise FileNotFoundError(f"Thiếu {supplement_path}; chạy scripts/extract_osm_supplement_v2.py")
    payload = json.loads(supplement_path.read_text(encoding="utf-8"))
    source_id = add_source(db, pbf_path, "spatial_source", "open_data", "scripts/extract_osm_supplement_v2.py")
    counters = Counter()
    for row in payload["rows"]:
        record_id = add_record(db, source_id, row["poi_id"], row, row.get("observed_at"))
        peers = name_index.get((row["name_normalized"], row["location"]), [])
        duplicate = next((p for p in peers if haversine((row["latitude"], row["longitude"]),
                                                         (p["latitude"], p["longitude"])) < .15), None)
        if duplicate:
            db.execute("INSERT INTO source_links VALUES (?,?,?,?,?,?,?)", (
                duplicate["poi_id"], record_id, "exact_name_location_within_150m", 1.0,
                None, "confirmed", "supplement linked to existing canonical POI",
            ))
            counters["linked_existing"] += 1
            continue
        poi_id = row["poi_id"]
        db.execute("INSERT INTO pois VALUES (?,?,?,?,?,?)", (
            poi_id, "usable", row["name"], row["location"], None, "unknown",
        ))
        db.execute("INSERT INTO source_links VALUES (?,?,?,?,?,?,?)", (
            poi_id, record_id, "osm_source_id", 1.0, None, "confirmed", None,
        ))
        observations = {}
        for field in ("name", "latitude", "longitude", "location", "category", "description", "hours_raw", "website", "source_url"):
            value = row.get(field)
            observations[field] = observe(
                db, poi_id, record_id, field, value, row.get("observed_at"), "open_data",
                row.get("coordinate_method") if field in ("latitude", "longitude") else "osm_tag",
            )
            select(db, poi_id, field, observations[field], value, "OSM supplemental observation", build_version)
        db.execute("INSERT INTO poi_categories VALUES (?,?,1,?)", (poi_id, row["category"], observations["category"]))
        for tag in tags_for(row["category"]):
            db.execute("INSERT INTO poi_categories VALUES (?,?,0,?)", (poi_id, "tag:" + tag, observations["category"]))
        profile = fallback_profile(row["category"])
        db.execute("INSERT INTO duration_profiles VALUES (?,?,?,?,?,?,?)", (
            poi_id, profile["short_minutes"], profile["typical_minutes"], profile["long_minutes"],
            profile["method"], None, None,
        ))
        db.execute("INSERT INTO access_points VALUES (?,?,?,?,?,?,?,?,?)", (
            stable_id("access", poi_id, "base"), poi_id, row["latitude"], row["longitude"],
            "poi_coordinate", 10, 0, row["coordinate_method"], observations["latitude"],
        ))
        weekly = row.get("hours_intervals")
        if weekly is not None:
            for weekday, intervals in enumerate(weekly):
                if not intervals:
                    db.execute("INSERT INTO opening_intervals VALUES (?,?,?,?,?,?,?,?,?)", (
                        stable_id("hours", poi_id, weekday, "closed"), poi_id, observations["hours_raw"],
                        weekday, None, "closed", None, None, 0,
                    ))
                for start, end in intervals:
                    db.execute("INSERT INTO opening_intervals VALUES (?,?,?,?,?,?,?,?,?)", (
                        stable_id("hours", poi_id, weekday, start, end), poi_id, observations["hours_raw"],
                        weekday, None, "open", start, end if end <= 1440 else end - 1440, int(end > 1440),
                    ))
        canonical = {
            "poi_id": poi_id, "name": row["name"], "name_normalized": row["name_normalized"],
            "latitude": row["latitude"], "longitude": row["longitude"], "location": row["location"],
            "category": row["category"], "data_status": "usable",
        }
        name_index[(row["name_normalized"], row["location"])].append(canonical)
        counters[row["location"] + ":" + row["category"]] += 1
        counters["inserted"] += 1
    return counters


def google_rows(path):
    frame = pd.read_excel(path, dtype=object)
    for index, series in frame.iterrows():
        row = {str(key): scalar(value) for key, value in series.items()}
        yield index + 2, row


def import_google(db, paths, name_index, queue):
    counters = Counter()
    seen_ratings = set()
    for path in paths:
        source_id = add_source(db, path, "source_observation_restricted", "restricted_internal", "legacy browser collector")
        observed_at = source_time(path)
        for row_number, row in google_rows(path):
            source_key = row.get("STT") if row.get("STT") not in (None, "") else f"row:{row_number}"
            record_id = add_record(db, source_id, source_key, row, observed_at)
            location = focus_location(row.get("Vị trí"))
            name = normalized_entity_name(row)
            coordinate = entity_coordinate(row.get("maps_url"))
            reasons = []
            if row.get("maps_match_status") not in ("matched", "match", True, 1):
                reasons.append("source_not_marked_matched")
            if not location:
                reasons.append("outside_focus_or_unknown_location")
            if not name:
                reasons.append("search_results_not_entity")
            if not coordinate:
                reasons.append("missing_entity_coordinate")
            candidates = name_index.get((name, location), []) if name and location else []
            if coordinate:
                candidates = [p for p in candidates if haversine(coordinate, (p["latitude"], p["longitude"])) <= .3]
            category = canonical_category(row.get("maps_destination_type"), row.get("maps_result_name"))
            if category:
                compatible = [p for p in candidates if p["category"] == category or p["category"] == "attraction"]
                candidates = compatible or candidates
            if not reasons and len(candidates) == 1:
                poi = candidates[0]
                db.execute("INSERT INTO source_links VALUES (?,?,?,?,?,?,?)", (
                    poi["poi_id"], record_id, "exact_name_location_entity_coordinate", 1.0, None,
                    "confirmed", None,
                ))
                counters["confirmed"] += 1
                for field, value in (("google_category_raw", row.get("maps_destination_type")),
                                     ("google_hours_raw", row.get("maps_first_open_hours")),
                                     ("google_maps_url", row.get("maps_url"))):
                    if value not in (None, ""):
                        observe(db, poi["poi_id"], record_id, field, value, observed_at,
                                "restricted_internal", "legacy_google_observation")
                rating = parse_rating(row.get("Đánh giá "))
                count = parse_review_count(row.get("maps_review_count"))
                rating_key = (poi["poi_id"], rating, count, observed_at)
                if (rating is not None or count is not None) and rating_key not in seen_ratings:
                    observation = observe(db, poi["poi_id"], record_id, "rating_pair",
                                          {"rating": rating, "review_count": count, "provider": "Google Maps"},
                                          observed_at, "restricted_internal", "same_source_row")
                    db.execute("INSERT INTO ratings VALUES (?,?,?,?,?,?,?,?)", (
                        stable_id("rating", *rating_key), poi["poi_id"], "Google Maps", rating, count,
                        observed_at, int(rating is not None and count is not None), observation,
                    ))
                    seen_ratings.add(rating_key)
            else:
                status = "ambiguous" if len(candidates) > 1 else "unmatched"
                counters[status] += 1
                queue.append({
                    "source_file": path.name, "source_key": str(source_key),
                    "seed_name": row.get("Tên địa điểm"), "result_name": row.get("maps_result_name"),
                    "location": location, "status": status,
                    "candidate_poi_ids": [p["poi_id"] for p in candidates],
                    "reasons": reasons or (["multiple_candidates"] if candidates else ["no_conservative_match"]),
                })
    return counters


def import_manual(db, path, queue):
    if not path.exists():
        return Counter(missing=1)
    workbook = load_workbook(path, read_only=True, data_only=True)
    headers = [cell.value for cell in workbook["places"][1]]
    if headers != PLACES:
        raise ValueError("Manual workbook headers do not match v2 schema")
    source_id = add_source(db, path, "manual_observation", "manual_fact_with_source", "manual workbook")
    counters = Counter()
    for row_number, values in enumerate(workbook["places"].iter_rows(min_row=2, values_only=True), 2):
        row = {key: scalar(value) for key, value in zip(headers, values)}
        if not any(value not in (None, "") for value in row.values()):
            continue
        record_id = add_record(db, source_id, row["record_id"], row, row.get("observed_at"))
        poi_id = str(row.get("canonical_poi_id") or "").strip()
        exists = poi_id and db.execute("SELECT 1 FROM pois WHERE poi_id=?", (poi_id,)).fetchone()
        if exists and row.get("maps_name") and row.get("maps_url"):
            db.execute("INSERT INTO source_links VALUES (?,?,?,?,?,?,?)", (
                poi_id, record_id, "manual_workbook_pending_verification", None, row.get("reviewer"),
                "ambiguous", "Verification sheet must confirm identity",
            ))
            counters["pending_verification"] += 1
        else:
            counters["seed_only"] += 1
        if row.get("maps_name") or row.get("maps_url"):
            queue.append({"source_file": path.name, "source_key": row["record_id"], "status": "ambiguous",
                          "candidate_poi_ids": [poi_id] if exists else [], "reasons": ["manual_verification_required"]})
    return counters


def coverage(db):
    result = []
    for location in ("Hà Nội", "Đà Nẵng"):
        total = db.execute("SELECT count(*) FROM pois WHERE location=?", (location,)).fetchone()[0]
        usable = db.execute("SELECT count(*) FROM pois WHERE location=? AND status='usable'", (location,)).fetchone()[0]
        ratings = db.execute("SELECT count(DISTINCT r.poi_id) FROM ratings r JOIN pois p ON p.poi_id=r.poi_id WHERE p.location=? AND r.same_observation=1", (location,)).fetchone()[0]
        hours = db.execute("SELECT count(DISTINCT h.poi_id) FROM opening_intervals h JOIN pois p ON p.poi_id=h.poi_id WHERE p.location=?", (location,)).fetchone()[0]
        food = db.execute("SELECT count(DISTINCT p.poi_id) FROM pois p JOIN poi_categories c ON c.poi_id=p.poi_id AND c.is_primary=1 WHERE p.location=? AND p.status='usable' AND c.category IN ('restaurant','cafe','food_street')", (location,)).fetchone()[0]
        attractions = usable - food
        result.append({"location": location, "total": total, "usable": usable,
                       "attractions": attractions, "food_rest": food, "with_rating_pair": ratings,
                       "with_structured_hours": hours, "with_specific_duration": 0,
                       "targets": {"attractions": 50, "food_rest": 20, "hours_percent": 80, "specific_duration_percent": 80}})
    return result


def pipeline_hash(paths):
    hasher = hashlib.sha256()
    for path in sorted(paths, key=lambda item: str(item)):
        hasher.update(str(path.relative_to(ROOT)).encode())
        hasher.update(digest(path).encode())
    return hasher.hexdigest()


def build(args):
    input_paths = [args.v1_catalog, args.pbf, args.supplement, *args.google]
    if args.manual.exists():
        input_paths.append(args.manual)
    code_paths = [Path(__file__), ROOT / "where2go/v2/storage.py", ROOT / "where2go/v2/observations.py",
                  ROOT / "where2go/v2/taxonomy.py", ROOT / "where2go/v2/durations.py"]
    input_hash = pipeline_hash(input_paths + code_paths)
    build_version = "v2-" + input_hash[:16]
    create_database(args.output)
    review_queue = []
    with closing(connect(args.output)) as db:
        pois, v1_manifest, name_index = import_base(db, args.v1_catalog, build_version)
        supplement_stats = import_osm_supplement(db, args.pbf, args.supplement, name_index, build_version)
        google_stats = import_google(db, args.google, name_index, review_queue)
        manual_stats = import_manual(db, args.manual, review_queue)
        stats = {
            "poi_count": db.execute("SELECT count(*) FROM pois").fetchone()[0],
            "osm_supplement": dict(supplement_stats), "google": dict(google_stats), "manual": dict(manual_stats),
            "review_queue": len(review_queue), "focus_coverage": coverage(db),
        }
        db.execute("INSERT INTO builds VALUES (?,?,?,?,?)", (
            build_version, datetime.now(timezone.utc).isoformat(), input_hash, MODEL_VERSION, json_text(stats),
        ))
        manifest = {
            "version": build_version, "created_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "2.0", "model_version": MODEL_VERSION, "input_hash": input_hash,
            "v1_dataset_version": v1_manifest["version"], "osm": v1_manifest["osm"], "stats": stats,
            "rights": {"Google Maps": "restricted_internal", "OpenStreetMap": "ODbL-1.0"},
        }
        db.execute("INSERT INTO metadata VALUES ('manifest',?)", (json_text(manifest),))
        db.commit()
        foreign = db.execute("PRAGMA foreign_key_check").fetchall()
        if foreign:
            raise RuntimeError(f"Foreign key errors: {foreign[:5]}")
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.report_dir / "coverage.json").write_text(json.dumps(stats["focus_coverage"], ensure_ascii=False, indent=2), encoding="utf-8")
    (args.report_dir / "review_queue.json").write_text(json.dumps(review_queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"version": build_version, **stats}, ensure_ascii=False))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-catalog", type=Path, default=CATALOG)
    parser.add_argument("--pbf", type=Path, default=ROOT / "data/raw/vietnam-260915.osm.pbf")
    parser.add_argument("--supplement", type=Path, default=ROOT / "data/cache/osm_supplement_v2.json")
    parser.add_argument("--google", type=Path, nargs="*", default=[ROOT / "data" / name for name in GOOGLE_FILES])
    parser.add_argument("--manual", type=Path, default=ROOT / "data/manual/poi_enrichment_v2.xlsx")
    parser.add_argument("--output", type=Path, default=ROOT / "data/catalog_v2.sqlite")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "data/reports/v2/catalog")
    build(parser.parse_args())


if __name__ == "__main__":
    main()
