"""Create a machine-assisted identity review report for Google pilot results."""
import argparse
import csv
from difflib import SequenceMatcher
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.catalog import haversine
from where2go.ranking import normalize
from where2go.v2.catalog import load_catalog


def location_matches(expected, address):
    text = normalize(address or "")
    if expected == "Hà Nội":
        return "ha noi" in text
    return any(token in text for token in ("da nang", "hoi an", "quang nam"))


def name_score(seed, result):
    a, b = normalize(seed), normalize(result)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if min(len(a), len(b)) >= 6 and (a in b or b in a):
        return 0.95
    return round(SequenceMatcher(None, a, b).ratio(), 4)


def review(input_path, output_csv, output_json):
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    catalog = {poi["poi_id"]: poi for poi in load_catalog()[0]}
    review_rows = []
    for row in rows:
        place = row.get("place") or {}
        score = name_score(row.get("seed_name"), place.get("name"))
        url = place.get("google_maps_url") or place.get("url") or ""
        resolved_place = bool(place.get("place_id") or "/maps/place/" in url)
        location_ok = location_matches(row.get("location_expected"), " ".join(filter(None, (place.get("address"), url))))
        canonical = catalog.get(row.get("canonical_poi_id"))
        distance_km = None
        if canonical and place.get("latitude") is not None and place.get("longitude") is not None:
            distance_km = round(haversine(
                (canonical["latitude"], canonical["longitude"]),
                (place["latitude"], place["longitude"]),
            ), 4)
        coordinate_match = distance_km is not None and distance_km <= 1.0
        resolved_distance = row.get("resolve_distance_km")
        try:
            resolved_distance = float(resolved_distance) if resolved_distance not in (None, "") else None
        except (TypeError, ValueError):
            resolved_distance = None
        trusted_resolution = bool(
            row.get("resolve_method") == "search_anchor_name_and_osm_proximity"
            and (resolved_distance is not None or score >= .72)
        )
        machine_match = bool(
            row.get("success") and resolved_place
            and (score >= .72 or trusted_resolution)
            and (location_ok or coordinate_match or resolved_distance is not None)
        )
        review_rows.append({
            "record_id": row.get("record_id"), "canonical_poi_id": row.get("canonical_poi_id"),
            "seed_name": row.get("seed_name"), "result_name": place.get("name") or "",
            "location_expected": row.get("location_expected"), "address": place.get("address") or "",
            "name_score": score, "location_match": location_ok, "machine_match": machine_match,
            "resolved_place": resolved_place,
            "coordinate_distance_km": distance_km if distance_km is not None else "",
            "coordinate_match": coordinate_match,
            "resolve_method": row.get("resolve_method") or "",
            "trusted_resolution": trusted_resolution,
            "rating": place.get("rating") if place else "", "review_count": place.get("review_count") if place else "",
            "has_hours": bool(place.get("hours")), "maps_url": place.get("google_maps_url") or place.get("url") or "",
            "human_identity_status": "", "human_reviewer": "", "human_notes": "",
        })
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]) if review_rows else [])
        if review_rows:
            writer.writeheader(); writer.writerows(review_rows)
    machine_matches = sum(row["machine_match"] for row in review_rows)
    summary = {
        "results": len(review_rows), "successful": sum(bool(row.get("success")) for row in rows),
        "machine_matches": machine_matches,
        "machine_match_percent": round(100 * machine_matches / len(review_rows), 2) if review_rows else 0,
        "human_reviewed": 0, "human_precision_percent": None,
        "expansion_gate": "NOT_RUN",
        "note": "Machine match is triage only. The 95% expansion gate requires human review.",
    }
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/google-pilot/results.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/google-pilot/review.csv")
    parser.add_argument("--report", type=Path, default=ROOT / "data/google-pilot/review_summary.json")
    args = parser.parse_args()
    print(json.dumps(review(args.input, args.output, args.report), ensure_ascii=False))


if __name__ == "__main__":
    main()
