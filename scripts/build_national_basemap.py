"""Produce a small national offline overview from the existing boundary snapshot."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shapely.geometry import mapping
from scripts.build_catalog import Boundaries
from where2go.config import ROOT


def build():
    boundaries = Boundaries(ROOT / "data/vietnam_provinces_wards_geojson.zip")
    features = [{"type": "Feature", "properties": {"name": name, "kind": "province"},
                 "geometry": mapping(geometry.simplify(.005, preserve_topology=True))} for name, geometry in boundaries.items]
    west = min(g.bounds[0] for _, g in boundaries.items)
    south = min(g.bounds[1] for _, g in boundaries.items)
    east = max(g.bounds[2] for _, g in boundaries.items)
    north = max(g.bounds[3] for _, g in boundaries.items)
    path = ROOT / "web/data/vietnam-boundaries.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"type": "FeatureCollection", "bbox": [west, south, east, north],
                               "source": "local_boundary_snapshot", "features": features}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"provinces": len(features), "bytes": path.stat().st_size, "bounds": [west, south, east, north]}))


if __name__ == "__main__":
    build()
