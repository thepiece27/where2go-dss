
from where2go.v2.models import ItineraryRequestV2
from where2go.v2.planner import plan_itinerary
from where2go.v2.ranking import RankingContext
from where2go.routing import RoutingUnavailable


OSM_HASH = "test-osm"
MANIFEST = {"version": "test-v2", "osm": {"sha256": OSM_HASH}}


class FakeRouter:
    version = "fake-router"
    manifest = {"pbf_sha256": OSM_HASH}

    def __init__(self, unavailable=False, no_route=None):
        self.unavailable = unavailable
        self.no_route = set(no_route or [])

    def table(self, coords):
        if self.unavailable:
            raise RoutingUnavailable("OSRM stopped")
        size = len(coords)
        durations = [[0 if i == j else 600 for j in range(size)] for i in range(size)]
        distances = [[0 if i == j else 5000 for j in range(size)] for i in range(size)]
        for i, j in self.no_route:
            durations[i][j] = distances[i][j] = None
        return {"durations": durations, "distances": distances,
                "sources": [{"distance": 0} for _ in coords], "invalid_edges": []}

    def route(self, coords, use_cache=True):
        if self.unavailable:
            raise RoutingUnavailable("OSRM stopped")
        return {"legs": [{"duration": 600, "distance": 5000} for _ in range(len(coords) - 1)],
                "duration": 600 * (len(coords) - 1), "distance": 5000 * (len(coords) - 1),
                "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in coords]}}


class SlowerRouteRouter(FakeRouter):
    def route(self, coords, use_cache=True):
        return {"legs": [{"duration": 1200, "distance": 5000} for _ in range(len(coords) - 1)],
                "duration": 1200 * (len(coords) - 1), "distance": 5000 * (len(coords) - 1),
                "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in coords]}}


def make_poi(ident, category, typical=60, latitude=21.03, longitude=105.85, hours=True, food=False):
    return {
        "poi_id": ident, "name": ident, "location": "Hà Nội", "category": category,
        "description": "lịch sử văn hóa", "aliases": [], "tags": ["lịch sử", "văn hóa"],
        "data_status": "usable", "entity_confirmed": True, "business_status": "open",
        "parent_poi_id": None, "is_food": food,
        "access_points": [{"access_id": ident + "-access", "latitude": latitude, "longitude": longitude,
                           "kind": "entrance", "access_minutes": 0, "verified": True, "method": "fixture"}],
        "duration_profile": {"short_minutes": max(15, typical // 2), "typical_minutes": typical,
                             "long_minutes": min(720, typical * 2), "method": "manual_estimate"},
        "hours_weekly": [[(0, 1440)]] * 7 if hours else None, "hours_exceptions": {},
        "ratings": [{"provider": "Google Maps", "rating": 4.5, "review_count": 100,
                     "observed_at": "2026-09-16T00:00:00+00:00", "same_observation": True}],
        "activity_checked_at": "2026-09-01", "website": "https://example.test",
    }


def request(**changes):
    payload = {"start": {"latitude": 21.03, "longitude": 105.85}, "date": "2026-09-17",
               "location": "Hà Nội", "start_time": "08:00", "end_time": "18:00",
               "include_meals": False}
    payload.update(changes)
    return ItineraryRequestV2.model_validate(payload)


def plan(pois, req, router=None):
    return plan_itinerary(pois, MANIFEST, req, router or FakeRouter(), RankingContext(pois))


def test_soft_preference_keeps_diverse_categories():
    pois = [make_poi("museum-a", "museum"), make_poi("historic-a", "historic"), make_poi("park-a", "park")]
    result = plan(pois, request(preferred_categories=["museum"], category_mode="preferred"))
    assert result["status"] == "ready"
    categories = {block["category"] for block in result["blocks"] if block["role"] == "attraction"}
    assert "museum" in categories and len(categories) >= 2


def test_thematic_mode_is_a_hard_filter():
    pois = [make_poi("museum-a", "museum"), make_poi("museum-b", "museum"), make_poi("park-a", "park")]
    result = plan(pois, request(preferred_categories=["museum"], category_mode="only"))
    assert result["status"] == "ready"
    assert {block["category"] for block in result["blocks"] if block["role"] == "attraction"} == {"museum"}


def test_different_poi_duration_profiles_are_preserved():
    pois = [make_poi("museum-short", "museum", 45), make_poi("museum-long", "museum", 120)]
    result = plan(pois, request(category_mode="only", preferred_categories=["museum"]))
    durations = {block["poi_id"]: block["duration_minutes"] for block in result["blocks"] if block["role"] == "attraction"}
    assert durations == {"museum-short": 45, "museum-long": 120}


def test_single_major_attraction_can_fill_the_day():
    pois = [make_poi("major", "theme_park", 300)]
    result = plan(pois, request())
    assert result["status"] == "ready"
    assert [block["poi_id"] for block in result["blocks"]] == ["major"]


def test_meal_fallback_has_no_fake_poi_id_and_consumes_time():
    pois = [make_poi("museum-a", "museum"), make_poi("historic-a", "historic")]
    result = plan(pois, request(include_meals=True))
    meals = [block for block in result["blocks"] if block["role"] == "meal"]
    assert meals and meals[0]["poi_id"] is None and meals[0]["duration_minutes"] == 60
    assert result["status"] == "provisional"


def test_required_unroutable_poi_is_reported():
    pois = [make_poi("required", "museum"), make_poi("other", "historic")]
    result = plan(pois, request(required_poi_ids=["required"]), FakeRouter(no_route={(0, 1)}))
    assert result["status"] == "insufficient_data"
    assert "bắt buộc" in result["reason"]


def test_router_outage_has_distinct_status():
    pois = [make_poi("a", "museum"), make_poi("b", "historic")]
    result = plan(pois, request(), FakeRouter(unavailable=True))
    assert result["status"] == "routing_unavailable"
    assert not result["blocks"]


def test_low_evidence_poi_is_not_served():
    blocked = make_poi("Hard to climb", "viewpoint")
    blocked["serving_quality"] = {"eligible": False, "reasons": ["weak_or_generic_name"]}
    rows = [blocked, make_poi("museum-a", "museum"), make_poi("historic-a", "historic")]
    result = plan(rows, request())
    selected = {block["poi_id"] for block in result["blocks"] if block["role"] == "attraction"}
    assert "Hard to climb" not in selected
    assert {item["reason"] for item in result["excluded_candidates"] if item["poi_id"] == "Hard to climb"} == {"weak_or_generic_name"}


def test_objective_is_recalculated_after_route_leg_recheck():
    pois = [make_poi("museum-a", "museum"), make_poi("historic-a", "historic")]
    result = plan(pois, request(), SlowerRouteRouter())
    attractions = [block for block in result["blocks"] if block["role"] == "attraction"]
    expected = sum(block["score"] for block in attractions) + 0.12 - 0.05 * result["drive_seconds"] / 3600
    assert result["drive_seconds"] == 3600
    assert result["objective"] == expected
