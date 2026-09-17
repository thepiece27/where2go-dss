import itertools
import json
from datetime import date
import numpy as np
import pytest
from fastapi.testclient import TestClient
from where2go.ranking import matrix_weights, topsis, normalize
from where2go.models import ItineraryRequest
from where2go.hours import parse_week, intervals_on
from where2go.planner import plan_itinerary
from where2go.evaluation import metrics, global_time_split
from where2go.routing import RoutingUnavailable


def request(**kwargs):
    base = dict(start={"latitude": 21.03, "longitude": 105.85}, date="2026-09-20")
    base.update(kwargs)
    return ItineraryRequest(**base)


def poi(i=1, **kwargs):
    p = dict(poi_id=f"osm:node:{i}", name=f"Bảo tàng {i}", description="", latitude=21.03+i*.001,
             longitude=105.85, location="Hà Nội", category="museum", data_status="usable",
             data_confidence=.8, hours_raw="Mo-Su 08:00-18:00", visit_duration_minutes=60,
             coordinate_status="osm_point")
    p.update(kwargs)
    return p


class Router:
    version="fixture-only"
    manifest={"pbf_sha256":"fixture"}
    def __init__(self, disconnected=False, fail=False, snap=0):
        self.disconnected, self.fail, self.snap = disconnected, fail, snap
    def table(self, coords):
        if self.fail: raise RoutingUnavailable("offline fixture")
        n=len(coords)
        m=[[0 if i==j else 300 for j in range(n)] for i in range(n)]
        if self.disconnected:
            for i in range(1,n): m[i][0]=None
        return {"durations":m,"distances":[row[:] for row in m],"sources":[{"distance":self.snap} for _ in coords]}
    def route(self, coords, use_cache=True):
        return {"geometry":{"type":"LineString","coordinates":[[lon,lat] for lat,lon in coords]}}


def plan(pois=None, req=None, router=None):
    return plan_itinerary(pois or [poi(1),poi(2)], {"version":"fixture","osm":{"sha256":"fixture"}},req or request(),router or Router())


def test_permutations():
    a=np.array([[1,3,2],[1/3,1,1/2],[1/2,2,1]])
    expected,_=matrix_weights(a)
    for p in itertools.permutations(range(3)):
        actual,_=matrix_weights(a[np.ix_(p,p)])
        assert np.allclose(actual,expected[list(p)])


def test_common_fuzzy_spread_equals_crisp_weights():
    a=np.array([[1,3,2],[1/3,1,1/2],[1/2,2,1]])
    assert np.allclose(matrix_weights(a,1)[0],matrix_weights(a,1.2)[0])


def test_lunch_break_and_directed_return():
    from where2go.planner import simulate
    points={"a":dict(poi(1,hours_raw="Mo-Su 08:00-12:00,13:00-18:00"),matrix_index=1),
            "b":dict(poi(2),matrix_index=2)}
    matrix={"durations":[[0,300,600],[900,0,None],[1200,400,0]],
            "distances":[[0,100,200],[300,0,None],[400,100,0]]}
    r=simulate(["a"],points,matrix,request(start_time="11:30"))
    assert r["stops"][0]["visit_start_time"]=="13:00"
    assert r["return_time"]=="14:15"
    assert simulate(["a","b"],points,matrix,request()) is None
    assert simulate(["b","a"],points,matrix,request()) is not None


@pytest.mark.parametrize("a", [np.zeros((3,3)),np.array([[1,9,1/9],[1/9,1,9],[9,1/9,1]]),np.full((3,3),np.nan),np.ones((2,2))])
def test_invalid_ahp(a):
    with pytest.raises(ValueError): matrix_weights(a)


def test_topsis_cost_and_degenerate():
    scores=topsis([[1,10,1],[1,20,1]],[1,1,1])
    assert scores.tolist()==[1,0]
    assert topsis([[0,0,0],[0,0,0]],[1,1,1]).tolist()==[.5,.5]
    assert topsis([[1,3,1]],[1,1,1]).tolist()==[.5]
    assert normalize("Đà Nẵng") == "da nang"


