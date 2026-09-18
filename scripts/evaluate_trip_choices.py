"""Paired real-OSRM scenarios for legacy planning and selection-first suggestions."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.routing import OSRM
from where2go.v2.catalog import load_catalog, CATALOG_V2
from where2go.v2.models import ItineraryRequestV2
from where2go.v2.quality import manual_trip_quality, recommendation_eligible
from where2go.v2.service import ItineraryService
from where2go.v2.trip_models import TripSuggestionRequest


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/reports/v2/trip_choices_evaluation.json")
    args = parser.parse_args()
    pois, manifest = load_catalog(CATALOG_V2)
    router = OSRM()
    service = ItineraryService(pois, manifest, router)
    centers = {"Đà Nẵng": {"latitude": 16.0544, "longitude": 108.2022}, "Hà Nội": {"latitude": 21.0285, "longitude": 105.8542}}
    beach = "osm:relation:19000664"
    pvd = "poi-google:9f6b613e52c6d0f34461666b"
    scenarios = [
        ("dn_single_without_metadata", "Đà Nẵng", [pvd], "08:00", "18:00", {}),
        ("dn_two_beaches", "Đà Nẵng", [beach, pvd], "08:00", "18:00", {}),
        ("dn_short_window", "Đà Nẵng", [beach, pvd], "08:00", "09:00", {beach: 90, pvd: 60}),
        ("hn_one_temple", "Hà Nội", ["osm:way:28912942"], "08:00", "12:00", {}),
        ("hn_culture", "Hà Nội", ["osm:way:340128580", "osm:way:704147278", "osm:way:178995262"], "08:00", "18:00", {}),
        ("hn_afternoon_museums", "Hà Nội", ["osm:way:339936730", "osm:way:340128580", "osm:way:704147278"], "13:00", "18:00", {}),
    ]
    food = next(p for p in pois if p["location"] == "Đà Nẵng" and p["category"] == "restaurant" and recommendation_eligible(p))
    scenarios.append(("dn_food_only", "Đà Nẵng", [food["poi_id"]], "11:30", "14:00", {}))
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "dataset_version": manifest["version"],
              "routing_version": router.version, "scope": "Seven targeted scenarios, not a representative quality benchmark; old planner may add unselected places.",
              "human_usability": "NOT RUN", "scenarios": []}
    for name, city, ids, start, end, overrides in scenarios:
        common = {"start": centers[city], "date": "2026-09-20", "location": city, "start_time": start, "end_time": end,
                  "include_meals": True, "duration_overrides": overrides}
        began = perf_counter()
        old = service.plan(ItineraryRequestV2.model_validate({**common, "required_poi_ids": ids}))
        old_ms = (perf_counter() - began) * 1000
        new = service.suggest(TripSuggestionRequest.model_validate({**common, "selected_poi_ids": ids, "must_visit_poi_ids": ids}))
        options = new["options"]
        old_used = {b["poi_id"] for b in old.get("blocks", []) if b.get("poi_id")}
        summary = {"scenario": name, "location": city, "selected_poi_ids": ids,
                   "legacy": {"status": old["status"], "reason": old["reason"], "has_schedule": bool(old.get("geometry")),
                              "must_fraction": len(set(ids) & old_used) / len(ids), "elapsed_ms": round(old_ms, 1)},
                   "suggestions": {"status": new["status"], "has_schedule": bool(options), "has_next_step": bool(options or new["actions"]),
                                   "elapsed_ms": new["elapsed_ms"], "best_must_fraction": max((o["coverage"]["must"] / len(ids) for o in options), default=0),
                                   "full_must_without_time_change": any(o["all_must_visits"] and not o["changes"] for o in options),
                                   "options": [{"profile": o["profile"], "selected": o["coverage"]["selected"], "must": o["coverage"]["must"],
                                                "departure": o["start_time"], "return": o["return_time"], "drive_minutes": round(o["drive_seconds"] / 60, 1),
                                                "requires_confirmation": o["requires_confirmation"], "changes": o["changes"]} for o in options]}}
        for o in options:
            timeline = o["timeline"]
            assert all(a["end_seconds"] <= b["start_seconds"] for a, b in zip(timeline, timeline[1:]))
            assert abs(sum(leg["duration"] for leg in o["legs"]) - o["drive_seconds"]) < .001
        result["scenarios"].append(summary)
        print(name, old["status"], "->", new["status"], len(options), flush=True)
    n = len(scenarios)
    result["summary"] = {
        "scenario_count": n,
        "legacy_schedule_count": sum(r["legacy"]["has_schedule"] for r in result["scenarios"]),
        "new_schedule_count": sum(r["suggestions"]["has_schedule"] for r in result["scenarios"]),
        "new_actionable_count": sum(r["suggestions"]["has_next_step"] for r in result["scenarios"]),
        "new_full_must_original_window": sum(r["suggestions"]["full_must_without_time_change"] for r in result["scenarios"]),
        "new_full_must_any_window": sum(r["suggestions"]["best_must_fraction"] == 1 for r in result["scenarios"]),
        "legacy_median_ms": statistics.median(r["legacy"]["elapsed_ms"] for r in result["scenarios"]),
        "new_median_ms": statistics.median(r["suggestions"]["elapsed_ms"] for r in result["scenarios"]),
        "new_max_ms": max(r["suggestions"]["elapsed_ms"] for r in result["scenarios"]),
        "timeline_route_consistency": "PASS",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    run()
