from functools import lru_cache
from pathlib import Path
import json
from fastapi import FastAPI, HTTPException, Query
from .catalog import load_catalog, coverage, filter_pois
from .config import CATALOG, ROOT
from .models import ItineraryRequest
from .planner import plan_itinerary
from .routing import OSRM, RoutingUnavailable


def create_app(catalog_path=CATALOG, router=None):
    app = FastAPI(title="Where2Go DSS", version="1.0.0")
    app.state.router = router or OSRM()

    @lru_cache(maxsize=1)
    def catalog():
        try:
            return load_catalog(Path(catalog_path))
        except Exception as error:
            raise HTTPException(503, "Catalog chưa sẵn sàng. Chạy scripts/build_catalog.py") from error

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
        audit_path = ROOT / "data/reports/routing_audit.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
        road = audit.get("summary", []) if audit.get("dataset_version") == meta["version"] else []
        return {"dataset_version": meta["version"], "locations": coverage(rows), "manifest": meta, "road_audit": road}

    @app.get("/api/health")
    def health():
        rows, meta = catalog()
        route = app.state.router
        try:
            route.route([(21.03, 105.85), (21.04, 105.84)], use_cache=False)
            ok = route.manifest.get("pbf_sha256") == meta["osm"]["sha256"]
        except RoutingUnavailable:
            ok = False
        return {"catalog": "ready", "poi_count": len(rows), "routing": "ready" if ok else "unavailable",
                "dataset_version": meta["version"], "routing_version": route.version}

    @app.post("/api/itineraries")
    def itineraries(request: ItineraryRequest):
        rows, meta = catalog()
        return plan_itinerary(rows, meta, request, app.state.router)

    # Mount only frontend assets; legacy scraped web/data is deliberately not public.
    @app.get("/")
    def index():
        from fastapi.responses import FileResponse
        return FileResponse(ROOT / "web/index.html")

    def asset_handler(filename, media):
        def asset():
            from fastapi.responses import FileResponse
            return FileResponse(ROOT / "web" / filename, media_type=media)
        return asset

    for filename, media in (("app.js", "text/javascript"), ("styles.css", "text/css")):
        asset = asset_handler(filename, media)
        app.add_api_route("/" + filename, asset, methods=["GET"], include_in_schema=False)
    return app


app = create_app()
