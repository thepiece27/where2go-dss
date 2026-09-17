"""Record road/snap checks for every eligible POI in both focus cities; not field verification."""
import json
import csv
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.catalog import load_catalog
from where2go.config import ROOT, SNAP_LIMIT_METERS
from where2go.routing import OSRM
from scripts.build_catalog import write_json


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    pois, manifest = load_catalog()
    router = OSRM()
    if router.manifest.get("pbf_sha256") != manifest["osm"]["sha256"]:
        raise SystemExit("OSRM snapshot mismatch/unavailable")
    rows = []
    summaries = []
    for city, start in [("Hà Nội", (21.0285, 105.8542)), ("Đà Nẵng", (16.0612, 108.2227))]:
        selected = [p for p in pois if p["location"] == city and p["data_status"] == "usable"]
        local = []
        for offset in range(0, len(selected), 60):
            batch = selected[offset:offset+60]
            matrix = router.table([start] + [(p["latitude"], p["longitude"]) for p in batch])
            for i, p in enumerate(batch, 1):
                snap = matrix["sources"][i]["distance"] if matrix else None
                routable = bool(matrix and matrix["durations"][0][i] is not None and matrix["durations"][i][0] is not None and snap <= SNAP_LIMIT_METERS)
                reason = "passed" if routable else ("snap_too_far" if snap is not None and snap > SNAP_LIMIT_METERS else "no_round_trip_route")
                local.append({"poi_id": p["poi_id"], "name": p["name"], "location": city,
                              "category": p["category"], "source_url": p["source_url"],
                              "latitude": p["latitude"], "longitude": p["longitude"],
                              "hours_status": p["hours_status"], "hours_raw": p["hours_raw"],
                              "snap_distance_meters": snap, "round_trip_routable": routable, "routing_reason": reason,
                              "source_review": p["review"], "field_verified": False})
            print(city, min(offset+60, len(selected)), "/", len(selected), flush=True)
        rows.extend(local)
        summaries.append({"location": city, "tested": len(local), "routable": sum(r["round_trip_routable"] for r in local),
                          "reviewed_and_routable": sum(bool(r["source_review"]) and r["round_trip_routable"] for r in local)})
    report = {"dataset_version": manifest["version"], "routing_version": router.version,
              "checked_at": datetime.now(timezone.utc).isoformat(), "method": "automated_OSRM_and_assisted_source_review_not_fieldwork",
              "summary": summaries, "pois": rows}
    write_json(ROOT / "data/reports/routing_audit.json", report)
    write_json(ROOT / "data/reports/reviewed_sample.json", {**{k:v for k,v in report.items() if k != "pois"},
                                                           "pois": [r for r in rows if r["source_review"]]})
    # This work queue prioritizes evidence gathering; no missing value is invented.
    by_id = {p["poi_id"]: p for p in pois}
    tasks = []
    for row in rows:
        p = by_id[row["poi_id"]]
        fields = []
        if not row["round_trip_routable"]:
            fields.append("road_access:" + row["routing_reason"])
        if p["coordinate_status"] != "osm_point":
            fields.append("verified_entrance")
        if p["hours_status"] == "unknown":
            fields.append("opening_hours")
        if not p["review"]:
            fields.append("independent_source_review")
        if not p.get("description"):
            fields.append("factual_description")
        if fields:
            tasks.append({"priority": 1 if p["review"] and row["round_trip_routable"] else 2 if row["round_trip_routable"] else 3,
                          "poi_id": p["poi_id"], "name": p["name"], "location": p["location"], "category": p["category"],
                          "latitude": p["latitude"], "longitude": p["longitude"], "fields_to_check": "|".join(fields), "source_url": p["source_url"]})
    tasks.sort(key=lambda r: (r["priority"], r["location"], r["poi_id"]))
    with (ROOT / "data/reports/enrichment_queue.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["priority","poi_id","name","location","category","latitude","longitude","fields_to_check","source_url"])
        writer.writeheader()
        writer.writerows(tasks)
    print(json.dumps(summaries, ensure_ascii=False))
    if any(r["reviewed_and_routable"] < 25 for r in summaries):
        raise SystemExit("Fewer than 25 source-reviewed routable POIs in a focus city")


if __name__ == "__main__": main()
