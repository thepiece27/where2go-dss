import asyncio

from fastapi.testclient import TestClient

from scripts.crawl_danang import TOPICS, Reviewer, discover, saturation, save, read, split_query, cells
from where2go.api import create_app
from where2go.v2.discovery import exclusion_reason, matches_scope, region_for
from where2go.v2.durations import DEFAULT_PROFILES
from where2go.v2.google_collector import google_identity
from where2go.v2.quality import manual_trip_quality
from where2go.v2.taxonomy import CATEGORIES, canonical_category
from tests.test_v2_api import poi, Router, OSM_HASH


def test_scope_covers_beaches_hoi_an_and_islands_but_not_rest_of_quang_nam():
    assert region_for(16.0732782, 108.2468342)  # Beach marker 18 m outside inherited shoreline.
    assert region_for(15.877, 108.329)["region"] == "hoi_an"
    assert region_for(15.956, 108.511)["requires_boat"]
    assert region_for(15.573, 108.474) is None  # Tam Ky.
    assert region_for(15.764, 108.123) is None  # My Son.
    assert region_for(21.0285, 105.8542) is None


def test_worship_filter_does_not_exclude_marble_mountains():
    for name, category in [("Chùa Linh Ứng", "Tourist attraction"), ("Linh Ung", "Buddhist temple"),
                           ("Nhà thờ Hội An", "Historic site"), ("Miếu Bà", "Tourist attraction")]:
        assert exclusion_reason(name, category) == "place_of_worship"
    assert exclusion_reason("Ngũ Hành Sơn", "Scenic spot") is None
    assert exclusion_reason("My Coffee", "Coffee shop")
    assert exclusion_reason("Chợ Hàn", "Market") is None
    assert exclusion_reason("Bãi biển Mỹ Khê parking", "Parking lot")
    assert exclusion_reason("Ban Quản lí các Bãi biển", "Municipal Department of Tourism")
    assert exclusion_reason("Sunrise", "Beach club")


def test_new_categories_are_specific_and_have_duration_defaults():
    for raw, expected in [("Water park", "water_park"), ("Playground", "playground"),
                           ("Pedestrian zone", "walking_street"), ("Bridge", "bridge"),
                           ("Cave", "cave"), ("Waterfall", "waterfall"),
                           ("Campground", "campground"), ("Hiking area", "trailhead")]:
        assert canonical_category(raw) == expected
    assert set(CATEGORIES) == set(DEFAULT_PROFILES)


def test_saturation_requires_all_topics_two_low_growth_rounds_and_no_pending():
    low = {"complete":True, "topics":{t:{"before":1000,"new":1} for t in TOPICS}}
    assert saturation([low] * 4, False)
    assert not saturation([low] * 4, True)
    assert not saturation([low] * 2, False)
    high = {"complete":True,"topics":{t:{"before":1000,"new":20 if t == "coast" else 0} for t in TOPICS}}
    assert not saturation([low, low, high, low], False)


def test_checkpoint_atomic_roundtrip_and_subdivision(tmp_path):
    path = tmp_path / "checkpoint.json"
    save(path, {"status":"blocked","candidates":{"abc":{"name":"Mỹ Khê"}}})
    assert read(path, {})["candidates"]["abc"]["name"] == "Mỹ Khê"
    assert not path.with_suffix(".json.tmp").exists()
    item = {"id":"test", "cell":cells()[0], "status":"limited"}
    children = split_query(item)
    assert children and all(c["cell"]["size_km"] == item["cell"]["size_km"] / 2 for c in children)


def test_campaign_lock_prevents_concurrent_publish_and_collection(tmp_path, monkeypatch):
    from scripts import crawl_danang
    import pytest
    monkeypatch.setattr(crawl_danang, "CAMPAIGN", tmp_path)
    with crawl_danang.CampaignLock():
        with pytest.raises(RuntimeError, match="already running"):
            with crawl_danang.CampaignLock():
                pass
    with crawl_danang.CampaignLock():
        pass


def test_api_refreshes_after_atomic_catalog_replacement(tmp_path, monkeypatch):
    import where2go.api as module
    path = tmp_path / "catalog.sqlite"
    path.write_text("old",encoding="utf-8")
    def load(current):
        return [poi("one","museum")], {"version":Path(current).read_text(encoding="utf-8"),"osm":{"sha256":OSM_HASH}}
    from pathlib import Path
    monkeypatch.setattr(module,"load_catalog_v2",load)
    with TestClient(create_app(router=Router(),v2_catalog_path=path)) as client:
        assert client.get("/api/v2/pois?view=explore").json()["dataset_version"] == "old"
        pending = tmp_path / "new.sqlite"
        pending.write_text("new-version",encoding="utf-8")
        pending.replace(path)
        assert client.get("/api/v2/pois?view=explore").json()["dataset_version"] == "new-version"