def test_hours():
    assert parse_week("Mo-Fr 08:00-12:00,13:00-17:00; Sa-Su off")[6]==[]
    assert parse_week("Directions | 8 AM–5 PM") is None
    assert parse_week("Mo-Fr 08:00-25:00") is None
    assert parse_week("Mo--Fr 08:00-17:00") is None
    assert intervals_on("Mo-Su 22:00-02:00", date(2026,9,20))==[(0,120),(1320,1440)]
    assert intervals_on("Mo-Su 08:00-17:00",date(2026,9,2)) is None
    assert intervals_on("24/7",date(2026,9,2))==[(0,1440)]


def test_ready_return_and_provisional():
    r=plan()
    assert r["status"]=="ready" and len(r["stops"])==2
    assert r["legs"][-1]["to"]=="start"
    assert r["return_time"]<="18:00"
    r=plan([poi(1,hours_raw=""),poi(2)])
    assert r["status"]=="provisional" and r["warnings"]


def test_constraints_and_failures():
    assert plan(router=Router(disconnected=True))["status"]=="insufficient_data"
    assert plan(router=Router(fail=True))["status"]=="routing_unavailable"
    assert plan(router=Router(snap=1000))["status"]=="insufficient_data"
    assert plan(req=request(end_time="08:30"))["status"]=="insufficient_data"
    assert plan([poi(1,hours_raw="Su off"),poi(2)])["status"]=="insufficient_data"
    assert plan(req=request(categories=["beach"]))["status"]=="insufficient_data"
    assert plan(req=request(location="Đà Nẵng"))["status"]=="insufficient_data"


def test_wait_and_cap():
    r=plan([poi(i,hours_raw="Mo-Su 09:00-18:00") for i in range(1,9)])
    assert len(r["stops"])==5
    assert r["stops"][0]["visit_start_time"]=="09:00"
    assert r["wait_seconds"]>0
    assert len({p["poi_id"] for p in r["stops"]})==5


def test_reject_request():
    for override in [dict(end_time="07:00"),dict(start={"latitude":float("nan"),"longitude":105}),dict(categories=["bad"])]:
        with pytest.raises(ValueError): request(**override)


def test_invalid_catalog_coordinates_are_excluded():
    from where2go.catalog import candidates
    rows=[poi(1,latitude=float("nan")),poi(2,longitude=200),poi(3,latitude=None),poi(4)]
    pool, counts=candidates(rows,request(),40)
    assert [p["poi_id"] for p in pool]==["osm:node:4"]
    assert counts["invalid_coordinates"]==3


def test_metrics_missing_relevant():
    m=metrics(["a"],{"a":1,"b":1,"c":1},10)
    assert m["ap"]==pytest.approx(1/3) and m["ndcg"]<1
    assert metrics(["a","b","c"],{"a":3,"b":2,"c":1})["ndcg"]==pytest.approx(1)
    assert global_time_split([{"timestamp":1},{"timestamp":3}],3)==([{"timestamp":1}],[{"timestamp":3}])


def test_api_contract(tmp_path):
    import sqlite3
    from where2go.api import create_app
    path=tmp_path/"catalog.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("CREATE TABLE pois(poi_id TEXT,payload TEXT);CREATE TABLE metadata(key TEXT,value TEXT);")
        db.executemany("INSERT INTO pois VALUES (?,?)",[(p["poi_id"],json.dumps(p)) for p in [poi(1),poi(2)]])
        db.execute("INSERT INTO metadata VALUES ('manifest',?)",(json.dumps({"version":"test","osm":{"sha256":"fixture"}}),))
    client=TestClient(create_app(path, Router()))
    assert client.get("/api/pois?location=Đà%20Nẵng").json()["total"]==0
    assert client.post("/api/itineraries",json=request().model_dump(mode="json")).json()["status"]=="ready"
    assert client.post("/api/itineraries",json={}).status_code==422
    assert client.get("/web/data/pois.json").status_code==404
    assert "const" in client.get("/app.js?path=README.md").text
