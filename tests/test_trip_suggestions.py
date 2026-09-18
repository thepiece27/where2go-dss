from copy import deepcopy
from datetime import date
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from where2go.api import create_app
from where2go.routing import RoutingUnavailable
from where2go.v2.service import ItineraryService
from where2go.v2.trip_models import TripSuggestionRequest, TripContext

MANIFEST = {"version": "trip-test", "osm": {"sha256": "trip-osm"}}


class Router:
    manifest = {"pbf_sha256": "trip-osm"}
    version = "trip-router"

    def __init__(self, route_seconds=300, missing=(), unavailable=False):
        self.route_seconds, self.missing, self.unavailable = route_seconds, set(missing), unavailable
        self.tables, self.routes = 0, []

    def table(self, coords):
        self.tables += 1
        if self.unavailable:
            raise RoutingUnavailable("OSRM unavailable")
        n = len(coords)
        return {"durations": [[None if (i, j) in self.missing else 0 if i == j else 300 for j in range(n)] for i in range(n)],
                "distances": [[None if (i, j) in self.missing else 0 if i == j else 1000 for j in range(n)] for i in range(n)],
                "sources": [{"distance": 0} for _ in coords]}

    def route(self, coords, use_cache=True):
        self.routes.append(coords)
        return {"legs": [{"duration": self.route_seconds, "distance": 1000} for _ in coords[1:]],
                "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in coords]},
                "duration": self.route_seconds * (len(coords) - 1), "distance": 1000 * (len(coords) - 1)}


def poi(i, **changes):
    p = {"poi_id": str(i), "name": f"Bảo tàng văn hóa {i}", "category": "museum", "location": "Đà Nẵng",
         "latitude": 16.05 + i * .005, "longitude": 108.22, "data_status": "usable", "entity_confirmed": True,
         "business_status": "open", "description": "Lịch sử văn hóa", "tags": [], "aliases": [], "ratings": [],
         "hours_weekly": [[(480, 1080)]] * 7, "hours_exceptions": {}, "access_points": [],
         "duration_profile": {"short_minutes": 30, "typical_minutes": 60, "long_minutes": 90, "method": "manual_estimate"}}
    p.update(changes)
    return p


def request(ids, **changes):
    return TripSuggestionRequest.model_validate({"start": {"latitude": 16.05, "longitude": 108.22},
                                                 "date": "2026-09-19", "location": "Đà Nẵng", "include_meals": False,
                                                 "selected_poi_ids": [str(i) for i in ids], **changes})


def plan(rows, req, router=None):
    return ItineraryService(rows, MANIFEST, router or Router()).suggest(req)


def visits(option):
    return [t for t in option["timeline"] if t["role"] == "visit"]


def test_single_unknown_hours_missing_rating_and_no_auto_add():
    rows = [poi(1, hours_weekly=None), poi(2)]
    rows[0]["serving_quality"] = {"eligible": False, "reasons": ["insufficient_service_evidence"]}
    result = plan(rows, request([1], must_visit_poi_ids=["1"]))
    assert result["status"] == "suggestions"
    assert all(o["scheduled_poi_ids"] == ["1"] and o["all_must_visits"] for o in result["options"])
    assert all(visits(o)[0]["hours_status"] == "unknown" and visits(o)[0]["warnings"] for o in result["options"])
    assert result["auto_added_poi_ids"] == []


def test_later_candidates_after_three_closed_places():
    rows = [poi(i, hours_weekly=[[]] * 7) for i in range(1, 4)] + [poi(4)]
    result = plan(rows, request([1, 2, 3, 4]))
    assert result["options"][0]["scheduled_poi_ids"] == ["4"]
    assert {i["poi_id"] for i in result["issues"]} == {"1", "2", "3"}


def test_required_permutation_not_input_order():
    rows = [poi(1, hours_weekly=[[(600, 720)]] * 7), poi(2, hours_weekly=[[(480, 570)]] * 7)]
    result = plan(rows, request([1, 2], must_visit_poi_ids=["1", "2"], end_time="12:30"))
    full = [o for o in result["options"] if o["all_must_visits"] and not o["requires_confirmation"]]
    assert full and all(o["scheduled_poi_ids"] == ["2", "1"] for o in full)


def test_twelve_same_category_and_shared_matrix():
    router = Router()
    result = plan([poi(i) for i in range(12)], request(range(12), end_time="23:00"), router)
    assert max(o["coverage"]["selected"] for o in result["options"]) == 12
    assert router.tables == 1
    assert len({o["option_id"] for o in result["options"]}) == len(result["options"]) <= 3


