"""Build and audit a separate dataset, then publish it with a rollback snapshot."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT


def run(*args):
    subprocess.run([sys.executable, "-X", "utf8", *map(str, args)], cwd=ROOT, check=True)


def rebuild(publish=False, compare_report=None):
    work = ROOT / "artifacts/dataset-build"
    dataset = work / "dataset"
    catalog = work / "catalog_v2.sqlite"
    run("scripts/build_catalog_v2.py", "--output", catalog, "--report-dir", work / "catalog")
    run("scripts/export_dataset_v2.py", "--catalog", catalog, "--output-dir", dataset,
        "--private-dir", work / "private")
    run("scripts/audit_dataset_v2.py", "--catalog", catalog, "--dataset-dir", dataset, "--output", dataset / "audit.json")
    audit = json.loads((dataset / "audit.json").read_text(encoding="utf-8"))
    if audit["status"] != "PASS":
        raise RuntimeError("Catalog mới chưa đạt audit; giữ nguyên dataset đang dùng")
    if compare_report:
        run("scripts/report_merge_v2.py", "--catalog", catalog, "--dataset", dataset,
            "--compare", compare_report, "--output", work / "rebuild_verification.json")
    if not publish:
        print(json.dumps({"status": "VALIDATED", "catalog": str(catalog), "dataset": str(dataset)}))
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = ROOT / "artifacts/dataset-backups" / stamp
    backup.mkdir(parents=True)
    active = ROOT / "data/catalog_v2.sqlite"
    active_reports = ROOT / "data/reports/v2"
    if active.exists():
        shutil.copy2(active, backup / active.name)
    for name in ("dataset", "catalog"):
        if (active_reports / name).exists():
            shutil.copytree(active_reports / name, backup / name)
    pending = active.with_suffix(".publish.sqlite")
    shutil.copy2(catalog, pending)
    marker = active_reports / "dataset/.publishing"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()
    try:
        # Each file is replaced atomically; version checks reject a mixed generation.
        for source_folder, target_folder in ((dataset, active_reports / "dataset"), (work / "catalog", active_reports / "catalog"), (work / "private", ROOT / "data/private")):
            target_folder.mkdir(parents=True, exist_ok=True)
            for source in source_folder.iterdir():
                target = target_folder / source.name
                temporary = target.with_suffix(target.suffix + ".publish")
                shutil.copy2(source, temporary)
                temporary.replace(target)
        pending.replace(active)
    except Exception:
        for name in ("dataset", "catalog"):
            if (backup / name).exists():
                shutil.copytree(backup / name, active_reports / name, dirs_exist_ok=True)
        raise
    finally:
        marker.unlink(missing_ok=True)
    print(json.dumps({"status": "PUBLISHED", "backup": str(backup), "dataset_version": audit["dataset_version"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Publish only after the staging audit passes")
    parser.add_argument("--compare-report", type=Path, help="Verify identical semantic tables against a previously validated build before publishing")
    args = parser.parse_args()
    rebuild(args.publish, args.compare_report)
