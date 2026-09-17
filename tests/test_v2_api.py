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


def client():
    rows = [poi("museum-a", "museum"), poi("historic-a", "historic")]
    manifest = {"version": "api-test-v2", "osm": {"sha256": OSM_HASH}}
    return TestClient(create_app(router=Router(), v2_data=(rows, manifest)))


def test_v2_pois_and_coverage_use_v2_catalog():
    with client() as api:
        response = api.get("/api/v2/pois", params={"location": "Hà Nội", "category": "museum"})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        coverage = api.get("/api/v2/coverage").json()
        assert coverage["dataset_version"] == "api-test-v2"
        assert coverage["locations"][0]["attractions"] == 2


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

