from functools import lru_cache
from pathlib import Path
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from .catalog import load_catalog, coverage, filter_pois
from .config import CATALOG, ROOT
from .models import ItineraryRequest
from .planner import plan_itinerary
from .routing import OSRM, RoutingUnavailable
from .ranking import normalize
from .v2.catalog import CATALOG_V2, load_catalog as load_catalog_v2, coverage as coverage_v2
from .v2.models import ItineraryRequestV2
from .v2.service import ItineraryService
from .v2.dataset import dataset_summary


DATASET_EXPORT_DIR = ROOT / "data/reports/v2/dataset"
BASEMAP_DIR = ROOT / "web/data"
BASEMAP_SLUGS = {"hanoi", "danang"}
DATASET_EXPORT_FILES = {
    "pois.csv", "opening_hours.csv", "ratings.csv", "duration_profiles.csv",
    "access_points.csv", "sources.csv", "summary.json", "audit.json", "README.md",
}
FRONTEND_ASSETS = {
    "app.js": ("app.js", "text/javascript"),
    "styles.css": ("styles.css", "text/css"),
    "vendor/leaflet.js": ("vendor/leaflet.js", "text/javascript"),
    "vendor/leaflet.css": ("vendor/leaflet.css", "text/css"),
    "vendor/images/layers.png": ("vendor/images/layers.png", "image/png"),
    "vendor/images/layers-2x.png": ("vendor/images/layers-2x.png", "image/png"),
    "vendor/images/marker-icon.png": ("vendor/images/marker-icon.png", "image/png"),
    "vendor/images/marker-icon-2x.png": ("vendor/images/marker-icon-2x.png", "image/png"),
    "vendor/images/marker-shadow.png": ("vendor/images/marker-shadow.png", "image/png"),
}