def test_manual_order_is_preserved_even_when_partial():
    rows = [poi(1, hours_weekly=[[(600, 720)]] * 7), poi(2, hours_weekly=[[(480, 570)]] * 7)]
    result = plan(rows, request([1, 2], manual_order=["1", "2"], must_visit_poi_ids=["1", "2"]))
    for o in result["options"]:
        assert o["scheduled_poi_ids"] != ["2", "1"]
        assert o["missing_must_visit_poi_ids"]
        assert o["requires_confirmation"]


def test_overrides_not_shortened_and_options_deduplicated():
    result = plan([poi(1)], request([1], duration_overrides={"1": 75}))
    assert len(result["options"]) == 1
    assert visits(result["options"][0])[0]["duration_minutes"] == 75
    assert visits(result["options"][0])[0]["duration_source"] == "user_override"


def test_keep_time_partial_and_keep_points_changed_time_both_offered():
    result = plan([poi(1), poi(2)], request([1, 2], end_time="09:30", duration_overrides={"1": 60, "2": 60}, must_visit_poi_ids=["1", "2"]))
    partial = [o for o in result["options"] if o["coverage"]["selected"] == 1 and o["return_seconds"] <= 570 * 60]
    full = [o for o in result["options"] if o["coverage"]["selected"] == 2]
    assert partial and full
    assert partial[0]["requires_confirmation"] and partial[0]["missing_must_visit_poi_ids"]
    assert full[0]["requires_confirmation"] and any(c["code"] == "time_changed" for c in full[0]["changes"])


def test_closed_business_and_closed_date_never_scheduled():
    rows = [poi(1, business_status="permanently_closed"), poi(2, hours_weekly=[[]] * 7)]
    result = plan(rows, request([1, 2]))
    assert result["options"] == [] and result["actions"]
    assert {i["code"] for i in result["issues"]} == {"business_closed", "closed_on_date"}


def test_food_only_and_no_double_meal():
    result = plan([poi(1, category="restaurant")], request([1], start_time="11:30", end_time="14:00", include_meals=True))
    assert result["options"]
    assert all(not any(t["role"] == "meal" for t in o["timeline"]) for o in result["options"])


def test_flexible_meal_is_accounted_and_non_overlapping():
    result = plan([poi(1), poi(2)], request([1, 2], start_time="10:30", end_time="15:00", include_meals=True))
    assert any(any(t["role"] == "meal" for t in o["timeline"]) for o in result["options"])
    for o in result["options"]:
        assert all(a["end_seconds"] <= b["start_seconds"] for a, b in zip(o["timeline"], o["timeline"][1:]))
        assert sum(t["duration_minutes"] for t in o["timeline"]) == pytest.approx(o["total_minutes"])


def test_outage_and_snapshot_have_actions_and_no_fake_route():
    for router in (Router(unavailable=True), Router()):
        if not router.unavailable:
            router.manifest = {"pbf_sha256": "wrong"}
        result = plan([poi(1)], request([1]), router)
        assert result["status"] == "routing_unavailable"
        assert result["options"] == [] and result["actions"] and result["selected_poi_ids"] == ["1"]
        assert "geometry" not in result and "timeline" not in result


def test_one_way_edges_can_use_different_return_stop():
    router = Router(missing={(1, 0), (0, 2)})
    result = plan([poi(1), poi(2)], request([1, 2], must_visit_poi_ids=["1", "2"]), router)
    assert any(o["scheduled_poi_ids"] == ["1", "2"] for o in result["options"])
    assert all(o["scheduled_poi_ids"] == ["1", "2"] for o in result["options"])


def test_disconnected_graph_does_not_emit_routes():
    result = plan([poi(1)], request([1]), Router(missing={(1, 0)}))
    assert result["options"] == [] and result["actions"]


def test_route_timing_revalidated_against_closing_hours():
    rows = [poi(1, hours_weekly=[[(480, 540)]] * 7)]
    result = plan(rows, request([1], duration_overrides={"1": 45}, end_time="10:00"), Router(route_seconds=1800))
    for o in result["options"]:
        for t in visits(o):
            assert t["end_seconds"] <= 540 * 60
        assert o["drive_seconds"] == 3600
        assert sum(leg["duration"] for leg in o["legs"]) == o["drive_seconds"]
        assert o["timeline"][0]["duration_minutes"] == 30
    assert not any(not o["requires_confirmation"] for o in result["options"])


def test_parent_child_without_independent_entrances_explained():
    result = plan([poi(1), poi(2, parent_poi_id="1")], request([1, 2], must_visit_poi_ids=["1", "2"]))
    assert result["options"]
    assert all(len(o["scheduled_poi_ids"]) == 1 and o["requires_confirmation"] for o in result["options"])
    assert all(o["unscheduled"][0]["code"] == "related_access" for o in result["options"])


