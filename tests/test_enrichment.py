
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, mapping

from where2go.api import create_app
from where2go.v2.google_collector import normalize_place, google_identity, spotlit_entity, image_url_allowed, choose_anchor
from where2go.v2.quality import serving_quality, explorable
from scripts.merge_sources_v2 import Matcher, reconcile_status, legacy_image_identity
from tests.test_v2_api import poi, Router, OSM_HASH


def test_google_coordinates_are_entity_coordinates_not_viewport():
    url = "https://www.google.com/maps/place/X/@10,105,8z/data=!1s0x123:0x456!8m2!3d16.0732782!4d108.2468342"
    place = normalize_place({"latitude": 10, "longitude": 105}, url)
    assert (place["latitude"], place["longitude"]) == (16.0732782, 108.2468342)
    assert place["viewport_coordinate"] == [10, 105]
    assert google_identity(url) == "0x123:0x456"
    assert normalize_place({}, "https://www.google.com/maps/@10,105,8z")["latitude"] is None


def test_only_one_highlighted_entity_can_supply_a_coordinate():
    record = [["123", "456"], "/g/abc", None, [160732782, 1082468342]]
    assert spotlit_entity({"lg": [record]}) == {"place_id": "0x7b:0x1c8", "latitude": 16.0732782, "longitude": 108.2468342}
    other = [["789", "999"], "/g/def", None, [160732782, 1082468342]]
    assert spotlit_entity([record, other]) is None
    assert spotlit_entity([[30668.9, 108.2549, 16.085]]) is None


def test_national_matching_preserves_distinct_beaches_and_parent_areas():
    rows = {
        "dn": {"poi_id": "dn", "name": "Bãi biển Mỹ Khê", "latitude": 16.06, "longitude": 108.24, "category": "beach", "data_status": "usable"},
        "qn": {"poi_id": "qn", "name": "Bãi biển Mỹ Khê", "latitude": 15.19, "longitude": 108.89, "category": "beach", "data_status": "usable"},
    }
    matcher = Matcher(rows)
    assert [p["poi_id"] for p in matcher.match(["Bãi biển Mỹ Khê"], (16.06, 108.24), "beach")[0]] == ["dn"]
    assert not matcher.match(["Bãi biển Mỹ Khê"], (16.06, 108.24), "temple")[0]
    area = mapping(Polygon([(108.23, 16.05), (108.27, 16.05), (108.27, 16.10), (108.23, 16.10)]))
    assert not matcher.match(["Bãi biển Mỹ Khê"], (16.09, 108.25), "beach")[0]
    matcher = Matcher(rows, {"dn": area})
    assert matcher.match(["Bãi biển Mỹ Khê"], (16.09, 108.25), "beach")[0][0]["poi_id"] == "dn"
    assert not matcher.match(["Cổng Mỹ Khê"], (16.09, 108.25), "beach")[0]


def test_profile_images_and_unsafe_urls_are_not_place_photos():
    assert not image_url_allowed("https://lh3.googleusercontent.com/ogw/123=s32")
    assert not image_url_allowed("javascript:alert(1)")
    assert not image_url_allowed("https://user:pass@example.com/photo.jpg")
    assert image_url_allowed("https://lh3.googleusercontent.com/gps-cs-s/photo=w408-h300")
    assert legacy_image_identity("https://tse3.mm.bing.net/photo.jpg", "Museum", "museum") == "needs_review"
    assert legacy_image_identity("https://travel.example/museum.jpg", "Museum", "museum") == "needs_review"
    assert legacy_image_identity("https://lh3.googleusercontent.com/gps-cs-s/photo", "Museum", "museum") == "legacy_entity_link"


def test_chain_branches_require_an_unambiguous_entity_position():
    seed = {"seed_name": "Highlands Coffee", "latitude": 21.03, "longitude": 105.85}
    near = "https://www.google.com/maps/place/X/data=!1s0x1:0x2!8m2!3d21.0301!4d105.8501"
    far = "https://www.google.com/maps/place/X/data=!1s0x3:0x4!8m2!3d21.08!4d105.90"
    anchors = [{"name": "Highlands Coffee", "url": url} for url in (near, far)]
    assert choose_anchor(seed, anchors) == near
    anchors[1]["url"] = far.replace("21.08!4d105.90", "21.0302!4d105.8502")
    assert choose_anchor(seed, anchors) is None


def test_unresolved_identity_cannot_become_serviceable_from_metadata_alone():
    row = poi("missing-identity", "beach")
    row["data_status"] = "needs_review"
    assert not serving_quality(row)["eligible"]
    assert not explorable(row)


