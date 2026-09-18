"""Build/run the project's dedicated OSRM container; other Docker projects untouched."""
import argparse
import hashlib
import json
import shlex
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "ghcr.io/project-osrm/osrm-backend@sha256:855614a38f464b0558a2ad6eaa7cb8c139f39887da9b38b485ce453c6e6e6124"
VOLUME = "where2go-osrm-data"
CONTAINER = "where2go-osrm"


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--pbf", type=Path, default=ROOT / "data/raw/vietnam-260915.osm.pbf")
    args = parser.parse_args()
    if args.download and not args.pbf.exists():
        args.pbf.parent.mkdir(parents=True, exist_ok=True)
        part = args.pbf.with_suffix(".part")
        urllib.request.urlretrieve("https://download.geofabrik.de/asia/" + args.pbf.name, part)
        part.replace(args.pbf)
    if not args.pbf.exists():
        raise SystemExit("Download the PBF first or pass --download")
    with args.pbf.open("rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    run("docker", "info", "--format", "{{.ServerVersion}}")
    available = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    if available.returncode:
        run("docker", "pull", "ghcr.io/project-osrm/osrm-backend:v5.27.1")
        run("docker", "image", "inspect", IMAGE)
    run("docker", "volume", "create", VOLUME)
    manifest_path = ROOT / "data/routing/manifest.json"
    version = {"pbf_sha256": sha, "image": IMAGE, "profile": "car.lua", "algorithm": "mld"}
    # Successful manifest is written only after preprocessing and a live health check.
    existing = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    running = subprocess.run(["docker", "inspect", "--format", "{{.State.Running}}", CONTAINER], capture_output=True, text=True)
    if existing == version and running.returncode == 0:
        run("docker", "start", CONTAINER)
    else:
        if running.returncode == 0:
            raise SystemExit("Existing where2go-osrm has another/missing manifest. Stop/reconcile this project container before rebuilding.")
        run("docker", "run", "--rm", "--name", "where2go-osrm-build", "--memory", "6g", "--memory-swap", "8g", "--cpus", "2",
            "-v", str(args.pbf.parent.resolve()) + ":/input:ro", "-v", VOLUME + ":/data", IMAGE,
            "sh", "-c", f"cp {shlex.quote('/input/' + args.pbf.name)} /data/vietnam.osm.pbf && osrm-extract -t 2 -p /opt/car.lua /data/vietnam.osm.pbf && osrm-partition -t 2 /data/vietnam.osrm && osrm-customize -t 2 /data/vietnam.osrm")
        run("docker", "run", "-d", "--name", CONTAINER, "--restart", "unless-stopped", "--memory", "5g", "--memory-swap", "7g",
            "-p", "127.0.0.1:5001:5000", "-v", VOLUME + ":/data:ro", IMAGE,
            "osrm-routed", "--algorithm", "mld", "--max-table-size", "100", "/data/vietnam.osrm")
    for _ in range(90):
        try:
            with urllib.request.urlopen("http://127.0.0.1:5001/route/v1/driving/105.85,21.03;105.84,21.04?overview=false", timeout=5) as response:
                payload = json.load(response)
            if payload.get("code") == "Ok":
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text(json.dumps(version, indent=2), encoding="utf-8")
                print("OSRM route PASS; manifest:", manifest_path)
                return
        except (OSError, ValueError):
            pass
        time.sleep(2)
    raise SystemExit("OSRM live health check failed; no success manifest written")


if __name__ == "__main__":
    main()
