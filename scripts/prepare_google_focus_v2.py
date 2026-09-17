"""Prepare a deterministic Google enrichment queue for curated focus landmarks."""
import argparse
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT


def prepare(curation_path, output_dir, limit=None, overrides_path=None):
    overrides = {}
    if overrides_path and overrides_path.exists():
        with overrides_path.open(encoding="utf-8-sig", newline="") as handle:
            overrides = {row["record_id"]: row["query"] for row in csv.DictReader(handle)}
    with curation_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: (int(row.get("priority") or 99), row["record_id"]))
    if limit is not None:
        rows = rows[:limit]
    seeds = []
    for row in rows:
        seeds.append({
            "record_id": row["record_id"],
            "canonical_poi_id": row.get("canonical_poi_id") or "",
            "seed_name": row["seed_name"],
            "location_expected": row["location_expected"],
            "expected_category": row.get("expected_category") or "",
            "query": overrides.get(row["record_id"]) or f"{row['seed_name']}, {row['location_expected']}, Việt Nam",
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "seeds.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(seeds[0]) if seeds else [
            "record_id", "canonical_poi_id", "seed_name", "location_expected", "expected_category", "query",
        ])
        writer.writeheader()
        writer.writerows(seeds)
    (output_dir / "queries.txt").write_text(
        "".join(f"{row['query']} #!#{row['record_id']}\n" for row in seeds), encoding="utf-8"
    )
    return seeds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curation", type=Path, default=ROOT / "data/curation/focus_landmarks_v2.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/google-focus")
    parser.add_argument("--overrides", type=Path, default=ROOT / "data/curation/google_query_overrides_v2.csv")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    rows = prepare(args.curation, args.output_dir, args.limit, args.overrides)
    print(f"Prepared {len(rows)} curated focus queries in {args.output_dir}")


if __name__ == "__main__":
    main()
