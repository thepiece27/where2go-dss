import argparse
import json
import math
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

try:
    from matplotlib.path import Path as MatplotlibPath
except Exception:
    MatplotlibPath = None


DEFAULT_INPUT = "data/vietnam_destinations_google_maps_browser_hotosm.xlsx"
DEFAULT_BOUNDARY_CACHE = "data/vietnam_provinces_wards_geojson.zip"
DEFAULT_BOUNDARY_URL = (
    "https://raw.githubusercontent.com/thanglequoc/vietnamese-provinces-database/"
    "master/json/vn_provinces_wards_geojson.zip"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Correct the province/city name in a location column from latitude/longitude "
            "using Vietnam province GeoJSON boundaries."
        )
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input Excel/CSV file.")
    parser.add_argument("--output", default=None, help="Output file. Defaults to overwriting input.")
    parser.add_argument("--lat-col", default="maps_latitude", help="Latitude column.")
    parser.add_argument("--lng-col", default="maps_longitude", help="Longitude column.")
    parser.add_argument("--url-col", default="maps_url", help="Google Maps URL column.")
    parser.add_argument("--location-col", default="Vị trí", help="Column to update with province/city name.")
    parser.add_argument("--boundary-url", default=DEFAULT_BOUNDARY_URL, help="Boundary zip URL.")
    parser.add_argument("--boundary-cache", default=DEFAULT_BOUNDARY_CACHE, help="Local boundary zip cache.")
    parser.add_argument(
        "--name-style",
        choices=["name", "full_name"],
        default="name",
        help='Use "name" like "Khánh Hòa" or "full_name" like "Tỉnh Khánh Hòa".',
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only fill rows where the location column is empty. Default overwrites matched rows.",
    )
    parser.add_argument(
        "--no-nearest-fallback",
        action="store_true",
        help="Do not use nearest province boundary when a point is just outside all polygons.",
    )
    parser.add_argument(
        "--nearest-max-km",
        type=float,
        default=25.0,
        help="Maximum distance for nearest-boundary fallback. Use 0 to disable distance limit.",
    )
    parser.add_argument(
        "--no-url-coordinates",
        action="store_true",
        help="Do not parse more precise coordinates from maps_url.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show summary without writing output.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a backup when overwriting input.")
    return parser.parse_args()


def read_table(path):
    suffix = Path(path).suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input format: {suffix}")


def write_table(df, path):
    output_path = Path(path)
    suffix = output_path.suffix.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if suffix in [".xlsx", ".xls"]:
        df.to_excel(output_path, index=False)
        return output_path
    if suffix == ".csv":
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path
    raise ValueError(f"Unsupported output format: {suffix}")


def backup_file(path):
    source = Path(path)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = source.with_name(f"{source.stem}_backup_{stamp}{source.suffix}")
    shutil.copy2(source, backup)
    return backup


def value_present(value):
    if pd.isna(value):
        return False
    return str(value).strip() != ""


def ensure_boundary_cache(cache_path, url):
    cache = Path(cache_path)
    if cache.exists() and cache.stat().st_size > 0:
        return cache

    cache.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Vietnam province boundaries: {url}", flush=True)
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    cache.write_bytes(response.content)
    return cache


def iter_rings(geometry):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        yield coordinates
    elif geometry_type == "MultiPolygon":
        for polygon in coordinates:
            yield polygon


def ring_bbox(ring):
    lngs = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return min(lngs), min(lats), max(lngs), max(lats)


def bbox_contains(bbox, lng, lat):
    min_lng, min_lat, max_lng, max_lat = bbox
    return min_lng <= lng <= max_lng and min_lat <= lat <= max_lat


def point_on_segment(lng, lat, x1, y1, x2, y2, eps=1e-10):
    cross = (lat - y1) * (x2 - x1) - (lng - x1) * (y2 - y1)
    if abs(cross) > eps:
        return False
    dot = (lng - x1) * (lng - x2) + (lat - y1) * (lat - y2)
    return dot <= eps


