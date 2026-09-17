"""Inventory Where2Go data files by role without modifying source artifacts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT


OUTPUT_NAMES = {
    "chronological_metrics.xlsx", "chronological_summary.xlsx",
    "poi_evaluation_metrics.xlsx", "poi_sample_recommendations.xlsx",
}


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def role(path):
    name = path.name.lower()
    relative = path.relative_to(ROOT / "data").as_posix()
    if path.suffix.lower() in {".pbf", ".osm"} or "provinces" in name:
        return "spatial_source"
    if relative.startswith("curation/"):
        return "curation_input"
    if relative.startswith(("raw/", "routing/", "cache/", "private/")):
        return "runtime_or_private"
    if relative.startswith("reports/") or name in OUTPUT_NAMES:
        return "generated_report"
    if "synthetic_user_behavior" in name:
        return "synthetic_fixture"
    if "cleaned" in name:
        return "derived_crosscheck"
    if "google_maps" in name or "hotosm" in name:
        return "source_observation_restricted"
    if name == "vietnam_destinations.xlsx":
        return "source_observation"
    if name.startswith("catalog") and path.suffix == ".sqlite":
        return "generated_catalog"
    if relative.startswith("manual/"):
        return "manual_observation"
    return "unclassified"


def use_status(file_role):
    return {
        "source_observation_restricted": "restricted_internal",
        "manual_observation": "manual_fact_with_source",
        "spatial_source": "license_check_required",
        "runtime_or_private": "not_for_publication",
    }.get(file_role, "project_internal")


def inventory(data_dir):
    rows = []
    for path in sorted(p for p in data_dir.rglob("*") if p.is_file()):
        if path.name.startswith("~$") or path.suffix.lower() in {".tmp", ".lock", ".pyc"}:
            continue
        file_role = role(path)
        stat = path.stat()
        rows.append({
            "logical_path": path.relative_to(ROOT).as_posix(),
            "size_bytes": stat.st_size,
            "sha256": digest(path),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "role": file_role,
            "use_status": use_status(file_role),
        })
    return rows


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reports/v2/source_manifest.json")
    args = parser.parse_args()
    rows = inventory(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": "data",
        "files": rows,
        "counts_by_role": {key: sum(r["role"] == key for r in rows) for key in sorted({r["role"] for r in rows})},
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(rows), "output": str(args.output), "counts_by_role": payload["counts_by_role"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
