import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.fill_location_from_coordinates import (
        DEFAULT_BOUNDARY_CACHE,
        DEFAULT_BOUNDARY_URL,
        ensure_boundary_cache,
        load_provinces,
        province_for_point,
    )
except Exception:
    DEFAULT_BOUNDARY_CACHE = None
    DEFAULT_BOUNDARY_URL = None
    ensure_boundary_cache = None
    load_provinces = None
    province_for_point = None


INPUT_PATH = Path("data/vietnam_destinations_google_maps_browser_hotosm.xlsx")
OUTPUT_PATH = Path("web/data/pois.json")


def value_present(value):
    if pd.isna(value):
        return False
    return str(value).strip() != ""


def clean_text(value, default=""):
    if not value_present(value):
        return default
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def parse_rating(value):
    text = clean_text(value).replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    rating = float(match.group(1))
    if 0 <= rating <= 5:
        return rating
    if 0 <= rating <= 10:
        return rating / 2
    return None


def parse_number(value):
    if not value_present(value):
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return int(value)
    text = clean_text(value)
    match = re.search(r"([\d][\d,.\s]*)", text)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def parse_keywords(value):
    text = clean_text(value)
    if not text:
        return []
    text = text.replace("“", '"').replace("”", '"')
    parts = re.split(r"[,;|]", text)
    keywords = []
    for part in parts:
        token = part.strip().strip('"').strip("'").strip()
        token = re.sub(r"\s+", " ", token)
        if token and token not in keywords:
            keywords.append(token)
    return keywords


def parse_coordinates_from_maps_url(url):
    text = clean_text(url)
    if not text:
        return None
    place_matches = re.findall(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", text)
    if place_matches:
        lat, lng = place_matches[-1]
        return float(lat), float(lng)
    viewport_match = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),", text)
    if viewport_match:
        return float(viewport_match.group(1)), float(viewport_match.group(2))
    return None


def valid_vietnam_coordinate(lat, lng):
    return lat is not None and lng is not None and 7.0 <= lat <= 24.5 and 102.0 <= lng <= 110.5


def safe_float(value):
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return float(parsed)


def minmax(values):
    numeric = [value for value in values if value is not None and not math.isnan(value)]
    if not numeric:
        return [0.0 for _ in values]
    low = min(numeric)
    high = max(numeric)
    if low == high:
        return [0.0 for _ in values]
    return [0.0 if value is None else (value - low) / (high - low) for value in values]


def main():
    df = pd.read_excel(INPUT_PATH)
    provinces = []
    if ensure_boundary_cache and load_provinces and province_for_point:
        try:
            boundary_cache = ensure_boundary_cache(DEFAULT_BOUNDARY_CACHE, DEFAULT_BOUNDARY_URL)
            provinces = load_provinces(boundary_cache)
        except Exception as error:
            print(f"Could not load province boundaries for web export: {error}")

    ratings = [parse_rating(value) for value in df.get("Đánh giá ", [])]
    reviews = [
        parse_number(count) if parse_number(count) is not None else parse_number(label)
        for count, label in zip(df.get("maps_review_count", []), df.get("maps_review_label", []))
    ]
    review_logs = [math.log1p(value or 0) for value in reviews]
    review_norm = minmax(review_logs)

    pois = []
    for index, row in df.iterrows():
        url = clean_text(row.get("maps_url"))
        lat = safe_float(row.get("maps_latitude"))
        lng = safe_float(row.get("maps_longitude"))
        url_coordinates = parse_coordinates_from_maps_url(url)
        if url_coordinates and valid_vietnam_coordinate(*url_coordinates):
            lat, lng = url_coordinates

        location = clean_text(row.get("Vị trí"), "Việt Nam")
        if provinces and valid_vietnam_coordinate(lat, lng):
            province, _ = province_for_point(float(lat), float(lng), provinces, nearest_max_km=25.0)
            if province and province.get("name"):
                location = province["name"]

        rating = ratings[index] if index < len(ratings) else None
        review_count = reviews[index] if index < len(reviews) else None
        has_image = 1 if value_present(row.get("Ảnh")) else 0
        has_hours = 1 if value_present(row.get("maps_first_open_hours")) or value_present(row.get("maps_open_hours")) else 0
        quality = (
            0.55 * ((rating or 0) / 5)
            + 0.35 * review_norm[index]
            + 0.05 * has_image
            + 0.05 * has_hours
        )

        if not valid_vietnam_coordinate(lat, lng):
            continue

        pois.append({
            "id": int(row.get("STT")) if value_present(row.get("STT")) else int(index + 1),
            "name": clean_text(row.get("Tên địa điểm"), "Không rõ tên"),
            "resultName": clean_text(row.get("maps_result_name")),
            "location": location,
            "description": clean_text(row.get("Mô tả")),
            "rating": round(rating, 2) if rating is not None else None,
            "image": clean_text(row.get("Ảnh")),
            "keywords": parse_keywords(row.get("Từ Khóa")),
            "matchStatus": clean_text(row.get("maps_match_status")),
            "lat": round(float(lat), 7),
            "lng": round(float(lng), 7),
            "type": clean_text(row.get("maps_destination_type"), "Unknown"),
            "reviewCount": review_count or 0,
            "reviewLabel": clean_text(row.get("maps_review_label")),
            "hours": clean_text(row.get("maps_first_open_hours")) or clean_text(row.get("maps_open_hours")),
            "url": url,
            "quality": round(quality, 4),
        })

    meta = {
        "source": str(INPUT_PATH),
        "count": len(pois),
        "locations": sorted({poi["location"] for poi in pois if poi["location"]}),
        "types": sorted({poi["type"] for poi in pois if poi["type"]}),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps({"meta": meta, "pois": pois}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Exported {len(pois)} POIs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
