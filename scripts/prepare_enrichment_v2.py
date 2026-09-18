"""Build a deduplicated, bounded collection queue from landmarks and priority POIs."""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.v2.catalog import load_catalog, CATALOG_V2
from where2go.v2.dataset import select_priority
from where2go.v2.google_collector import google_identity
from where2go.v2.quality import latest_rating_pair


def missing_fields(poi):
    weekly = poi.get("hours_weekly")
    return [field for field, present in {
        "image": bool(poi.get("image")), "weekly_hours": weekly is not None and all(day is not None for day in weekly),
        "rating_pair": bool(latest_rating_pair(poi)), "address": bool(poi.get("address_raw")),
        "website": bool(poi.get("website")),
    }.items() if not present]


def prepare(catalog, output):
    pois, _ = load_catalog(catalog)
    by_id = {p["poi_id"]: p for p in pois}
    with sqlite3.connect(f"file:{catalog.as_posix()}?mode=ro", uri=True) as db:
        known = {}
        for poi_id, field, value in db.execute("SELECT poi_id,field_name,value_json FROM field_observations WHERE field_name IN ('google_maps_url','google_place_id') AND verification_method LIKE '%manual%'"):
            known.setdefault(poi_id, {})[field] = json.loads(value)
    rows = [{"record_id": "landmark-pham-van-dong", "canonical_poi_id": "", "seed_name": "Bãi tắm Phạm Văn Đồng",
             "aliases": ["Pham Van Dong Beach", "Bãi biển Phạm Văn Đồng"], "location_expected": "Đà Nẵng",
             "expected_category": "beach", "query": "Bãi tắm Phạm Văn Đồng Đà Nẵng Việt Nam"}]
    beach = next((p for p in pois if p["name"] == rows[0]["seed_name"] and p.get("location") == "Đà Nẵng"), {})
    rows[0].update(canonical_poi_id=beach.get("poi_id", ""), latitude=beach.get("latitude"),
                   longitude=beach.get("longitude"), missing_fields=missing_fields(beach))
    if not rows[0]["missing_fields"]:
        rows.clear()
    with (ROOT / "data/curation/focus_landmarks_v2.csv").open(encoding="utf-8-sig") as f:
        landmarks = sorted(csv.DictReader(f), key=lambda r: (r["location_expected"] != "Đà Nẵng", r["seed_name"] != "Bãi biển Mỹ Khê", r["record_id"]))
    seen = {beach["poi_id"]} if beach else set()
    for row in landmarks:
        poi = by_id.get(row.get("canonical_poi_id"), {})
        ident = poi.get("poi_id") or row["record_id"]
        if ident in seen:
            continue
        seen.add(ident)
        gaps = missing_fields(poi)
        if not gaps:
            continue
        source = known.get(ident, {})
        url = source.get("google_maps_url")
        rows.append({"record_id": row["record_id"], "canonical_poi_id": poi.get("poi_id", ""),
                     "seed_name": row["seed_name"], "location_expected": row["location_expected"],
                     "expected_category": row["expected_category"], "query": row["seed_name"] + ", " + row["location_expected"] + ", Việt Nam",
                     "aliases": sorted(set([poi.get("name", ""), *poi.get("aliases", [])]) - {""}), "missing_fields": gaps,
                     "latitude": poi.get("latitude"), "longitude": poi.get("longitude"),
                     "maps_url": url, "expected_place_id": source.get("google_place_id") or google_identity(url)})
    for location in ("Đà Nẵng", "Hà Nội"):
        for food, limit in ((False, 50), (True, 20)):
            for poi in select_priority(pois, location, food, limit):
                if poi["poi_id"] in seen:
                    continue
                seen.add(poi["poi_id"])
                gaps = missing_fields(poi)
                if not gaps:
                    continue
                rows.append({"record_id": "missing:" + poi["poi_id"], "canonical_poi_id": poi["poi_id"],
                             "seed_name": poi["name"], "aliases": poi.get("aliases", []), "location_expected": location, "missing_fields": gaps,
                             "expected_category": poi["category"], "latitude": poi["latitude"], "longitude": poi["longitude"],
                             "query": poi["name"] + ", " + location + ", Việt Nam"})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows[:200], ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"seeds": len(rows[:200]), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_V2)
    parser.add_argument("--output", type=Path, default=ROOT / "data/enrichment/seeds.json")
    args = parser.parse_args()
    prepare(args.catalog, args.output)
