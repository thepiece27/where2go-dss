"""Review entity identity against OSM position/geometry and explicit digital-source decisions."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shapely.geometry import Point, shape
from where2go.config import ROOT
from where2go.catalog import haversine
from where2go.v2.catalog import load_catalog, CATALOG_V2
from where2go.v2.google_collector import entity_coordinate, google_identity, name_similarity
from where2go.v2.quality import weak_name
from where2go.v2.taxonomy import canonical_category
from scripts.merge_sources_v2 import compatible


def review(input_path, output, report, catalog):
    latest = {r["record_id"]: r for r in json.loads(input_path.read_text(encoding="utf-8"))}
    pois = {p["poi_id"]: p for p in load_catalog(catalog)[0]}
    geo_path = ROOT / "data/cache/poi_geometries_v2.json"
    geometries = json.loads(geo_path.read_text(encoding="utf-8")).get("geometries", {}) if geo_path.exists() else {}
    decisions_path = ROOT / "data/curation/collection_identity_reviews_v2.csv"
    decisions = {}
    if decisions_path.exists():
        with decisions_path.open(encoding="utf-8-sig") as f:
            decisions = {r["record_id"]: r for r in csv.DictReader(f)}
    reviewed = []
    for row in latest.values():
        p = row.get("place") or {}
        url = p.get("google_maps_url") or p.get("url")
        coord, external = entity_coordinate(url), google_identity(url)
        poi = pois.get(row.get("canonical_poi_id"))
        decision = decisions.get(row["record_id"], {})
        accepted = False
        evidence = {}
        if coord and external and not weak_name(p.get("name")):
            if decision.get("decision") == "accepted" and decision.get("external_id") == external:
                accepted = True
                evidence = {"method": decision["verification_method"], "evidence_url": decision["evidence_url"], "notes": decision["notes"]}
            elif poi:
                names = [poi["name"], *poi.get("aliases", []), row.get("seed_name", "")]
                score = max(name_similarity(n, p.get("name")) for n in names)
                distance = haversine(coord, (poi["latitude"], poi["longitude"]))
                area = geometries.get(poi["poi_id"])
                contained = bool(area and shape(area).covers(Point(coord[1], coord[0])))
                accepted = (score == 1 and (distance <= .3 or contained)
                            and compatible(canonical_category(p.get("category"), p.get("name")), poi.get("category")))
                evidence = {"method": "name_and_independent_osm_position", "name_score": score,
                            "distance_km": distance, "within_osm_area": contained, "evidence_url": poi.get("source_url")}
        if row.get("status") in ("blocked", "transient_error", "unresolved"):
            accepted = False
        row = dict(row, accepted=accepted, review_evidence=json.dumps(evidence, ensure_ascii=False),
                   identity={**row.get("identity", {}), "status": "tool_confirmed" if accepted else "needs_review"}, reviewer="tool:cross_source_review")
        reviewed.append(row)
    accepted = sum(r["accepted"] for r in reviewed)
    summary = {"unique_results": len(reviewed), "accepted": accepted, "needs_review": len(reviewed)-accepted,
               "accepted_percent": round(100 * accepted / len(reviewed), 2) if reviewed else 0,
               "with_image": sum(bool((r.get("place") or {}).get("image_url")) for r in reviewed if r["accepted"]),
               "status_counts": dict(Counter(r["status"] for r in reviewed)), "human_verified": 0,
               "expansion_gate": ("PASS" if accepted >= 19 else "NOT_PASSED") if len(reviewed) == 20 else "NOT_APPLICABLE",
               "method": "Tool cross-check against OSM plus explicit source decisions; not field verification"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reviewed, ensure_ascii=False, indent=2), encoding="utf-8")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=CATALOG_V2)
    args = parser.parse_args()
    review(args.input, args.output, args.report, args.catalog)
