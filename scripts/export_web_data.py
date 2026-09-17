"""Export the canonical catalog; never reclean legacy data or assign new IDs."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.catalog import load_catalog, filter_pois
from where2go.config import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reports/public_catalog.json")
    args = parser.parse_args()
    pois, manifest = load_catalog()
    payload = {"manifest": manifest, "pois": filter_pois(pois)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Exported {len(payload['pois'])} canonical POIs to {args.output}")


if __name__ == "__main__":
    main()
