"""Export deterministic 50-attraction/20-food priority sets and their evidence gaps."""
import argparse
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.v2.catalog import CATALOG_V2, load_catalog


def latest_rating(poi):
    rows = [row for row in poi["ratings"] if row["same_observation"]]
    return max(rows, key=lambda row: row.get("observed_at") or "") if rows else None


def evidence_score(poi):
    rating = latest_rating(poi)
    access = poi["access_points"][0] if poi["access_points"] else None
    score = 0
    score += 4 if rating else 0
    score += 3 if poi["hours_weekly"] is not None else 0
    score += 2 if poi.get("website") else 0
    score += 1 if access and access["method"] == "osm_point" else 0
    score += 1 if poi.get("description") else 0
    return score


def select(pois, location, food, limit):
    pool = [poi for poi in pois if poi["location"] == location and poi["data_status"] == "usable"
            and poi["serving_quality"]["eligible"] and poi["is_food"] == food]
    pool.sort(key=lambda poi: (-evidence_score(poi), poi["category"], poi["poi_id"]))
    selected, category_counts = [], {}
    while len(selected) < min(limit, len(pool)):
        remaining = [poi for poi in pool if poi not in selected]
        if not remaining:
            break
        poi = min(remaining, key=lambda item: (category_counts.get(item["category"], 0), -evidence_score(item), item["poi_id"]))
        selected.append(poi)
        category_counts[poi["category"]] = category_counts.get(poi["category"], 0) + 1
    return selected


def export(catalog, output):
    pois, manifest = load_catalog(catalog)
    rows = []
    for location in ("Hà Nội", "Đà Nẵng"):
        for kind, food, limit in (("attraction", False, 50), ("food_rest", True, 20)):
            for rank, poi in enumerate(select(pois, location, food, limit), 1):
                rating = latest_rating(poi)
                gaps = []
                if poi["hours_weekly"] is None: gaps.append("opening_hours")
                if poi["duration_profile"]["method"] == "category_default": gaps.append("specific_duration")
                if not any(point["verified"] for point in poi["access_points"]): gaps.append("verified_access")
                if not rating: gaps.append("rating_pair")
                rows.append({
                    "location": location, "set": kind, "priority_rank": rank, "poi_id": poi["poi_id"],
                    "name": poi["name"], "category": poi["category"], "evidence_score": evidence_score(poi),
                    "rating": rating["rating"] if rating else "", "review_count": rating["review_count"] if rating else "",
                    "hours_known": poi["hours_weekly"] is not None,
                    "duration_method": poi["duration_profile"]["method"],
                    "access_verified": any(point["verified"] for point in poi["access_points"]),
                    "serving_evidence_count": poi["serving_quality"]["evidence_count"],
                    "review_status": "needs_manual_review" if gaps else "data_complete_not_field_verified",
                    "missing_fields": "|".join(gaps), "dataset_version": manifest["version"],
                })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_V2)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reports/v2/priority_set.csv")
    args = parser.parse_args()
    rows = export(args.catalog, args.output)
    print(f"Exported {len(rows)} priority rows to {args.output}")


if __name__ == "__main__":
    main()
