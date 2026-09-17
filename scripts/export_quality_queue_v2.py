"""Export POIs present in the v2 catalog but blocked by serving-quality gates."""
import argparse
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.v2.catalog import CATALOG_V2, load_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_V2)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reports/v2/quality_queue.csv")
    args = parser.parse_args()
    pois, manifest = load_catalog(args.catalog)
    rows = []
    for poi in pois:
        quality = poi["serving_quality"]
        if poi["location"] not in ("Hà Nội", "Đà Nẵng") or quality["eligible"]:
            continue
        rows.append({
            "poi_id": poi["poi_id"], "name": poi["name"], "location": poi["location"],
            "category": poi["category"], "reasons": "|".join(quality["reasons"]),
            "evidence_count": quality["evidence_count"],
            "source_url": poi.get("source_url", ""), "dataset_version": manifest["version"],
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["poi_id", "name", "location", "category", "reasons", "evidence_count", "source_url", "dataset_version"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f"Exported {len(rows)} blocked POIs to {args.output}")


if __name__ == "__main__":
    main()
