"""Compare the delivered catalog with the preserved baseline and verify its contracts."""
import argparse
from collections import Counter
from contextlib import closing
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from where2go.api import create_app
from where2go.config import ROOT
from where2go.v2.catalog import CATALOG_V2, load_catalog
from where2go.v2.quality import explorable, itinerary_eligible, latest_rating_pair
from where2go.v2.storage import connect


def semantic_signature(catalog):
    result = {}
    with closing(connect(catalog, readonly=True)) as db:
        for table in ("pois", "selected_fields", "poi_aliases", "external_ids", "poi_images",
                      "ratings", "opening_intervals", "duration_profiles", "access_points"):
            columns = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
            digest = hashlib.sha256()
            for row in db.execute(f"SELECT * FROM {table} ORDER BY {','.join(columns)}"):
                digest.update(json.dumps(list(row), ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                digest.update(b"\n")
            result[table] = digest.hexdigest()
    return result


def report(catalog, baseline_dir, dataset_dir, output, compare=None):
    baseline = json.loads((baseline_dir / "baseline.json").read_text(encoding="utf-8"))
    pois, manifest = load_catalog(catalog)
    serviceable = [p for p in pois if itinerary_eligible(p)]
    checks = {}
    with closing(connect(baseline_dir / "catalog_v2.before.sqlite", readonly=True)) as before:
        old_ids = {r[0] for r in before.execute("SELECT poi_id FROM pois")}
    checks["preserved_canonical_ids"] = old_ids <= {p["poi_id"] for p in pois}
    checks["original_workbooks_unchanged"] = all(
        hashlib.sha256((ROOT / "data" / name).read_bytes()).hexdigest() == digest
        for name, digest in baseline["source_checksums"].items())
    summary = json.loads((dataset_dir / "summary.json").read_text(encoding="utf-8"))
    audit = json.loads((dataset_dir / "audit.json").read_text(encoding="utf-8"))
    checks["audit"] = audit["status"] == "PASS" and audit["dataset_version"] == manifest["version"]
    with (dataset_dir / "pois.csv").open(encoding="utf-8-sig", newline="") as f:
        exported = list(csv.DictReader(f))
    checks["csv_poi_count"] = len(exported) == len(pois)
    checks["csv_serviceable_count"] = sum(r["serving_eligible"].lower() in ("true", "1") for r in exported) == len(serviceable)
    with TestClient(create_app(v2_catalog_path=catalog, v2_export_dir=dataset_dir)) as client:
        checks["api_export_explore_count"] = client.get("/api/v2/pois?view=explore&limit=1").json()["total"] == summary["explorable_count"]
        checks["api_export_itinerary_count"] = client.get("/api/v2/pois?limit=1").json()["total"] == summary["serviceable_count"] == len(serviceable)
        beaches = {}
        for query, name in (("my khe", "Bãi biển Mỹ Khê"), ("pham van dong", "Bãi tắm Phạm Văn Đồng")):
            rows = client.get("/api/v2/pois", params={"view": "explore", "location": "Đà Nẵng", "query": query}).json()["pois"]
            matching = [p for p in rows if p["name"] == name]
            checks[query] = len(matching) == 1
            if matching:
                p = matching[0]
                detail = client.get(f"/api/v2/pois/{p['poi_id']}?view=explore")
                checks[query + "_detail"] = detail.status_code == 200 and bool(p.get("image"))
                beaches[name] = {key: p.get(key) for key in ("poi_id", "name", "location", "latitude", "longitude", "itinerary_eligible", "image")}
        checks["my_khe_id_preserved"] = beaches.get("Bãi biển Mỹ Khê", {}).get("poi_id") == "osm:relation:19000664"
    with closing(connect(catalog, readonly=True)) as db:
        fresh_fields = dict(db.execute("""SELECT o.field_name,count(*) FROM field_observations o
            JOIN source_records r USING(source_record_id) JOIN source_files f USING(source_file_id)
            WHERE f.role='google_collection' GROUP BY o.field_name"""))
        selected_images = dict(db.execute("""SELECT i.identity_status,count(*) FROM selected_fields s
            JOIN poi_images i ON s.observation_id=i.observation_id WHERE s.field_name='image' GROUP BY i.identity_status"""))
        image_states = dict(db.execute("SELECT validation_status,count(*) FROM poi_images GROUP BY validation_status"))
        checks["legacy_rating_pairs_not_used"] = db.execute("SELECT count(*) FROM ratings WHERE provider LIKE '%legacy%' AND same_observation=1").fetchone()[0] == 0
        checks["profile_photos_not_selected"] = db.execute("SELECT count(*) FROM selected_fields WHERE field_name='image' AND (value_json LIKE '%/ogw/%' OR value_json LIKE '%/a-/%' OR value_json LIKE '%/a/%')").fetchone()[0] == 0
        checks["foreign_keys"] = not db.execute("PRAGMA foreign_key_check").fetchall()
    collection = {}
    for batch in ("pilot", "expansion"):
        attempts = json.loads((ROOT / f"data/enrichment/{batch}.json").read_text(encoding="utf-8"))
        reviewed = json.loads((ROOT / f"data/enrichment/accepted-{batch}.json").read_text(encoding="utf-8"))
        collection[batch] = {"attempts": len(attempts), "unique_targets": len({r["record_id"] for r in attempts}),
                             "accepted": sum(r["accepted"] for r in reviewed), "held": sum(not r["accepted"] for r in reviewed),
                             "latest_statuses": dict(Counter(r["status"] for r in reviewed)), "human_verified": 0}
    signature = semantic_signature(catalog)
    if compare:
        checks["deterministic_rebuild"] = signature == json.loads(compare.read_text(encoding="utf-8"))["semantic_signature"]
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "dataset_version": manifest["version"],
              "checks": checks, "before": baseline,
              "after": {"pois": len(pois), "explorable": sum(explorable(p) for p in pois), "serviceable": len(serviceable),
                        "images": sum(bool(p.get("image")) for p in pois), "rating_pairs_serviceable": sum(bool(latest_rating_pair(p)) for p in serviceable),
                        "serviceable_missing_hours": sum(p.get("hours_weekly") is None for p in serviceable),
                        "serviceable_missing_rating_pair": sum(not latest_rating_pair(p) for p in serviceable)},
              "merge_stats": manifest["stats"], "fresh_field_observations": fresh_fields, "selected_images_by_evidence": selected_images,
              "image_validation_states": image_states, "collection": collection, "named_beaches": beaches,
              "semantic_signature": signature}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks, "after": result["after"]}, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_V2)
    parser.add_argument("--baseline", type=Path, default=ROOT / "artifacts/enrichment-20260918")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/reports/v2/dataset")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reports/v2/merge_report.json")
    parser.add_argument("--compare", type=Path, help="Previous report from an independent build with the same inputs")
    args = parser.parse_args()
    report(args.catalog, args.baseline, args.dataset, args.output, args.compare)
