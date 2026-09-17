from fastapi.testclient import TestClient

from where2go.api import create_app


OSM_HASH = "api-test-osm"


class Router:
    version = "api-test-router"
    manifest = {"pbf_sha256": OSM_HASH}

    def table(self, coords):
        size = len(coords)
        return {
            "durations": [[0 if i == j else 300 for j in range(size)] for i in range(size)],
            "distances": [[0 if i == j else 2000 for j in range(size)] for i in range(size)],
            "sources": [{"distance": 0} for _ in coords], "invalid_edges": [],
        }

    def route(self, coords, use_cache=True):
        return {"legs": [{"duration": 300, "distance": 2000} for _ in range(len(coords) - 1)],
                "duration": 300 * (len(coords) - 1), "distance": 2000 * (len(coords) - 1),
                "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in coords]}}


def poi(ident, category):
    return {
        "poi_id": ident, "name": ident, "location": "Hà Nội", "category": category,
        "description": "văn hóa lịch sử", "aliases": [], "tags": ["văn hóa", "lịch sử"],
        "data_status": "usable", "entity_confirmed": True, "business_status": "open",
        "parent_poi_id": None, "is_food": False, "website": "",
        "access_points": [{"access_id": ident + "-a", "latitude": 21.03, "longitude": 105.85,
                           "kind": "entrance", "access_minutes": 0, "verified": True, "method": "test"}],
        "duration_profile": {"short_minutes": 30, "typical_minutes": 60, "long_minutes": 90,
                             "method": "manual_estimate", "verified_at": "2026-09-01"},
        "hours_weekly": [[(480, 1080)]] * 7, "hours_exceptions": {}, "ratings": [],
        "activity_checked_at": "2026-09-01",
    }


def client(v2_export_dir=None):
    rows = [poi("museum-a", "museum"), poi("historic-a", "historic")]
    manifest = {"version": "api-test-v2", "osm": {"sha256": OSM_HASH}}
    kwargs = {"router": Router(), "v2_data": (rows, manifest)}
    if v2_export_dir is not None:
        kwargs["v2_export_dir"] = v2_export_dir
    return TestClient(create_app(**kwargs))


def test_v2_pois_and_coverage_use_v2_catalog():
    with client() as api:
        response = api.get("/api/v2/pois", params={"location": "Hà Nội", "category": "museum"})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        coverage = api.get("/api/v2/coverage").json()
        assert coverage["dataset_version"] == "api-test-v2"
        assert coverage["locations"][0]["attractions"] == 2


def test_v2_pois_hide_unserviceable_rows_by_default():
    rows = [poi("museum-a", "museum")]
    blocked = poi("1-km", "attraction")
    blocked["serving_quality"] = {
        "eligible": False,
        "reasons": ["weak_or_generic_name"],
        "components": {},
    }
    rows.append(blocked)
    manifest = {"version": "api-test-v2", "osm": {"sha256": OSM_HASH}}
    with TestClient(create_app(router=Router(), v2_data=(rows, manifest))) as api:
        assert api.get("/api/v2/pois").json()["total"] == 1
        response = api.get("/api/v2/pois", params={"include_unserviceable": True}).json()
        assert response["total"] == 2


def test_health_reports_the_active_v2_catalog():
    with client() as api:
        health = api.get("/api/health")
        assert health.status_code == 200
        assert health.json() == {
            "catalog": "ready",
            "catalog_api_version": "v2",
            "poi_count": 2,
            "routing": "ready",
            "dataset_version": "api-test-v2",
            "routing_version": "api-test-router",
        }


def test_v2_itinerary_contract_and_v1_endpoint_both_exist():
    with client() as api:
        schema = api.get("/openapi.json").json()["paths"]
        assert "/api/itineraries" in schema and "/api/v2/itineraries" in schema
        response = api.post("/api/v2/itineraries", json={
            "start": {"latitude": 21.03, "longitude": 105.85}, "date": "2026-09-17",
            "location": "Hà Nội", "include_meals": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["dataset_version"] == "api-test-v2"
        assert {block["role"] for block in data["blocks"]} == {"attraction"}


def test_v2_rejects_inconsistent_ahp():
    with client() as api:
        response = api.post("/api/v2/itineraries", json={
            "start": {"latitude": 21.03, "longitude": 105.85}, "date": "2026-09-17",
            "ahp": {"criteria_order": ["preference_match", "place_quality", "drive_time", "data_confidence"],
                    "comparisons": [9, 9, 1 / 9, 9, 1 / 9, 9], "uncertainty": [1.2] * 6},
        })
        assert response.status_code == 422
        assert "CR=" in response.text


def test_v2_dataset_summary_and_download(tmp_path):
    (tmp_path / "pois.csv").write_text("poi_id,name\n1,Test\n", encoding="utf-8")
    with client(tmp_path) as api:
        summary = api.get("/api/v2/dataset")
        assert summary.status_code == 200
        assert summary.json()["poi_count"] == 2
        assert summary.json()["locations"][0]["priority_set"]["selected"] == 2
        download = api.get("/api/v2/dataset/pois.csv")
        assert download.status_code == 200
        assert "poi_id,name" in download.text
        assert api.get("/api/v2/dataset/secret.txt").status_code == 404
