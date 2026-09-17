import json
import sqlite3
import math
from contextlib import closing
from .config import CATALOG
from .ranking import normalize, preference


def connect(path=CATALOG):
    # A read must never silently create an empty database.
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def load_catalog(path=CATALOG):
    with closing(connect(path)) as db:
        rows = [json.loads(r[0]) for r in db.execute("SELECT payload FROM pois ORDER BY poi_id")]
        manifest = json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
    return rows, manifest


def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    x = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(x)))


def filter_pois(pois, location="", categories=(), query=""):
    q = normalize(query)
    return [p for p in pois if p["data_status"] == "usable"
            and (not location or p["location"] == location)
            and (not categories or p["category"] in categories)
            and (not q or q in normalize(p["name"] + " " + p.get("description", "")))]


def candidates(pois, request, limit):
    filtered = filter_pois(pois, request.location, request.categories, request.query)
    near = []
    invalid_coordinates = 0
    for p in filtered:
        lat, lon = p.get("latitude"), p.get("longitude")
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            invalid_coordinates += 1
            continue
        km = haversine((request.start.latitude, request.start.longitude), (p["latitude"], p["longitude"]))
        if km <= request.radius_km:
            near.append(dict(p, straight_distance_km=km))
    spatial = sorted(near, key=lambda p: (p["straight_distance_km"], p["poi_id"]))
    relevant = sorted(near, key=lambda p: (-preference(p, request.interests), p["straight_distance_km"], p["poi_id"]))
    chosen = {}
    for a, b in zip(relevant, spatial):
        for p in (a, b):
            if len(chosen) < limit:
                chosen.setdefault(p["poi_id"], p)
    return list(chosen.values()), {"catalog": len(pois), "hard_filter": len(filtered),
                                  "invalid_coordinates": invalid_coordinates,
                                  "within_radius": len(near), "shortlist": len(chosen)}


def coverage(pois):
    groups = {}
    for p in pois:
        key = p["location"] or "Chưa xác định"
        row = groups.setdefault(key, {"location": key, "total": 0, "usable": 0, "needs_review": 0,
                                      "excluded": 0, "hours_parsed": 0, "source_checked": 0, "categories": {}})
        row["total"] += 1
        row[p["data_status"]] += 1
        row["hours_parsed"] += bool(p.get("hours_intervals") is not None)
        row["source_checked"] += bool(p.get("review"))
        row["categories"][p["category"]] = row["categories"].get(p["category"], 0) + 1
    return sorted(groups.values(), key=lambda r: (r["location"] not in ("Hà Nội", "Đà Nẵng"), r["location"]))