def point_in_ring(lng, lat, ring):
    inside = False
    count = len(ring)
    if count < 3:
        return False

    j = count - 1
    for i in range(count):
        x_i, y_i = ring[i][0], ring[i][1]
        x_j, y_j = ring[j][0], ring[j][1]

        if point_on_segment(lng, lat, x_i, y_i, x_j, y_j):
            return True

        intersects = ((y_i > lat) != (y_j > lat)) and (
            lng < (x_j - x_i) * (lat - y_i) / ((y_j - y_i) or 1e-30) + x_i
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def prepare_geometry(geometry):
    prepared = []
    for polygon in iter_rings(geometry):
        if not polygon:
            continue
        outer = polygon[0]
        holes = polygon[1:]
        prepared.append({
            "outer": outer,
            "outer_bbox": ring_bbox(outer),
            "outer_path": MatplotlibPath([(point[0], point[1]) for point in outer]) if MatplotlibPath else None,
            "holes": [(hole, ring_bbox(hole)) for hole in holes],
            "hole_paths": [
                (MatplotlibPath([(point[0], point[1]) for point in hole]), ring_bbox(hole))
                for hole in holes
            ] if MatplotlibPath else [],
        })
    return prepared


def point_in_prepared_polygon(lng, lat, prepared_polygon):
    if not bbox_contains(prepared_polygon["outer_bbox"], lng, lat):
        return False
    if prepared_polygon.get("outer_path") is not None:
        if not prepared_polygon["outer_path"].contains_point((lng, lat), radius=1e-12):
            return False
        for hole_path, hole_bbox in prepared_polygon["hole_paths"]:
            if bbox_contains(hole_bbox, lng, lat) and hole_path.contains_point((lng, lat), radius=1e-12):
                return False
    else:
        if not point_in_ring(lng, lat, prepared_polygon["outer"]):
            return False
        for hole, hole_bbox in prepared_polygon["holes"]:
            if bbox_contains(hole_bbox, lng, lat) and point_in_ring(lng, lat, hole):
                return False
    return True


def distance_to_bbox_km(lat, lng, bbox):
    min_lng, min_lat, max_lng, max_lat = bbox
    clamped_lng = min(max(lng, min_lng), max_lng)
    clamped_lat = min(max(lat, min_lat), max_lat)
    return haversine_km(lat, lng, clamped_lat, clamped_lng)


def flatten_points(geometry):
    for polygon in iter_rings(geometry):
        for ring in polygon:
            for lng, lat, *_ in ring:
                yield lng, lat


def haversine_km(lat1, lng1, lat2, lng2):
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_provinces(cache_path):
    provinces = []
    with zipfile.ZipFile(cache_path) as archive:
        province_files = [
            name for name in archive.namelist()
            if name.startswith("geojson/")
            and name.endswith(".geojson")
            and "/wards/" not in name
        ]
        for name in province_files:
            data = json.loads(archive.read(name).decode("utf-8"))
            features = data.get("features", [data])
            for feature in features:
                properties = feature.get("properties", {})
                geometry = feature.get("geometry") or {}
                all_points = list(flatten_points(geometry))
                if not all_points:
                    continue
                lngs = [point[0] for point in all_points]
                lats = [point[1] for point in all_points]
                provinces.append({
                    "name": properties.get("name"),
                    "full_name": properties.get("fullName") or properties.get("full_name"),
                    "prepared_polygons": prepare_geometry(geometry),
                    "bbox": (min(lngs), min(lats), max(lngs), max(lats)),
                })
    if not provinces:
        raise ValueError("No province GeoJSON features found in boundary cache.")
    return provinces


def province_for_point(lat, lng, provinces, use_nearest_fallback=True, nearest_max_km=25.0):
    bbox_candidates = []
    for province in provinces:
        if not bbox_contains(province["bbox"], lng, lat):
            continue
        bbox = province["bbox"]
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        bbox_candidates.append((bbox_area, province))
        for polygon in province["prepared_polygons"]:
            if point_in_prepared_polygon(lng, lat, polygon):
                return province, "polygon"

    if not use_nearest_fallback:
        return None, "unmatched"

    if bbox_candidates:
        return sorted(bbox_candidates, key=lambda item: item[0])[0][1], "bbox"

    nearest = None
    nearest_distance = None
    for province in provinces:
        distance = distance_to_bbox_km(lat, lng, province["bbox"])
        if nearest_distance is None or distance < nearest_distance:
            nearest = province
            nearest_distance = distance

    if nearest_max_km > 0 and nearest_distance is not None and nearest_distance > nearest_max_km:
        return None, "unmatched"
    return nearest, "nearest" if nearest else "unmatched"


def parse_coordinates_from_maps_url(url):
    if not value_present(url):
        return None
    text = str(url)
    place_matches = re.findall(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", text)
    if place_matches:
        lat, lng = place_matches[-1]
        return float(lat), float(lng)

    viewport_match = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),", text)
    if viewport_match:
        return float(viewport_match.group(1)), float(viewport_match.group(2))
    return None


def valid_vietnam_coordinate(lat, lng):
    return 7.0 <= lat <= 24.5 and 102.0 <= lng <= 110.5


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    df = read_table(input_path)
    for column in [args.lat_col, args.lng_col, args.location_col]:
        if column not in df.columns:
            raise KeyError(f"Input file does not contain required column: {column}")

    cache = ensure_boundary_cache(args.boundary_cache, args.boundary_url)
    provinces = load_provinces(cache)

    updated = 0
    coordinates_updated = 0
    unmatched = 0
    nearest_used = 0
    examples = []

    for row_index, row in df.iterrows():
        if args.only_missing and value_present(row.get(args.location_col)):
            continue

        lat = pd.to_numeric(row.get(args.lat_col), errors="coerce")
        lng = pd.to_numeric(row.get(args.lng_col), errors="coerce")
        url_coordinates = None
        if not args.no_url_coordinates and args.url_col in df.columns:
            url_coordinates = parse_coordinates_from_maps_url(row.get(args.url_col))
            if url_coordinates and valid_vietnam_coordinate(*url_coordinates):
                url_lat, url_lng = url_coordinates
                if pd.isna(lat) or pd.isna(lng) or haversine_km(float(lat), float(lng), url_lat, url_lng) > 0.2:
                    coordinates_updated += 1
                    if not args.dry_run:
                        df.at[row_index, args.lat_col] = url_lat
                        df.at[row_index, args.lng_col] = url_lng
                lat, lng = url_lat, url_lng

        if pd.isna(lat) or pd.isna(lng):
            unmatched += 1
            continue

        province, match_method = province_for_point(
            float(lat),
            float(lng),
            provinces,
            use_nearest_fallback=not args.no_nearest_fallback,
            nearest_max_km=args.nearest_max_km,
        )
        if not province:
            unmatched += 1
            continue

        new_location = province["full_name"] if args.name_style == "full_name" else province["name"]
        if not value_present(new_location):
            unmatched += 1
            continue

        old_location = row.get(args.location_col)
        if str(old_location).strip() != str(new_location).strip():
            updated += 1
            if len(examples) < 10:
                examples.append((row_index, row.get("Tên địa điểm"), old_location, new_location, match_method))
            if not args.dry_run:
                df.at[row_index, args.location_col] = new_location
        if match_method == "nearest":
            nearest_used += 1

    print(f"Province boundary features: {len(provinces)}")
    print(f"Rows changed: {updated}")
    print(f"Coordinate fixes from maps_url: {coordinates_updated}")
    print(f"Rows unmatched/skipped due missing coordinates: {unmatched}")
    print(f"Nearest fallback matches: {nearest_used}")
    if examples:
        print("Examples:")
        for row_index, name, old_location, new_location, method in examples:
            print(f"  row={row_index} name={name!r}: {old_location!r} -> {new_location!r} ({method})")

    if args.dry_run:
        print("Dry run only. No file written.")
        return

    if output_path.resolve() == input_path.resolve() and not args.no_backup:
        backup = backup_file(input_path)
        print(f"Backup saved: {backup}")

    try:
        saved_path = write_table(df, output_path)
    except PermissionError:
        autosave_path = output_path.with_name(f"{output_path.stem}_autosave{output_path.suffix}")
        saved_path = write_table(df, autosave_path)
        print(f"Could not write {output_path}; workbook may be open. Saved to: {saved_path}")
    else:
        print(f"Saved: {saved_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
