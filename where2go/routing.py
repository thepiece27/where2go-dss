import hashlib
import json
import math
import threading
from copy import deepcopy
from pathlib import Path
import httpx
from .config import OSRM_URL, ROOT


class RoutingUnavailable(RuntimeError):
    pass


class OSRM:
    def __init__(self, url=OSRM_URL, manifest=None):
        self.url = url
        path = ROOT / "data/routing/manifest.json"
        self.manifest = manifest if manifest is not None else (json.loads(path.read_text()) if path.exists() else {})
        self.version = hashlib.sha256(json.dumps(self.manifest, sort_keys=True).encode()).hexdigest()[:16]
        self.cache = {}
        self.lock = threading.Lock()

    def call(self, service, coordinates, params, use_cache=True):
        if not self.manifest.get("pbf_sha256"):
            raise RoutingUnavailable("Chưa có manifest routing đã kiểm chứng. Chạy scripts/setup_osrm.py.")
        coords = ";".join(f"{lon:.7f},{lat:.7f}" for lat, lon in coordinates)
        key = (self.version, self.url, service, coords, tuple(sorted(params.items())))
        with self.lock:
            cached = self.cache.get(key)
        if use_cache and cached is not None:
            return deepcopy(cached)
        try:
            response = httpx.get(f"{self.url}/{service}/v1/driving/{coords}", params=params, timeout=20)
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("OSRM response must be an object")
            if data.get("code") not in ("NoRoute", "NoTable", "NoSegment"):
                response.raise_for_status()
            if data.get("code") not in ("Ok", "NoRoute", "NoTable", "NoSegment"):
                raise ValueError("OSRM error: " + str(data.get("code")))
        except (httpx.HTTPError, ValueError) as error:
            raise RoutingUnavailable("Không lấy được tuyến đường OSRM: " + str(error)) from error
        with self.lock:
            if len(self.cache) > 128:
                self.cache.clear()
            self.cache[key] = data
        return deepcopy(data)

    def table(self, coords):
        data = self.call("table", coords, {"annotations": "duration,distance"})
        if data.get("code") != "Ok":
            return None
        n = len(coords)
        try:
            for key in ("durations", "distances"):
                matrix = data[key]
                if len(matrix) != n or any(len(row) != n for row in matrix):
                    raise ValueError("Invalid OSRM matrix size")
            # Some OSRM builds return a tiny negative distance for coincident snapped
            # points. Do not invent zero/travel time: quarantine that directed edge.
            data["invalid_edges"] = []
            for i in range(n):
                for j in range(n):
                    values = (data["durations"][i][j], data["distances"][i][j])
                    if any(x is None for x in values):
                        data["durations"][i][j] = data["distances"][i][j] = None
                    elif any(not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in values):
                        data["invalid_edges"].append({"from": i, "to": j, "reason": "invalid_osrm_value"})
                        data["durations"][i][j] = data["distances"][i][j] = None
            if len(data["sources"]) != n:
                raise ValueError("Missing snap distances")
            if any(not math.isfinite(s["distance"]) or s["distance"] < 0 for s in data["sources"]):
                raise ValueError("Invalid snap distance")
        except (KeyError, TypeError, ValueError) as error:
            raise RoutingUnavailable(str(error)) from error
        return data

    def route(self, coords, use_cache=True):
        data = self.call("route", coords, {"overview": "full", "geometries": "geojson", "steps": "false", "continue_straight": "false"}, use_cache=use_cache)
        if data.get("code") != "Ok" or not data.get("routes"):
            raise RoutingUnavailable("OSRM không trả hình học tuyến đã chọn")
        route = data["routes"][0]
        try:
            if len(route["legs"]) != len(coords)-1:
                raise ValueError("Invalid Route leg count")
            for item in [route, *route["legs"]]:
                if any(not isinstance(item.get(k), (int, float)) or not math.isfinite(item[k]) or item[k] < 0 for k in ("duration", "distance")):
                    raise ValueError("Invalid Route duration/distance")
            geometry = route["geometry"]
            if geometry["type"] != "LineString" or len(geometry["coordinates"]) < 2:
                raise ValueError("Missing Route geometry")
            for point in geometry["coordinates"]:
                if len(point) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in point) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                    raise ValueError("Invalid Route coordinate")
        except (KeyError, TypeError, ValueError) as error:
            raise RoutingUnavailable(str(error)) from error
        return route
