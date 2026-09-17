from copy import deepcopy
import httpx
import pytest
from where2go.routing import OSRM, RoutingUnavailable


COORDS = [(21.03, 105.85), (21.04, 105.84)]


def mock_response(payload):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "http://fixture.test"))


def test_cache_isolation_and_negative_edges(monkeypatch):
    payload = {"code": "Ok", "durations": [[0, 1], [2, 0]],
               "distances": [[0, -.3], [3, 0]], "sources": [{"distance": 0}, {"distance": 1}]}
    calls = []
    def fetch(*args, **kwargs):
        calls.append(1)
        return mock_response(payload)
    monkeypatch.setattr(httpx, "get", fetch)
    router = OSRM(manifest={"pbf_sha256": "fixture"})
    first = router.table(COORDS)
    assert first["durations"][0][1] is None
    assert first["invalid_edges"] == [{"from": 0, "to": 1, "reason": "invalid_osrm_value"}]
    first["durations"][1][0] = 999
    assert router.table(COORDS)["durations"][1][0] == 2
    assert len(calls) == 1


def test_live_probe_does_not_hide_offline_and_rejects_bad_geometry(monkeypatch):
    route = {"duration": 1, "distance": 2, "legs": [{"duration": 1, "distance": 2}],
             "geometry": {"type": "LineString", "coordinates": [[105.85, 21.03], [105.84, 21.04]]}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: mock_response({"code": "Ok", "routes": [route]}))
    router = OSRM(manifest={"pbf_sha256": "fixture"})
    assert router.route(COORDS)["duration"] == 1
    def offline(*args, **kwargs):
        raise httpx.ConnectError("fixture offline")
    monkeypatch.setattr(httpx, "get", offline)
    with pytest.raises(RoutingUnavailable):
        router.route(COORDS, use_cache=False)


    bad = deepcopy(route)
    bad["geometry"]["coordinates"] = [[999, 999]]
    monkeypatch.setattr(httpx, "get", lambda *a, **k: mock_response({"code": "Ok", "routes": [bad]}))
    with pytest.raises(RoutingUnavailable):
        router.route(COORDS, use_cache=False)


def test_malformed_osrm_payload_is_service_error(monkeypatch):
    monkeypatch.setattr(httpx,"get",lambda *a,**k:mock_response([]))
    with pytest.raises(RoutingUnavailable):
        OSRM(manifest={"pbf_sha256":"fixture"}).table(COORDS)
