"""Rebuild public OSM catalog, audit legacy privately, never overwrite source workbooks."""
import argparse
import csv
import hashlib
import inspect
import json
import math
import os
import re
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone
import zipfile
from collections import Counter
from contextlib import closing

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# libosmium's default CPU-sized pool can stall interpreter shutdown on this
# Windows/Python 3.13 host. One worker is sufficient for the bounded import job.
os.environ.setdefault("OSMIUM_POOL_THREADS", "1")
import osmium
import pandas as pd
from shapely.geometry import Point, Polygon, shape
from shapely.strtree import STRtree
from shapely import wkb
from where2go.config import ROOT, DURATIONS
from where2go.ranking import normalize
from where2go.hours import parse_week
from where2go.catalog import coverage, haversine


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


class Boundaries:
    def __init__(self, path):
        self.items = []
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.count("/") != 2 or not name.endswith(".geojson"):
                    continue
                for f in json.loads(archive.read(name))["features"]:
                    self.items.append((f["properties"]["name"], shape(f["geometry"])))
        self.tree = STRtree([g for _, g in self.items])

    def locate(self, lon, lat):
        point = Point(lon, lat)
        for idx in self.tree.query(point):
            name, polygon = self.items[int(idx)]
            if polygon.covers(point):
                return name
        return ""


def category(tags):
    tourism = tags.get("tourism", "")
    if tourism in DURATIONS:
        return tourism
    if tags.get("historic") in ("monument", "memorial", "ruins", "archaeological_site", "fort", "castle", "heritage", "building"):
        return "historic"
    if tags.get("leisure") in ("park", "garden"):
        return "park"
    if tags.get("natural") == "beach":
        return "beach"
    if tags.get("amenity") == "place_of_worship":
        return "temple"
    return ""


