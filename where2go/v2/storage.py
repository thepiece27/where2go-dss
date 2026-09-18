"""SQLite schema and deterministic storage helpers for the v2 catalog."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3

from . import SCHEMA_VERSION


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE source_files(
  source_file_id TEXT PRIMARY KEY, logical_path TEXT NOT NULL, sha256 TEXT NOT NULL,
  role TEXT NOT NULL, received_at TEXT, tool TEXT, use_status TEXT NOT NULL,
  UNIQUE(logical_path, sha256)
);
CREATE TABLE source_records(
  source_record_id TEXT PRIMARY KEY, source_file_id TEXT NOT NULL REFERENCES source_files(source_file_id),
  source_key TEXT NOT NULL, observed_at TEXT, raw_payload TEXT NOT NULL,
  UNIQUE(source_file_id, source_key)
);
CREATE TABLE pois(
  poi_id TEXT PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('usable','needs_review','excluded')),
  display_name TEXT NOT NULL, location TEXT, parent_poi_id TEXT REFERENCES pois(poi_id),
  business_status TEXT NOT NULL CHECK(business_status IN ('open','temporarily_closed','permanently_closed','unknown'))
);
CREATE TABLE source_links(
  poi_id TEXT NOT NULL REFERENCES pois(poi_id), source_record_id TEXT NOT NULL REFERENCES source_records(source_record_id),
  method TEXT NOT NULL, match_score REAL, reviewer TEXT,
  status TEXT NOT NULL CHECK(status IN ('confirmed','ambiguous','unmatched','rejected')),
  notes TEXT, PRIMARY KEY(poi_id, source_record_id)
);
CREATE TABLE field_observations(
  observation_id TEXT PRIMARY KEY, poi_id TEXT REFERENCES pois(poi_id),
  source_record_id TEXT NOT NULL REFERENCES source_records(source_record_id), field_name TEXT NOT NULL,
  value_json TEXT NOT NULL, observed_at TEXT, verified_at TEXT, verification_method TEXT,
  use_status TEXT NOT NULL, notes TEXT
);
CREATE TABLE selected_fields(
  poi_id TEXT NOT NULL REFERENCES pois(poi_id), field_name TEXT NOT NULL,
  observation_id TEXT REFERENCES field_observations(observation_id), value_json TEXT NOT NULL,
  selection_reason TEXT NOT NULL, build_version TEXT NOT NULL,
  PRIMARY KEY(poi_id, field_name)
);
CREATE TABLE opening_intervals(
  interval_id TEXT PRIMARY KEY, poi_id TEXT NOT NULL REFERENCES pois(poi_id),
  observation_id TEXT REFERENCES field_observations(observation_id), day_of_week INTEGER,
  specific_date TEXT, status TEXT NOT NULL CHECK(status IN ('open','closed','unknown')),
  open_minute INTEGER, close_minute INTEGER, closes_next_day INTEGER NOT NULL DEFAULT 0,
  CHECK(day_of_week IS NULL OR day_of_week BETWEEN 0 AND 6),
  CHECK((status='open' AND open_minute IS NOT NULL AND close_minute IS NOT NULL) OR
        (status<>'open' AND open_minute IS NULL AND close_minute IS NULL))
);
CREATE TABLE duration_profiles(
  poi_id TEXT PRIMARY KEY REFERENCES pois(poi_id), short_minutes INTEGER NOT NULL,
  typical_minutes INTEGER NOT NULL, long_minutes INTEGER NOT NULL,
  method TEXT NOT NULL, observation_id TEXT REFERENCES field_observations(observation_id),
  verified_at TEXT, CHECK(short_minutes<=typical_minutes AND typical_minutes<=long_minutes)
);
CREATE TABLE access_points(
  access_id TEXT PRIMARY KEY, poi_id TEXT NOT NULL REFERENCES pois(poi_id),
  latitude REAL NOT NULL, longitude REAL NOT NULL, kind TEXT NOT NULL,
  access_minutes INTEGER NOT NULL, verified INTEGER NOT NULL, method TEXT NOT NULL,
  observation_id TEXT REFERENCES field_observations(observation_id)
);
CREATE TABLE ratings(
  rating_id TEXT PRIMARY KEY, poi_id TEXT NOT NULL REFERENCES pois(poi_id),
  provider TEXT NOT NULL, rating REAL, review_count INTEGER, observed_at TEXT,
  same_observation INTEGER NOT NULL, observation_id TEXT REFERENCES field_observations(observation_id),
  CHECK(rating IS NULL OR rating BETWEEN 1 AND 5),
  CHECK(review_count IS NULL OR review_count>=0)
);
CREATE TABLE poi_categories(
  poi_id TEXT NOT NULL REFERENCES pois(poi_id), category TEXT NOT NULL, is_primary INTEGER NOT NULL,
  observation_id TEXT REFERENCES field_observations(observation_id), PRIMARY KEY(poi_id, category)
);
CREATE TABLE builds(
  build_version TEXT PRIMARY KEY, created_at TEXT NOT NULL, input_hash TEXT NOT NULL,
  model_version TEXT NOT NULL, stats_json TEXT NOT NULL
);
CREATE TABLE poi_aliases(
  poi_id TEXT NOT NULL REFERENCES pois(poi_id), name TEXT NOT NULL, normalized TEXT NOT NULL,
  observation_id TEXT REFERENCES field_observations(observation_id), PRIMARY KEY(poi_id,normalized)
);
CREATE TABLE external_ids(
  provider TEXT NOT NULL, external_id TEXT NOT NULL, poi_id TEXT NOT NULL REFERENCES pois(poi_id),
  observation_id TEXT REFERENCES field_observations(observation_id), PRIMARY KEY(provider,external_id)
);
CREATE TABLE poi_images(
  image_id TEXT PRIMARY KEY, poi_id TEXT NOT NULL REFERENCES pois(poi_id), url TEXT NOT NULL,
  source_url TEXT, provider TEXT NOT NULL, rights_status TEXT NOT NULL,
  identity_status TEXT NOT NULL, validation_status TEXT NOT NULL DEFAULT 'pending',
  checked_at TEXT, content_type TEXT, width INTEGER, height INTEGER,
  observation_id TEXT REFERENCES field_observations(observation_id), UNIQUE(poi_id,url)
);
CREATE TABLE poi_redirects(old_id TEXT PRIMARY KEY, poi_id TEXT NOT NULL REFERENCES pois(poi_id));
CREATE INDEX idx_records_file ON source_records(source_file_id);
CREATE INDEX idx_observations_poi_field ON field_observations(poi_id, field_name);
CREATE INDEX idx_links_record_status ON source_links(source_record_id, status);
CREATE INDEX idx_pois_location_status ON pois(location, status);
"""


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def create_database(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.unlink(missing_ok=True)
    with closing(sqlite3.connect(temp)) as db:
        db.executescript(DDL)
        db.execute("INSERT INTO metadata VALUES ('schema_version',?)", (SCHEMA_VERSION,))
        db.commit()
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Foreign key check failed")
    temp.replace(path)


def connect(path, readonly=False):
    path = Path(path)
    if readonly:
        db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    else:
        db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = sqlite3.Row
    return db
