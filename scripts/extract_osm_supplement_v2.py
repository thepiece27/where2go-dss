"""Extract food, market and nature POIs missing from the v1 OSM taxonomy."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OSMIUM_POOL_THREADS", "1")
import osmium
from shapely import wkb

from scripts.build_catalog import Boundaries
from where2go.config import ROOT
from where2go.hours import parse_week
from where2go.ranking import normalize


def supplement_category(tags):
    amenity = tags.get("amenity", "")
    if amenity in ("restaurant", "fast_food", "food_court"):
        return "restaurant"
    if amenity == "cafe":
        return "cafe"
    if amenity == "marketplace" or tags.get("shop") == "marketplace":
        return "market"
    if tags.get("leisure") == "nature_reserve" or tags.get("boundary") == "national_park":
        return "nature_area"
    if tags.get("natural") in ("peak", "waterfall"):
        return "nature_area"
    return None


class SupplementHandler(osmium.SimpleHandler):
    def __init__(self, boundaries, observed_at):
        super().__init__()
        self.boundaries = boundaries
        self.observed_at = observed_at
        self.factory = osmium.geom.WKBFactory()
        self.rows = {}
        self.errors = Counter()

    def add(self, kind, ident, tags, lon, lat, geometry_kind, timestamp):
        category = supplement_category(tags)
        name = tags.get("name:vi") or tags.get("name")
        if not category or not name or not math.isfinite(lat + lon):
            return
        location = self.boundaries.locate(lon, lat)
        if location not in ("Hà Nội", "Đà Nẵng"):
            return
        oid = f"osm:{kind}:{ident}"
        hours_raw = tags.get("opening_hours", "")
        self.rows[oid] = {
            "poi_id": oid,
            "name": name,
            "name_normalized": normalize(name),
            "latitude": lat,
            "longitude": lon,
            "location": location,
            "category": category,
            "description": tags.get("description:vi") or tags.get("description", ""),
            "hours_raw": hours_raw,
            "hours_intervals": parse_week(hours_raw),
            "website": tags.get("website") or tags.get("contact:website", ""),
            "source_url": f"https://www.openstreetmap.org/{kind}/{ident}",
            "source_updated_at": timestamp,
            "observed_at": self.observed_at,
            "coordinate_method": geometry_kind,
            "license": "ODbL-1.0",
        }

    def node(self, node):
        tags = dict(node.tags)
        if supplement_category(tags) and node.location.valid():
            self.add("node", node.id, tags, node.location.lon, node.location.lat, "osm_point", str(node.timestamp))

    def area(self, area):
        tags = dict(area.tags)
        if not supplement_category(tags) or not (tags.get("name") or tags.get("name:vi")):
            return
        try:
            geometry = wkb.loads(self.factory.create_multipolygon(area), hex=True)
            point = geometry.representative_point()
            self.add("way" if area.from_way() else "relation", area.orig_id(), tags, point.x, point.y,
                     "osm_area_representative_point_not_entrance", str(area.timestamp))
        except (RuntimeError, ValueError):
            self.errors["invalid_area_geometry"] += 1


def extract(pbf, boundaries):
    observed_at = datetime.now(timezone.utc).isoformat()
    handler = SupplementHandler(Boundaries(boundaries), observed_at)
    handler.apply_file(
        str(pbf), locations=True, idx="flex_mem",
        filters=[osmium.filter.KeyFilter("amenity", "shop", "leisure", "boundary", "natural")],
    )
    return sorted(handler.rows.values(), key=lambda row: row["poi_id"]), dict(handler.errors)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, default=ROOT / "data/raw/vietnam-260915.osm.pbf")
    parser.add_argument("--boundaries", type=Path, default=ROOT / "data/vietnam_provinces_wards_geojson.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "data/cache/osm_supplement_v2.json")
    args = parser.parse_args()
    rows, errors = extract(args.pbf, args.boundaries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"rows": rows, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = Counter((row["location"], row["category"]) for row in rows)
    print(json.dumps({"rows": len(rows), "counts": {"|".join(key): value for key, value in counts.items()}, "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    main()