def test_tight_buffer_is_advisory():
    result = plan([poi(1)], request([1], duration_overrides={"1": 60}, end_time="09:10"))
    original = next(o for o in result["options"] if not o["requires_confirmation"])
    assert original["reserve_minutes"] == 0
    assert any("Lịch khá sát" in w for w in original["warnings"])


@pytest.mark.parametrize("changes", [{"must_visit_poi_ids": ["2"]}, {"manual_order": ["1", "1"]},
                                   {"duration_overrides": {"1": 1}}, {"duration_overrides": {"1": 5.5}},
                                   {"duration_overrides": {"2": 60}}, {"end_time": "08:00"},
                                   {"selected_poi_ids": [str(i) for i in range(13)]}, {"ahp": {}}])
def test_request_invariants(changes):
    with pytest.raises(ValidationError):
        request([1], **changes)


def test_api_contract_and_empty_request():
    with TestClient(create_app(router=Router(), v2_data=([poi(1)], MANIFEST))) as client:
        payload = request([]).model_dump(mode="json")
        response = client.post("/api/v2/trip-suggestions", json=payload)
        assert response.status_code == 200 and response.json()["status"] == "choose_places"
        assert response.json()["actions"]
        payload["selected_poi_ids"] = ["1"]
        assert client.post("/api/v2/trip-suggestions", json=payload).json()["options"]
        assert client.get("/api/v2/pois", params={"view": "explore"}).json()["pois"][0]["manual_trip_quality"]["eligible"]
        payload["must_visit_poi_ids"] = ["missing"]
        assert client.post("/api/v2/trip-suggestions", json=payload).status_code == 422
        context = {key: payload[key] for key in ("start", "date", "location", "selected_poi_ids")}
        assert client.post("/api/v2/trip-recommendations", json=context).status_code == 200


def test_no_catalog_mutation_and_deterministic_ids():
    rows = [poi(1), poi(2)]
    before = deepcopy(rows)
    first, second = plan(rows, request([1, 2])), plan(rows, request([1, 2]))
    assert rows == before
    assert first["options"] == second["options"]


def test_snap_distance_explained_for_start_and_stop():
    class FarRouter(Router):
        def __init__(self, index):
            super().__init__(); self.index = index

        def table(self, coords):
            table = super().table(coords)
            table["sources"][self.index]["distance"] = 1000
            return table
    for index in (0, 1):
        result = plan([poi(1)], request([1]), FarRouter(index))
        assert not result["options"] and result["actions"]
        if index:
            assert result["issues"][0]["code"] == "snap_too_far"


def test_explicit_auto_add_is_visible_and_within_limit():
    rows = [poi(1), poi(2)]
    result = plan(rows, request([1], auto_add=True))
    assert result["auto_added_poi_ids"] == ["2"]
    assert any(o["auto_added"] == [{"poi_id": "2", "name": rows[1]["name"]}] for o in result["options"])


def test_two_profiles_not_duplicated_to_three():
    row = poi(1)
    row["duration_profile"]["long_minutes"] = 60
    result = plan([row], request([1]))
    assert len(result["options"]) == 2


def test_route_exception_does_not_leak_table_geometry_or_times():
    class MissingRoute(Router):
        def route(self, coords, use_cache=True):
            raise RoutingUnavailable("NoRoute")
    result = plan([poi(1)], request([1]), MissingRoute())
    assert result["status"] == "routing_unavailable" and not result["options"] and result["actions"]


def test_recommendations_preserve_editorial_identity_and_outage_labels(monkeypatch):
    monkeypatch.setattr("where2go.v2.trips.curated_focus_ids", lambda: {"Đà Nẵng": ["1"]})
    rows = [poi(1, hours_weekly=None), poi(2), poi(3, business_status="permanently_closed")]
    req = TripContext(start={"latitude": 16.05, "longitude": 108.22}, date=date(2026, 9, 19), location="Đà Nẵng")
    data = ItineraryService(rows, MANIFEST, Router(unavailable=True)).recommend(req)
    assert [p["poi_id"] for p in data["featured"]] == ["1"]
    assert data["featured"][0]["warnings"]
    assert [p["poi_id"] for p in data["contextual"]] == ["2"]
    assert data["routing_status"] == "unavailable" and data["ranking"] is None
    assert "theo vị trí" in data["contextual"][0]["reasons"][0]


def test_same_name_outside_city_not_selected():
    result = plan([poi(1, location="Quảng Ngãi")], request([1], must_visit_poi_ids=["1"]))
    assert not result["options"]
    assert result["issues"][0]["code"] == "wrong_location"


def test_consumer_api_has_separate_information_page():
    with TestClient(create_app(router=Router(), v2_data=([poi(1)], MANIFEST))) as client:
        assert client.get("/dataset.html").status_code == 200
        assert client.get("/dataset.js").status_code == 200
        assert "/api/v2/trip-suggestions" in client.get("/openapi.json").json()["paths"]