def create_app(catalog_path=CATALOG, router=None, v2_catalog_path=CATALOG_V2, v2_data=None,
               v2_export_dir=DATASET_EXPORT_DIR, basemap_dir=BASEMAP_DIR):
    app = FastAPI(title="Where2Go DSS", version="2.0.0")
    app.state.router = router or OSRM()

    @lru_cache(maxsize=1)
    def catalog():
        try:
            return load_catalog(Path(catalog_path))
        except Exception as error:
            raise HTTPException(503, "Catalog chưa sẵn sàng. Chạy scripts/build_catalog.py") from error

    @lru_cache(maxsize=1)
    def v2_service():
        try:
            rows, meta = v2_data if v2_data is not None else load_catalog_v2(Path(v2_catalog_path))
            return ItineraryService(rows, meta, app.state.router)
        except Exception as error:
            raise HTTPException(503, "Catalog v2 chưa sẵn sàng. Chạy scripts/build_catalog_v2.py") from error

    @lru_cache(maxsize=1)
    def basemap_manifest():
        path = Path(basemap_dir) / "basemap-manifest.json"
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise HTTPException(503, "Basemap local chưa sẵn sàng. Chạy scripts/build_local_basemaps.py") from error
        if not isinstance(manifest.get("outputs"), dict) or not manifest.get("pbf_sha256"):
            raise HTTPException(503, "Manifest basemap local không hợp lệ")
        return manifest

    def basemap_state(service):
        try:
            manifest = basemap_manifest()
        except HTTPException:
            return "unavailable", []
        expected_hash = service.manifest.get("osm", {}).get("sha256")
        routing_hash = getattr(app.state.router, "manifest", {}).get("pbf_sha256")
        if not expected_hash or manifest.get("pbf_sha256") != expected_hash or routing_hash != expected_hash:
            return "version_mismatch", []
        available = [slug for slug in sorted(BASEMAP_SLUGS)
                     if slug in manifest["outputs"] and (Path(basemap_dir) / f"basemap-{slug}.json.gz").is_file()]
        return ("ready" if len(available) == len(BASEMAP_SLUGS) else "unavailable"), available

    @app.get("/api/pois")
    def pois(location: str = "", category: str = "", query: str = "", limit: int = Query(500, ge=1, le=20000)):
        rows, meta = catalog()
        selected = filter_pois(rows, location, [category] if category else [], query)
        return {"pois": selected[:limit], "total": len(selected), "dataset_version": meta["version"],
                "locations": sorted({p["location"] for p in rows if p["location"]}),
                "categories": sorted({p["category"] for p in rows})}

    @app.get("/api/coverage")
    def data_coverage():
        rows, meta = catalog()
        audit_path = ROOT / "data/reports/v1/routing_audit.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
        road = audit.get("summary", []) if audit.get("dataset_version") == meta["version"] else []
        return {"dataset_version": meta["version"], "locations": coverage(rows), "manifest": meta, "road_audit": road}

    @app.get("/api/health")
    def health():
        service = v2_service()
        route = app.state.router
        try:
            route.route([(21.03, 105.85), (21.04, 105.84)], use_cache=False)
            ok = route.manifest.get("pbf_sha256") == service.manifest["osm"]["sha256"]
        except RoutingUnavailable:
            ok = False
        return {
            "catalog": "ready",
            "catalog_api_version": "v2",
            "poi_count": len(service.pois),
            "routing": "ready" if ok else "unavailable",
            "dataset_version": service.manifest["version"],
            "routing_version": route.version,
            "basemap": basemap_state(service)[0],
            "basemap_locations": basemap_state(service)[1],
        }

    @app.post("/api/itineraries")
    def itineraries(request: ItineraryRequest):
        rows, meta = catalog()
        return plan_itinerary(rows, meta, request, app.state.router)

    @app.get("/api/v2/pois")
    def pois_v2(location: str = "", category: str = "", query: str = "",
                include_unserviceable: bool = False,
                limit: int = Query(500, ge=1, le=20000)):
        service = v2_service()
        text = normalize(query)
        visible = [
            poi for poi in service.pois
            if poi["data_status"] == "usable"
            and (include_unserviceable or poi.get("serving_quality", {}).get("eligible", True))
        ]
        selected = [poi for poi in visible
                    if (not location or poi["location"] == location)
                    and (not category or poi["category"] == category)
                    and (not text or text in normalize(poi["name"] + " " + poi.get("description", "")))]
        selected.sort(key=lambda poi: (poi["location"] or "", poi["name"], poi["poi_id"]))
        return {
            "pois": selected[:limit], "total": len(selected),
            "dataset_version": service.manifest["version"],
            "locations": sorted({poi["location"] for poi in visible if poi.get("location")}),
            "categories": sorted({poi["category"] for poi in visible if poi.get("category")}),
        }

    @app.get("/api/v2/pois/{poi_id}")
    def poi_v2(poi_id: str):
        service = v2_service()
        poi = next((item for item in service.pois if item["poi_id"] == poi_id), None)
        if poi is None or poi["data_status"] != "usable" or not poi.get("serving_quality", {}).get("eligible", True):
            raise HTTPException(404, "POI không tồn tại hoặc chưa đủ điều kiện phục vụ")
        return {"poi": poi, "dataset_version": service.manifest["version"]}

    @app.get("/api/v2/coverage")
    def data_coverage_v2():
        service = v2_service()
        summary = dataset_summary(service.pois, service.manifest)
        summary["manifest"] = service.manifest
        return summary

    @app.get("/api/v2/dataset")
    def dataset_v2():
        service = v2_service()
        return dataset_summary(service.pois, service.manifest)

    @app.get("/api/v2/dataset/{filename}")
    def dataset_file_v2(filename: str):
        if filename not in DATASET_EXPORT_FILES:
            raise HTTPException(404, "File dataset không tồn tại")
        path = Path(v2_export_dir) / filename
        if not path.is_file():
            raise HTTPException(404, "Chưa xuất dataset; chạy scripts/export_dataset_v2.py")
        media = "text/csv" if filename.endswith(".csv") else ("application/json" if filename.endswith(".json") else "text/markdown")
        return FileResponse(path, media_type=media, filename=filename)

    @app.get("/api/v2/basemaps/{slug}")
    def basemap_v2(slug: str):
        if slug not in BASEMAP_SLUGS:
            raise HTTPException(404, "Basemap không tồn tại")
        service = v2_service()
        status, available = basemap_state(service)
        if status != "ready" or slug not in available:
            raise HTTPException(503, "Basemap local không khớp phiên bản catalog và OSRM")
        manifest = basemap_manifest()
        info = manifest["outputs"][slug]
        path = Path(basemap_dir) / f"basemap-{slug}.json.gz"
        headers = {
            "Content-Encoding": "gzip",
            "Cache-Control": "public, max-age=3600, must-revalidate",
            "ETag": f'"{info.get("gzip_sha256", manifest["pbf_sha256"])}"',
            "X-Basemap-PBF-SHA256": manifest["pbf_sha256"],
        }
        return FileResponse(path, media_type="application/geo+json", headers=headers)

    @app.post("/api/v2/itineraries")
    def itineraries_v2(request: ItineraryRequestV2):
        return v2_service().plan(request)

    # Mount only frontend assets; legacy scraped web/data is deliberately not public.
    @app.get("/")
    def index():
        return FileResponse(ROOT / "web/index.html")

    def asset_handler(filename, media):
        def asset():
            return FileResponse(ROOT / "web" / filename, media_type=media)
        return asset

    for route, (filename, media) in FRONTEND_ASSETS.items():
        asset = asset_handler(filename, media)
        app.add_api_route("/" + route, asset, methods=["GET"], include_in_schema=False)
    return app


app = create_app()
