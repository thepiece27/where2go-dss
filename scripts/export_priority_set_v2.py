"""Export deterministic 50-attraction/20-food priority sets and their evidence gaps."""
import argparse
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.v2.catalog import CATALOG_V2, load_catalog
from where2go.v2.dataset import evidence_score, select_priority


def latest_rating(poi):
    rows = [row for row in poi["ratings"] if row["same_observation"]]
    return max(rows, key=lambda row: row.get("observed_at") or "") if rows else None



def select(pois, location, food, limit):
    return select_priority(pois, location, food, limit)

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
