from scripts.build_catalog import Boundaries, Importer, category
from where2go.config import ROOT
from copy import deepcopy
from scripts.build_catalog import deduplicate


def test_current_boundaries_cover_old_quangnam():
    b=Boundaries(ROOT / "data/vietnam_provinces_wards_geojson.zip")
    assert b.locate(108.3278,15.8794)=="Đà Nẵng"  # Hoi An, former Quang Nam
    assert b.locate(108.2227,16.0612)=="Đà Nẵng"
    assert b.locate(105.8542,21.0285)=="Hà Nội"
    assert b.locate(0,0)==""


def test_osm_id_and_unknown_provenance():
    importer=Importer(Boundaries(ROOT / "data/vietnam_provinces_wards_geojson.zip"),"2026-09-17")
    tags={"tourism":"museum","name":"Bảo tàng kiểm thử"}
    importer.add("node",123,tags,105.8542,21.0285,"osm_point","2026-09-01")
    importer.add("node",123,tags,105.8542,21.0285,"osm_point","2026-09-01")
    assert len(importer.pois)==1
    p=importer.pois["osm:node:123"]
    assert p["hours_status"]=="unknown" and p["review"] is None
    assert p["provenance"]["coordinates"]["verified_at"] is None
    assert category({"tourism":"hotel"})==""


def test_canonical_id_survives_new_source_and_import_order():
    def record(ident):
        return {"poi_id":ident,"source_ids":[ident],"name_normalized":"bao tang", "location":"Hà Nội", "category":"museum",
                "latitude":21.03,"longitude":105.85,"data_status":"usable","review_reason":[]}
    original=record("osm:node:9")
    registry=deduplicate([original],{})
    new=record("osm:node:1")
    rows=[new,deepcopy(original)]
    registry=deduplicate(rows,registry)
    assert registry[new["poi_id"]]==original["poi_id"]
    assert rows[0]["data_status"]=="excluded"
    again=[record("osm:node:9"),record("osm:node:1")]
    assert deduplicate(again,registry.copy())==registry
    orphan=[record("osm:node:1")]
    deduplicate(orphan,registry)
    assert orphan[0]["data_status"]=="needs_review"