class Locator:
    def __init__(self, page, selector):
        self.page, self.selector = page, selector
    async def inner_text(self):
        return self.page.bodies[min(self.page.step, len(self.page.bodies)-1)]
    async def evaluate_all(self, _):
        return self.page.anchors[min(self.page.step, len(self.page.anchors)-1)]
    async def count(self):
        return 1 if self.selector == '[role="feed"]' else 0
    @property
    def first(self):
        return self
    async def evaluate(self, _):
        self.page.step += 1


class Page:
    def __init__(self, bodies, anchors):
        self.bodies, self.anchors, self.step = bodies, anchors, 0
    async def goto(self, url, **kwargs):
        self.url = url
    async def wait_for_timeout(self, _):
        pass
    def locator(self, selector):
        return Locator(self, selector)


def test_discovery_scrolls_deduplicates_and_stops_on_explicit_end():
    a = {"name":"A Beach", "url":"https://www.google.com/maps/place/A/data=!1s0x123:0x456!8m2!3d16.07!4d108.24"}
    b = {"name":"B Beach", "url":a["url"].replace("0x456", "0x789")}
    page = Page(["Results", "You've reached the end of the list."], [[a], [a,b]])
    status, rows = asyncio.run(discover(page, {"query":"beach","cell":{"size_km":2,"latitude":16.07,"longitude":108.24}}))
    assert status == "complete" and len(rows) == 2
    assert google_identity(a["url"] + "?hl=en") == google_identity(a["url"])
    page = Page(["Unusual traffic"], [[]])
    assert asyncio.run(discover(page, {"query":"beach","cell":{"size_km":2,"latitude":16.07,"longitude":108.24}}))[0] == "blocked"


def test_stalled_feed_is_not_successful_exhaustion():
    page = Page(["Results"], [[]])
    status, _ = asyncio.run(discover(page, {"query":"beach","cell":{"size_km":2,"latitude":16.07,"longitude":108.24}}))
    assert status == "limited"


def test_discovery_single_entity_keeps_marker_not_viewport():
    class SingleLocator(Locator):
        async def count(self):
            return int(self.selector == 'h1.DUwDvf')
        async def inner_text(self):
            return "APEC Park"
    class SinglePage(Page):
        def locator(self, selector):
            return SingleLocator(self, selector)
        async def evaluate(self, _):
            return [[["123","456"],"/g/one",None,[160581055,1082232435]]]
    page = SinglePage(["APEC Park"],[[]])
    status, rows = asyncio.run(discover(page,{"query":"park","cell":{"size_km":2,"latitude":16.01,"longitude":108.1}}))
    assert status == "complete" and len(rows) == 1
    assert rows[0]["external_id"] == "0x7b:0x1c8"
    assert "!3d16.0581055!4d108.2232435" in rows[0]["url"]


def test_new_google_entity_can_be_accepted_without_osm_and_rejects_redirect():
    from scripts.merge_sources_v2 import Matcher
    reviewer = Reviewer.__new__(Reviewer)
    reviewer.by_external, reviewer.matcher = {}, Matcher({})
    place = {"name":"New Beach", "category":"Beach", "latitude":16.0732782,"longitude":108.2468342,
             "google_maps_url":"https://www.google.com/maps/place/New/data=!1s0x123:0x456!8m2!3d16.0732782!4d108.2468342"}
    row = {"seed_name":"New Beach","status":"partial","place":place,"expected_place_id":"0x123:0x456"}
    assert reviewer.review(dict(row))["accepted"]
    assert not reviewer.review(dict(row,expected_place_id="0x111:0x222"))["accepted"]
    other = dict(place,google_maps_url=place["google_maps_url"].replace("0x456","0x777"))
    result = reviewer.review(dict(row,place=other,expected_place_id="0x123:0x777"))
    assert result["canonical_poi_id"] == reviewer.by_external["0x123:0x456"]["poi_id"]


def test_list_map_share_tourism_scope_and_islands_need_boat():
    beach, cafe, outside = poi("beach", "beach"), poi("cafe", "cafe"), poi("outside", "museum")
    for p in (beach,cafe):
        p.update(latitude=16.0732782,longitude=108.2468342,location="Đà Nẵng", name="Tourist " + p["poi_id"])
    outside.update(latitude=15.573,longitude=108.474,location="Đà Nẵng")
    assert not matches_scope(outside,"danang_hoian")
    island = dict(beach,latitude=15.956,longitude=108.511)
    assert manual_trip_quality(island)["reasons"] == ["boat_transfer_required"]
    with TestClient(create_app(router=Router(),v2_data=([beach,cafe,outside],{"version":"test","osm":{"sha256":OSM_HASH}}))) as client:
        params = {"scope":"danang_hoian","tourism_only":True,"view":"explore"}
        listing = client.get("/api/v2/pois",params=params).json()
        mapped = client.get("/api/v2/map-pois",params=params).json()
        assert listing["total"] == mapped["total"] == 1
        assert listing["pois"][0]["poi_id"] == mapped["features"][0]["properties"]["poi_id"] == "beach"
        assert client.get("/api/v2/pois?scope=invalid").status_code == 422