def test_explore_alias_pagination_map_and_detail_share_visibility():
    rows = [poi(f"museum-{i}", "museum") for i in range(3)]
    for i, row in enumerate(rows):
        row["latitude"] = 21.03 + .001 * i
        row["longitude"] = 105.85
    rows[0]["name"] = "Bãi biển Mỹ Khê"
    rows[0]["aliases"] = ["My Khe Beach"]
    rows[0]["serving_quality"] = {"eligible": False, "reasons": ["insufficient_service_evidence"]}
    with TestClient(create_app(router=Router(), v2_data=(rows, {"version": "test", "osm": {"sha256": OSM_HASH}}))) as client:
        assert client.get("/api/v2/pois").json()["total"] == 2
        result = client.get("/api/v2/pois", params={"view": "explore", "query": "my khe"}).json()
        assert result["total"] == 1
        assert client.get("/api/v2/pois/museum-0?view=explore").status_code == 200
        assert client.get("/api/v2/pois/museum-0").status_code == 404
        first = client.get("/api/v2/pois?view=explore&limit=1").json()
        second = client.get("/api/v2/pois?view=explore&limit=1&offset=1").json()
        assert first["has_more"] and first["pois"][0]["poi_id"] != second["pois"][0]["poi_id"]
        assert client.get("/api/v2/map-pois?bbox=105,20,106,22").json()["total"] == 3
        assert client.get("/api/v2/map-pois?bbox=nan,20,106,22").status_code == 422
        assert client.get("/api/v2/map-pois?bbox=106,22,105,20").status_code == 422


def test_three_workbooks_are_observations_not_three_places(tmp_path, monkeypatch):
    from openpyxl import Workbook
    from where2go.v2.storage import create_database, connect
    from scripts import build_catalog_v2 as builder, merge_sources_v2 as merge
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(merge, "ROOT", tmp_path)
    class Boundaries:
        items = [("Hà Nội", None)]
        def __init__(self, path):
            pass
        def locate(self, lon, lat):
            return "Hà Nội"
    monkeypatch.setattr(merge, "Boundaries", Boundaries)
    paths = []
    for index in range(3):
        path = tmp_path / f"source-{index}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["STT", "Tên địa điểm", "Vị trí", "maps_result_name", "maps_url", "maps_destination_type", "maps_match_status", "Đánh giá ", "maps_review_count", "Ảnh", "Mô tả"])
        sheet.append([1, "Bảo tàng kiểm thử", "Hà Nội", "Bảo tàng kiểm thử", "https://www.google.com/maps/place/Museum/data=!1s0x123:0x456!8m2!3d21.03!4d105.85", "Museum", "matched", "4.8/5", 1200, "https://lh3.googleusercontent.com/ogw/avatar", "Mô tả từ nguồn cũ"])
        workbook.save(path)
        paths.append(path)
    catalog = tmp_path / "catalog.sqlite"
    create_database(catalog)
    with connect(catalog) as db:
        stats = merge.import_legacy(db, paths, [], "test")
        assert stats["linked_unique_pois"] == 1
        assert db.execute("SELECT count(*) FROM pois").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM source_records").fetchone()[0] == 3
        assert db.execute("SELECT count(*) FROM ratings WHERE same_observation=1").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM source_records WHERE observed_at IS NOT NULL").fetchone()[0] == 0
        assert db.execute("SELECT validation_status FROM poi_images").fetchone()[0] == "rejected_url"
        assert db.execute("SELECT count(*) FROM source_links WHERE status='confirmed'").fetchone()[0] == 3


def test_location_repair_does_not_clear_unrelated_review_reasons(tmp_path):
    from where2go.v2.storage import create_database, connect
    from scripts.build_catalog_v2 import observe, select
    path = tmp_path / "catalog.sqlite"
    create_database(path)
    with connect(path) as db:
        db.execute("INSERT INTO source_files VALUES ('s','source','hash','curation',NULL,NULL,'internal')")
        db.execute("INSERT INTO source_records VALUES ('r','s','key',NULL,'{}')")
        for ident, reasons in (("beach", ["outside_boundary_needs_review"]), ("conflict", ["outside_boundary_needs_review", "identity_conflict"])):
            db.execute("INSERT INTO pois VALUES (?,'needs_review',?,'Đà Nẵng',NULL,'unknown')", (ident, ident))
            select(db, ident, "review_reasons", None, reasons, "test", "test")
            # Each observation belongs to a distinct source record.
            db.execute("INSERT INTO source_records VALUES (?, 's', ?, NULL, '{}')", (ident, ident))
            observe(db, ident, ident, "location", "Đà Nẵng", None, "internal", "curated_spatial_assignment")
        assert reconcile_status(db) == 1
        assert db.execute("SELECT status FROM pois WHERE poi_id='beach'").fetchone()[0] == "usable"
        assert db.execute("SELECT status FROM pois WHERE poi_id='conflict'").fetchone()[0] == "needs_review"
