"""Build compact offline Leaflet basemaps for the two focus locations."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OSMIUM_POOL_THREADS", "1")

import osmium
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

from where2go.config import ROOT


FOCUS = {
    "hanoi": {
        "location": "Hà Nội",
        "boundary_member": "geojson/01_ha_noi/01_ha_noi.geojson",
        "center": [21.0285, 105.8542],
    },
    "danang": {
        "location": "Đà Nẵng",
        "boundary_member": "geojson/48_da_nang/48_da_nang.geojson",
        "center": [16.0544, 108.2022],
    },
}

MAJOR_ROADS = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"}
SECONDARY_ROADS = {"secondary", "secondary_link", "tertiary", "tertiary_link"}
LOCAL_ROADS = {"unclassified", "residential", "living_street", "service", "road", "pedestrian"}


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def classify_way(tags):
    highway = tags.get("highway", "")
    name = tags.get("name:vi") or tags.get("name") or ""
    if highway in MAJOR_ROADS:
        return "road", "major", False
    if highway in SECONDARY_ROADS:
        return "road", "secondary", False
    if highway in LOCAL_ROADS and (highway != "service" or name):
        return "road", "local", False
    waterway = tags.get("waterway", "")
    if waterway in {"river", "canal"} or (waterway == "stream" and name):
        return "waterway", waterway, False
    if tags.get("natural") == "coastline":
        return "coastline", "coastline", False
    if tags.get("railway") in {"rail", "light_rail", "subway", "tram"}:
        return "railway", tags.get("railway"), False
    if tags.get("boundary") == "administrative" and tags.get("admin_level") in {"4", "5", "6"}:
        return "admin", tags.get("admin_level"), False
    if tags.get("natural") in {"water", "wetland"} or tags.get("water") or tags.get("landuse") in {"reservoir", "basin"}:
        return "water", "area", True
    if tags.get("leisure") in {"park", "garden", "nature_reserve"} or tags.get("landuse") in {"forest", "grass", "recreation_ground"} or tags.get("natural") == "wood":
        return "green", "area", True
    return None


def read_boundary(archive_path, member):
    with zipfile.ZipFile(archive_path) as archive:
        payload = json.loads(archive.read(member))
    return unary_union([shape(feature["geometry"]) for feature in payload["features"]])


def compatible_parts(geometry, area):
    allowed = (Polygon, MultiPolygon) if area else (LineString, MultiLineString)
    if isinstance(geometry, allowed):
        return geometry
    if isinstance(geometry, GeometryCollection):
        parts = [item for item in geometry.geoms if isinstance(item, allowed)]
        return unary_union(parts) if parts else None
    return None


def rounded_mapping(geometry):
    payload = mapping(geometry)

    def rounded(value):
        if isinstance(value, (list, tuple)):
            return [rounded(item) for item in value]
        return round(float(value), 6)

    payload["coordinates"] = rounded(payload["coordinates"])
    return payload


class BasemapHandler(osmium.SimpleHandler):
    def __init__(self, focuses):
        super().__init__()
        self.focuses = focuses
        self.features = {slug: [] for slug in focuses}
        self.counts = {slug: Counter() for slug in focuses}

    def way(self, way):
        tags = {tag.k: tag.v for tag in way.tags}
        classification = classify_way(tags)
        if classification is None:
            return
        kind, detail, area = classification
        try:
            coordinates = [(node.lon, node.lat) for node in way.nodes if node.location.valid()]
        except osmium.InvalidLocationError:
            return
        if len(coordinates) < (4 if area else 2):
            return
        if area:
            if way.nodes[0].ref != way.nodes[-1].ref:
                return
            geometry = Polygon(coordinates)
            if not geometry.is_valid:
                geometry = geometry.buffer(0)
        else:
            geometry = LineString(coordinates)
        if geometry.is_empty:
            return
        name = tags.get("name:vi") or tags.get("name") or ""
        tolerance = 0.00012 if detail in {"major", "area"} else 0.00008 if detail == "secondary" else 0.00004
        for slug, focus in self.focuses.items():
            min_lon, min_lat, max_lon, max_lat = geometry.bounds
            b_min_lon, b_min_lat, b_max_lon, b_max_lat = focus["bounds"]
            if max_lon < b_min_lon or min_lon > b_max_lon or max_lat < b_min_lat or min_lat > b_max_lat:
                continue
            if not focus["prepared"].intersects(geometry):
                continue
            clipped = compatible_parts(geometry.intersection(focus["boundary"]), area)
            if clipped is None or clipped.is_empty:
                continue
            clipped = clipped.simplify(tolerance, preserve_topology=area)
            if clipped.is_empty or (area and clipped.area < 1e-8) or (not area and clipped.length < 0.0001):
                continue
            self.features[slug].append({
                "type": "Feature",
                "id": f"osm:way:{way.id}",
                "properties": {"kind": kind, "class": detail, "name": name},
                "geometry": rounded_mapping(clipped),
            })
            self.counts[slug][f"{kind}:{detail}"] += 1


def write_gzip_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, compresslevel=9, mtime=0) as zipped:
            zipped.write(raw)
    temp.replace(path)
    return len(raw), path.stat().st_size


def merge_render_features(features):
    """Collapse source ways into one Canvas path per visual class."""
    grouped = {}
    for feature in features:
        properties = feature["properties"]
        key = (properties["kind"], properties["class"])
        geometry = feature["geometry"]
        bucket = grouped.setdefault(key, {"lines": [], "polygons": []})
        if geometry["type"] == "LineString":
            bucket["lines"].append(geometry["coordinates"])
        elif geometry["type"] == "MultiLineString":
            bucket["lines"].extend(geometry["coordinates"])
        elif geometry["type"] == "Polygon":
            bucket["polygons"].append(geometry["coordinates"])
        elif geometry["type"] == "MultiPolygon":
            bucket["polygons"].extend(geometry["coordinates"])

    order = {
        ("green", "area"): 10,
        ("water", "area"): 20,
        ("waterway", "stream"): 30,
        ("waterway", "canal"): 31,
        ("waterway", "river"): 32,
        ("coastline", "coastline"): 33,
        ("admin", "6"): 40,
        ("admin", "5"): 41,
        ("admin", "4"): 42,
        ("road", "local"): 50,
        ("road", "secondary"): 51,
        ("road", "major"): 52,
        ("railway", "tram"): 60,
        ("railway", "subway"): 61,
        ("railway", "light_rail"): 62,
        ("railway", "rail"): 63,
    }
    merged = []
    for key, parts in sorted(grouped.items(), key=lambda item: (order.get(item[0], 999), item[0])):
        kind, detail = key
        if parts["polygons"]:
            merged.append({
                "type": "Feature", "id": f"osm:{kind}:{detail}:areas",
                "properties": {"kind": kind, "class": detail, "name": ""},
                "geometry": {"type": "MultiPolygon", "coordinates": parts["polygons"]},
            })
        if parts["lines"]:
            merged.append({
                "type": "Feature", "id": f"osm:{kind}:{detail}:lines",
                "properties": {"kind": kind, "class": detail, "name": ""},
                "geometry": {"type": "MultiLineString", "coordinates": parts["lines"]},
            })
    return merged


def build(pbf_path, boundaries_path, output_dir):
    focuses = {}
    for slug, config in FOCUS.items():
        boundary = read_boundary(boundaries_path, config["boundary_member"])
        focuses[slug] = {**config, "boundary": boundary, "prepared": prep(boundary), "bounds": boundary.bounds}
    handler = BasemapHandler(focuses)
    handler.apply_file(str(pbf_path), locations=True, idx="flex_mem")
    pbf_sha256 = digest(pbf_path)
    boundary_sha256 = digest(boundaries_path)
    outputs = {}
    for slug, focus in focuses.items():
        boundary = focus["boundary"].simplify(0.0002, preserve_topology=True)
        source_feature_count = len(handler.features[slug]) + 1
        features = [{
            "type": "Feature",
            "id": f"boundary:{slug}",
            "properties": {"kind": "focus_boundary", "class": "boundary", "name": focus["location"]},
            "geometry": rounded_mapping(boundary),
        }, *merge_render_features(handler.features[slug])]
        payload = {
            "type": "FeatureCollection",
            "metadata": {
                "schema_version": "1.0", "location": focus["location"], "center": focus["center"],
                "pbf_sha256": pbf_sha256, "boundary_sha256": boundary_sha256,
                "attribution": "© OpenStreetMap contributors, ODbL 1.0",
            },
            "features": features,
        }
        path = output_dir / f"basemap-{slug}.json.gz"
        raw_bytes, gzip_bytes = write_gzip_json(path, payload)
        outputs[slug] = {
            "file": path.relative_to(ROOT).as_posix(), "location": focus["location"],
            "source_features": source_feature_count, "render_features": len(features),
            "counts": dict(sorted(handler.counts[slug].items())),
            "raw_bytes": raw_bytes, "gzip_bytes": gzip_bytes,
            "gzip_sha256": digest(path),
        }
    manifest = {
        "schema_version": "1.0", "pbf_sha256": pbf_sha256, "boundary_sha256": boundary_sha256,
        "outputs": outputs,
    }
    manifest_path = output_dir / "basemap-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, default=ROOT / "data/raw/vietnam-260915.osm.pbf")
    parser.add_argument("--boundaries", type=Path, default=ROOT / "data/vietnam_provinces_wards_geojson.zip")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "web/data")
    args = parser.parse_args()
    manifest = build(args.pbf, args.boundaries, args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
