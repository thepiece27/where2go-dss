"""Cache geometry for large OSM areas used by identity reconciliation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault("OSMIUM_POOL_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import osmium
from shapely import wkb
from shapely.geometry import mapping
from where2go.config import ROOT
from where2go.v2.catalog import load_catalog


def extract(pbf, output):
    digest = hashlib.file_digest(pbf.open("rb"), "sha256").hexdigest()
    if output.exists() and json.loads(output.read_text(encoding="utf-8")).get("pbf_sha256") == digest:
        return
    wanted = {p["poi_id"] for p in load_catalog()[0] if p["category"] in ("beach", "nature_area", "theme_park", "old_quarter") or p["data_status"] == "needs_review"}
    class Handler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.factory = osmium.geom.WKBFactory()
            self.features = {}
        def area(self, area):
            ident = f"osm:{'way' if area.from_way() else 'relation'}:{area.orig_id()}"
            if ident in wanted:
                try:
                    geom = wkb.loads(self.factory.create_multipolygon(area), hex=True)
                    self.features[ident] = mapping(geom)
                except (RuntimeError, ValueError):
                    pass
    handler = Handler()
    handler.apply_file(str(pbf), locations=True, idx="flex_mem")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"pbf_sha256": digest, "geometries": handler.features}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"geometries": len(handler.features)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, default=ROOT / "data/raw/vietnam-260915.osm.pbf")
    parser.add_argument("--output", type=Path, default=ROOT / "data/cache/poi_geometries_v2.json")
    args = parser.parse_args()
    extract(args.pbf, args.output)