class Importer(osmium.SimpleHandler):
    def __init__(self, boundaries, observed_at):
        super().__init__()
        self.boundaries, self.observed_at = boundaries, observed_at
        self.pois = {}
        self.factory = osmium.geom.WKBFactory()
        self.errors = Counter()

    def add(self, typ, ident, tags, lon, lat, geometry_kind, timestamp):
        cat = category(tags)
        name = tags.get("name:vi") or tags.get("name")
        if not cat or not name or not math.isfinite(lon + lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return
        loc = self.boundaries.locate(lon, lat)
        oid = f"osm:{typ}:{ident}"
        url = f"https://www.openstreetmap.org/{typ}/{ident}"
        raw_hours = tags.get("opening_hours", "")
        hours = parse_week(raw_hours)
        provenance = {field: {"source": "OpenStreetMap", "source_url": url,
                              "observed_at": self.observed_at, "verified_at": None,
                              "source_updated_at": timestamp, "license": "ODbL-1.0",
                              "method": "osm_tag" if field != "coordinates" else geometry_kind}
                      for field in ("name", "coordinates", "category", "description", "hours_raw")}
        provenance["location"] = {"source": "local_boundary_snapshot", "method": "point_in_polygon"}
        self.pois[oid] = {
            "poi_id": oid, "source_ids": [oid], "name": name, "name_normalized": normalize(name),
            "latitude": lat, "longitude": lon, "location": loc,
            "location_original": tags.get("addr:province", tags.get("addr:city", "")),
            "category": cat, "description": tags.get("description:vi", tags.get("description", "")),
            "hours_raw": raw_hours, "hours_intervals": hours,
            "hours_status": "known" if hours is not None else "unknown",
            "visit_duration_minutes": DURATIONS[cat], "duration_status": "estimated",
            "data_confidence": .6 + (.2 if hours is not None else 0),
            "data_status": "usable" if loc else "needs_review",
            "review_reason": [] if loc else ["outside_boundary_needs_review"],
            "coordinate_status": geometry_kind, "provenance": provenance,
            "website": tags.get("website", tags.get("contact:website", "")),
            "wikidata": tags.get("wikidata", ""), "wikipedia": tags.get("wikipedia", ""),
            "source_url": url, "license": "ODbL-1.0", "review": None,
        }

    def node(self, n):
        tags = dict(n.tags)
        if category(tags) and n.location.valid():
            self.add("node", n.id, tags, n.location.lon, n.location.lat, "osm_point", str(n.timestamp))

    def area(self, a):
        tags = dict(a.tags)
        if not category(tags) or not (tags.get("name") or tags.get("name:vi")):
            return
        try:
            geom = wkb.loads(self.factory.create_multipolygon(a), hex=True)
            point = geom.representative_point()
            self.add("way" if a.from_way() else "relation", a.orig_id(), tags, point.x, point.y,
                     "osm_area_representative_point_not_entrance", str(a.timestamp))
        except (RuntimeError, ValueError):
            self.errors["invalid_area_geometry"] += 1


def legacy_audit(path, output):
    df = pd.read_excel(path).fillna("")
    if df["STT"].duplicated().any() or (df["STT"] == "").any():
        raise ValueError("Legacy STT must be unique/nonempty")
    coords = Counter((str(r["maps_latitude"]), str(r["maps_longitude"])) for _, r in df.iterrows())
    rows = []
    for _, r in df.iterrows():
        reasons = ["legacy_field_source_and_license_unverified"]
        if coords[str(r["maps_latitude"]), str(r["maps_longitude"])] > 5:
            reasons.append("coordinate_cluster")
        url = str(r.get("maps_url", ""))
        if "@" in url and "!3d" not in url:
            reasons.append("viewport_only_url")
        if str(r.get("maps_result_name", "")).lower() == "results":
            reasons.append("search_results_not_entity")
        if not r.get("maps_destination_type"):
            reasons.append("missing_category")
        rows.append({"poi_id": f"legacy:{r['STT']}", "name": r["Tên địa điểm"],
                     "location_original": r["Vị trí"], "status": "needs_review", "reasons": "|".join(reasons)})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(reason for r in rows for reason in r["reasons"].split("|"))
    return {"rows": len(rows), "issues": dict(counts), "sha256": digest(path), "source": str(path.name),
            "suspicious_coordinate_clusters": [{"latitude": lat, "longitude": lon, "count": n}
                                               for (lat, lon), n in coords.most_common() if n > 5]}


def deduplicate(pois, registry):
    """Keep already-issued canonical IDs even if a new lower source ID appears."""
    buckets, by_id = {}, {p["poi_id"]: p for p in pois}
    ordered = sorted(pois, key=lambda p: (registry.get(p["poi_id"]) != p["poi_id"], p["poi_id"]))
    for p in ordered:
        ident = p["poi_id"]
        previous = registry.get(ident)
        if previous and previous != ident:
            same = by_id.get(previous)
            if same is None or same["name_normalized"] != p["name_normalized"] or same["location"] != p["location"] or same["category"] != p["category"] or haversine((p["latitude"], p["longitude"]), (same["latitude"], same["longitude"])) >= .15:
                p["data_status"] = "needs_review"
                p["review_reason"].append("canonical_link_needs_review:" + previous)
                continue
        else:
            key = (p["name_normalized"], p["location"], p["category"])
            peers = buckets.setdefault(key, [])
            # Two issued canonical entities are not silently merged later.
            same = None if previous == ident else next((q for q in peers if haversine((p["latitude"], p["longitude"]), (q["latitude"], q["longitude"])) < .15), None)
            if same is None:
                peers.append(p)
        if same is not None:
            p["data_status"] = "excluded"
            p["review_reason"].append("duplicate_of:" + same["poi_id"])
            if ident not in same["source_ids"]:
                same["source_ids"].append(ident)
            registry[ident] = same["poi_id"]
        else:
            registry[ident] = ident
    return registry


def build(args):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    reports = ROOT / "data/reports"
    legacy = legacy_audit(args.legacy, ROOT / "data/private/legacy_review.csv")
    boundary_hash = digest(args.boundaries)
    pbf_hash = digest(args.pbf)
    reader = osmium.io.Reader(str(args.pbf), osmium.osm.NOTHING)
    timestamp = reader.header().get("osmosis_replication_timestamp")
    reader.close()
    importer_hash = hashlib.sha256((inspect.getsource(Importer) + inspect.getsource(Boundaries) + inspect.getsource(category)
                                   + inspect.getsource(parse_week) + digest(ROOT / "where2go/config.py")).encode()).hexdigest()[:12]
    cache = ROOT / "data/cache" / (pbf_hash[:16] + boundary_hash[:16] + "-" + importer_hash + ".json")
    if cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        pois, import_errors = cached["pois"], cached["errors"]
    else:
        handler = Importer(Boundaries(args.boundaries), now)
        print("Importing OSM nodes/areas...", flush=True)
        handler.apply_file(str(args.pbf), locations=True, idx="flex_mem",
                           filters=[osmium.filter.KeyFilter("tourism", "historic", "leisure", "natural", "amenity")])
        pois = sorted(handler.pois.values(), key=lambda p: p["poi_id"])
        import_errors = dict(handler.errors)
        write_json(cache, {"pois": pois, "errors": import_errors})
    # Conservative duplicate suppression; retain all objects and source aliases.
    registry_path = ROOT / "data/curation/id_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
    if not registry and args.output.exists():
        from where2go.catalog import load_catalog
        previous, _ = load_catalog(args.output)
        for p in previous:
            for source_id in p["source_ids"]:
                if len(p["source_ids"]) > 1 or not any(r.startswith("duplicate_of:") for r in p["review_reason"]):
                    registry[source_id] = p["poi_id"]
    for p in pois:
        if p["location"] == "Đà Nẵng" and p["category"] == "historic" and re.fullmatch(r"(?:Group )?[A-K][0-9]*", p["name"]):
            p["data_status"] = "excluded"
            p["review_reason"].append("internal_site_component_not_separate_trip_stop")
        if p["poi_id"] == "osm:way:178995269":
            p["data_status"] = "needs_review"
            p["review_reason"].append("island_monument_no_verified_car_access")
        if p["category"] == "park" and any(t in p["name_normalized"] for t in ("bai dau xe", "vong xoay", "pool spa")):
            p["data_status"] = "needs_review"
            p["review_reason"].append("category_name_conflict")
        p["provenance"]["location"].update(source_url="https://github.com/thanglequoc/vietnamese-provinces-database", snapshot_sha256=boundary_hash,
                                            observed_at="2026-09-17", verified_at=None, license="see_boundary_source")
        p["provenance"]["visit_duration_minutes"] = {"source": "where2go/config.py:DURATIONS", "method": "category_default_estimate",
                                                        "observed_at": "2026-09-17", "verified_at": None, "license": "project_configuration"}
    registry = deduplicate(pois, registry)
    write_json(registry_path, registry)
    review_path = ROOT / "data/curation/reviews.json"
    reviews = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else []
    by_id = {p["poi_id"]: p for p in pois}
    for review in reviews:
        if review["poi_id"] not in by_id:
            raise ValueError("Review points to missing POI: " + review["poi_id"])
        if not review.get("evidence_urls") or not review.get("reviewed_at") or not review.get("reviewer"):
            raise ValueError("Review lacks evidence")
        p = by_id[review["poi_id"]]
        p["review"] = review
        for field, value in review.get("overrides", {}).items():
            if field != "hours_raw":
                raise ValueError("Unsupported override field")
            p["hours_original"] = p["hours_raw"]
            p[field] = value
            p["hours_intervals"] = parse_week(value)
            p["hours_status"] = "known" if p["hours_intervals"] is not None else "unknown"
            p["provenance"][field] = {"source": "venue_or_tourism_portal", "source_url": review["evidence_urls"][-1],
                                      "observed_at": review["reviewed_at"], "verified_at": review["reviewed_at"],
                                      "method": "assisted_digital_source_crosscheck", "license": "factual_hours_with_source"}
            p["data_confidence"] = .6 + (.2 if p["hours_intervals"] is not None else 0)
        p["data_confidence"] = min(1, p["data_confidence"] + .2)
    pipeline_hash = hashlib.sha256("".join(digest(p) for p in [Path(__file__), ROOT / "where2go/config.py", ROOT / "where2go/hours.py", ROOT / "where2go/ranking.py", registry_path]).encode()).hexdigest()
    manifest = {"version": "osm-" + pbf_hash[:12] + "-" + boundary_hash[:8] + "-" + (digest(review_path)[:8] if review_path.exists() else "unreviewed") + "-" + pipeline_hash[:8],
                "pipeline_sha256": pipeline_hash, "id_registry_sha256": digest(registry_path),
                "created_at": now, "pipeline_version": "1.0", "osm": {"sha256": pbf_hash,
                "filename": args.pbf.name, "url": "https://download.geofabrik.de/asia/" + args.pbf.name,
                "source_timestamp": timestamp, "license": "ODbL-1.0"},
                "boundaries": {"sha256": boundary_hash, "source": "https://github.com/thanglequoc/vietnamese-provinces-database", "method": "covers; no nearest fallback"},
                "legacy_audit": legacy, "import_errors": import_errors, "poi_count": len(pois),
                "review_count": len(reviews), "attribution": "© OpenStreetMap contributors; ODbL 1.0"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(args.output) + ".tmp")
    with closing(sqlite3.connect(temp)) as db:
        db.executescript("DROP TABLE IF EXISTS pois; DROP TABLE IF EXISTS metadata; CREATE TABLE pois(poi_id TEXT PRIMARY KEY,payload TEXT NOT NULL); CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);")
        db.executemany("INSERT INTO pois VALUES (?,?)", [(p["poi_id"], json.dumps(p, ensure_ascii=False, allow_nan=False)) for p in pois])
        db.execute("INSERT INTO metadata VALUES ('manifest',?)", (json.dumps(manifest, ensure_ascii=False),))
        db.commit()
    os.replace(temp, args.output)
    write_json(reports / "manifest.json", manifest)
    write_json(reports / "coverage.json", coverage(pois))
    write_json(reports / "review_queue.json", [{"poi_id": p["poi_id"], "reasons": p["review_reason"]} for p in pois if p["data_status"] != "usable"])
    with (reports / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["poi_id", "name", "location", "category", "latitude", "longitude", "hours_raw", "hours_status", "data_status", "source_url"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(pois)
    print(json.dumps({"pois": len(pois), "coverage": coverage(pois)[:2], "legacy": legacy}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, default=ROOT / "data/raw/vietnam-260915.osm.pbf")
    parser.add_argument("--boundaries", type=Path, default=ROOT / "data/vietnam_provinces_wards_geojson.zip")
    parser.add_argument("--legacy", type=Path, default=ROOT / "data/vietnam_destinations_google_maps_browser_hotosm.xlsx")
    parser.add_argument("--output", type=Path, default=ROOT / "data/catalog.sqlite")
    build(parser.parse_args())
