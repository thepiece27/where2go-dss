from datetime import date, datetime, time
import sqlite3
from openpyxl import Workbook, load_workbook

from scripts.create_manual_template_v2 import create, PLACES, OPENING, DURATION, VERIFICATION
from scripts import build_catalog_v2, inventory_sources_v2
from scripts.validate_manual_data_v2 import validate
from where2go.config import CATALOG
from where2go.v2.durations import choose_duration, fallback_profile
from where2go.v2.hours import intervals_on_date
from where2go.v2.google_hours import parse_google_week
from where2go.v2.storage import connect, create_database
from where2go.v2.taxonomy import canonical_category, refine_category
from where2go.v2.quality import serving_quality


def test_taxonomy_specific_rules_precede_broad_park():
    assert canonical_category("National park") == "nature_area"
    assert canonical_category("Coffee shop") == "cafe"
    assert canonical_category("Results") is None
    assert refine_category("attraction", "Phố cổ Hội An") == "old_quarter"
    assert refine_category("attraction", "Làng gốm Thanh Hà") == "craft_village"
    assert refine_category("attraction", "Nhà hát múa rối") == "performance_venue"


def test_source_inventory_excludes_its_own_manifest(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    report_dir = data_dir / "reports" / "v2"
    report_dir.mkdir(parents=True)
    source = data_dir / "source.txt"
    source.write_text("source", encoding="utf-8")
    output = report_dir / "source_manifest.json"
    output.write_text("old manifest", encoding="utf-8")
    monkeypatch.setattr(inventory_sources_v2, "ROOT", tmp_path)

    rows = inventory_sources_v2.inventory(data_dir, exclude=(output,))

    assert [row["logical_path"] for row in rows] == ["data/source.txt"]


def test_duration_profile_and_override_are_explicit():
    profile = fallback_profile("museum")
    assert choose_duration(profile, "quick") == (30, "category_default")
    assert choose_duration(profile, "relaxed") == (120, "category_default")
    assert choose_duration(profile, "balanced", 75) == (75, "user_override")


def test_hours_unknown_closed_and_overnight_are_distinct():
    weekly = [None, [], [(1320, 1560)], [], [], [], []]
    assert intervals_on_date(weekly, {}, date(2026, 9, 14), True) is None  # Monday unknown
    assert intervals_on_date(weekly, {}, date(2026, 9, 15), True) == []   # Tuesday closed
    assert intervals_on_date(weekly, {}, date(2026, 9, 17), True) == [(0, 120)]
    exceptions = {"2026-09-17": {"status": "closed"}}
    assert intervals_on_date(weekly, exceptions, date(2026, 9, 17), True) == []


def test_google_hours_keep_missing_unknown_and_parse_24_hours():
    weekly = parse_google_week([
        "MondayClosed\ue14d", "TuesdayOpen 24 hours\ue14d",
        "Wednesday9:30\u202fAM–12\u202fPM, 1–5\u202fPM\ue14d",
    ])
    assert weekly[0] == []
    assert weekly[1] == [(0, 1440)]
    assert weekly[2] == [(570, 720), (780, 1020)]
    assert weekly[3] is None
    assert parse_google_week(None) is None


def test_storage_schema_enforces_foreign_keys(tmp_path):
    path = tmp_path / "v2.sqlite"
    create_database(path)
    with connect(path) as db:
        assert db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "2.0"
        try:
            db.execute("INSERT INTO source_records VALUES ('r','missing','1',NULL,'{}')")
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Foreign key was not enforced")


def test_manual_template_is_valid_before_human_enrichment(tmp_path):
    path = tmp_path / "manual.xlsx"
    count = create(path, CATALOG, per_city=2)
    errors, warnings, stats = validate(path)
    assert count == 4
    assert not errors
    assert not warnings
    assert stats["places"] == 4
    workbook = load_workbook(path, read_only=True)
    assert {"places", "opening_hours", "visit_duration", "verification"} <= set(workbook.sheetnames)


def test_serving_quality_blocks_generic_and_evidence_free_pois():
    base = {"name": "Hard to climb", "ratings": [], "hours_weekly": None,
            "website": "", "description": "", "duration_profile": {"method": "category_default"},
            "access_points": [{"verified": False}]}
    quality = serving_quality(base)
    assert not quality["eligible"]
    assert set(quality["reasons"]) == {"weak_or_generic_name", "insufficient_service_evidence"}
    numeric_distance = dict(base, name="1.5 km", hours_weekly=[[(0, 1440)]] * 7)
    assert "weak_or_generic_name" in serving_quality(numeric_distance)["reasons"]
    improved = dict(base, name="Bảo tàng kiểm thử", website="https://example.test")
    assert serving_quality(improved)["eligible"]
    improved["hours_weekly"] = [[(480, 1020)]] * 7
    assert serving_quality(improved)["eligible"]


def test_quality_detects_name_category_conflict_and_repeated_description():
    row = {"name": "Trại gà Đông Tảo", "category": "historic", "ratings": [], "hours_weekly": None,
           "website": "2lualamgiau.com", "description": "Trại gà Đông Tảo",
           "duration_profile": {"method": "category_default"}, "access_points": [{"verified": False}]}
    quality = serving_quality(row)
    assert not quality["eligible"]
    assert "category_name_conflict" in quality["reasons"]
    assert not quality["components"]["description"]


def test_cultural_sports_facility_misclassified_as_park_is_not_serviceable():
    row = {
        "name": "Trung tâm Văn hóa - Thể thao quận Thanh Khê",
        "category": "park",
        "ratings": [],
        "hours_weekly": [[(420, 1320)]] * 7,
        "website": "",
        "description": "",
        "duration_profile": {"method": "category_default"},
        "access_points": [{"verified": False}],
    }
    quality = serving_quality(row)
    assert not quality["eligible"]
    assert "category_name_conflict" in quality["reasons"]


def test_priority_duration_target_requires_verified_profiles():
    from where2go.v2.dataset import priority_coverage

    rows = []
    for index in range(50):
        rows.append({
            "poi_id": f"attraction-{index}",
            "name": f"Điểm tham quan {index}",
            "location": "Hà Nội",
            "category": "museum",
            "is_food": False,
            "data_status": "usable",
            "hours_weekly": [[(480, 1020)]] * 7,
            "ratings": [],
            "access_points": [],
            "duration_profile": {
                "method": "curated_planning_estimate",
                "verified_at": None,
            },
            "serving_quality": {"eligible": True, "reasons": [], "components": {}},
        })
    for index in range(20):
        rows.append({
            "poi_id": f"food-{index}",
            "name": f"Nhà hàng {index}",
            "location": "Hà Nội",
            "category": "restaurant",
            "is_food": True,
            "data_status": "usable",
            "hours_weekly": [[(480, 1320)]] * 7,
            "ratings": [],
            "access_points": [],
            "duration_profile": None,
            "serving_quality": {"eligible": True, "reasons": [], "components": {}},
        })

    coverage = priority_coverage(rows, "Hà Nội")
    assert coverage["specific_duration_percent"] == 100.0
    assert coverage["verified_duration_percent"] == 0.0
    assert not coverage["target_status"]["verified_duration"]
    assert not coverage["target_status"]["specific_duration"]


def test_confirmed_manual_rows_import_hours_duration_rating_and_access(tmp_path, monkeypatch):
    workbook = Workbook()
    places = workbook.active
    places.title = "places"
    places.append(PLACES)
    place = {key: "" for key in PLACES}
    place.update({
        "record_id": "manual-1", "canonical_poi_id": "poi-1", "seed_name": "Bảo tàng A",
        "maps_name": "Bảo tàng A", "maps_url": "https://maps.google.com/example",
        "location_expected": "Hà Nội", "rating_raw": "4,6", "review_count_raw": "1.234",
        "latitude": 21.03, "longitude": 105.85, "coordinate_method": "manual_verified_entrance",
        "website": "https://example.test", "observed_at": datetime(2026, 9, 18, 8, 0),
        "reviewer": "tester",
    })
    places.append([place[key] for key in PLACES])
    hours = workbook.create_sheet("opening_hours")
    hours.append(OPENING)
    opening = {key: "" for key in OPENING}
    opening.update({
        "record_id": "manual-1", "day_of_week": "Mo", "status": "open",
        "open_time": time(0, 0), "close_time": time(0, 0), "closes_next_day": True,
        "source_url": "https://example.test/hours", "observed_at": datetime(2026, 9, 18, 8, 0),
    })
    hours.append([opening[key] for key in OPENING])
    durations = workbook.create_sheet("visit_duration")
    durations.append(DURATION)
    duration = {key: "" for key in DURATION}
    duration.update({
        "record_id": "manual-1", "short_minutes": 45, "typical_minutes": 90,
        "long_minutes": 150, "duration_method": "manual_estimate",
        "source_url": "https://example.test/visit", "observed_at": datetime(2026, 9, 18, 8, 0),
        "reviewer": "tester",
    })
    durations.append([duration[key] for key in DURATION])
    verification = workbook.create_sheet("verification")
    verification.append(VERIFICATION)
    decision = {key: "" for key in VERIFICATION}
    decision.update({
        "record_id": "manual-1", "reviewer": "tester", "reviewed_at": datetime(2026, 9, 18, 9, 0),
        "fields_checked": "identity,hours,duration,access,rating", "identity_status": "confirmed",
        "evidence_url": "https://example.test", "include_in_demo": True,
    })
    verification.append([decision[key] for key in VERIFICATION])
    path = tmp_path / "manual.xlsx"
    workbook.save(path)

    monkeypatch.setattr(build_catalog_v2, "ROOT", tmp_path)
    database = tmp_path / "catalog.sqlite"
    create_database(database)
    with connect(database) as db:
        db.execute("INSERT INTO pois VALUES (?,?,?,?,?,?)", ("poi-1", "usable", "Bảo tàng A", "Hà Nội", None, "unknown"))
        db.execute(
            "INSERT INTO opening_intervals VALUES (?,?,?,?,?,?,?,?,?)",
            ("old-hours", "poi-1", None, 1, None, "open", 600, 660, 0),
        )
        stats = build_catalog_v2.import_manual(db, path, [], "test-build")
        assert stats["confirmed"] == 1
        assert db.execute("SELECT status FROM source_links").fetchone()[0] == "confirmed"
        assert tuple(db.execute("SELECT status,open_minute,close_minute,closes_next_day FROM opening_intervals").fetchone()) == ("open", 0, 0, 1)
        assert db.execute("SELECT count(*) FROM opening_intervals").fetchone()[0] == 1
        assert stats["hours_sources_replaced"] == 1
        assert tuple(db.execute("SELECT short_minutes,typical_minutes,long_minutes,method FROM duration_profiles").fetchone()) == (45, 90, 150, "manual_estimate")
        assert tuple(db.execute("SELECT rating,review_count,same_observation FROM ratings").fetchone()) == (4.6, 1234, 1)
        assert db.execute("SELECT verified FROM access_points").fetchone()[0] == 1


def test_duration_curation_is_explicit_unverified_planning_estimate(tmp_path, monkeypatch):
    path = tmp_path / "durations.csv"
    path.write_text(
        "poi_id,short_minutes,typical_minutes,long_minutes,method,source_url,notes\n"
        "poi-1,30,90,180,curated_planning_estimate,,test estimate\n",
        encoding="utf-8",
    )
    database = tmp_path / "catalog.sqlite"
    create_database(database)
    monkeypatch.setattr(build_catalog_v2, "ROOT", tmp_path)
    with connect(database) as db:
        db.execute("INSERT INTO pois VALUES (?,?,?,?,?,?)", ("poi-1", "usable", "Điểm A", "Hà Nội", None, "unknown"))
        stats = build_catalog_v2.import_duration_curation(db, path, "test-build")
        assert stats["imported"] == 1
        row = db.execute(
            "SELECT short_minutes,typical_minutes,long_minutes,method,verified_at FROM duration_profiles"
        ).fetchone()
        assert tuple(row) == (30, 90, 180, "curated_planning_estimate", None)


def test_google_rating_with_impossible_precision_is_not_rankable(tmp_path, monkeypatch):
    workbook = Workbook()
    places = workbook.active
    places.title = "places"
    places.append(PLACES)
    row = {key: "" for key in PLACES}
    row.update({
        "record_id": "google-1", "canonical_poi_id": "poi-1", "seed_name": "Điểm A",
        "maps_name": "Điểm A", "maps_url": "https://www.google.com/maps/place/example",
        "place_id": "place-1", "location_expected": "Hà Nội", "category_raw": "Museum",
        "rating_raw": "4.97", "review_count_raw": "24", "observed_at": datetime(2026, 9, 18),
    })
    places.append([row[key] for key in PLACES])
    for title, headers in (("opening_hours", OPENING), ("visit_duration", DURATION)):
        sheet = workbook.create_sheet(title); sheet.append(headers)
    verification = workbook.create_sheet("verification")
    verification.append(VERIFICATION)
    decision = {key: "" for key in VERIFICATION}
    decision.update({
        "record_id": "google-1", "reviewer": "tool:test", "reviewed_at": datetime(2026, 9, 18),
        "fields_checked": "identity", "identity_status": "tool_confirmed",
        "evidence_url": "https://www.google.com/maps/place/example",
    })
    verification.append([decision[key] for key in VERIFICATION])
    path = tmp_path / "manual.xlsx"; workbook.save(path)
    monkeypatch.setattr(build_catalog_v2, "ROOT", tmp_path)
    database = tmp_path / "catalog.sqlite"; create_database(database)
    with connect(database) as db:
        db.execute("INSERT INTO pois VALUES (?,?,?,?,?,?)", ("poi-1", "usable", "Điểm A", "Hà Nội", None, "unknown"))
        stats = build_catalog_v2.import_manual(db, path, [], "test-build")
        rating = db.execute("SELECT rating,review_count,same_observation FROM ratings").fetchone()
        assert stats["invalid_google_rating_precision"] == 1
        assert tuple(rating) == (None, 24, 0)
