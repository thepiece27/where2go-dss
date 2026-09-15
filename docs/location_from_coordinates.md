# Correct Location From Coordinates

Use `scripts/fill_location_from_coordinates.py` to correct the `Vị trí` column from latitude/longitude.

The script uses Vietnam province/city GeoJSON boundaries, then maps each POI coordinate to the province/city polygon that contains it.

## Why This Is Needed

Some rows have location text that is incomplete or stale.

Some rows also have `maps_latitude` and `maps_longitude` that do not match the more precise coordinates embedded in `maps_url`. The script therefore prefers coordinates parsed from `maps_url` when available.

## Data Source

The boundary cache is downloaded from:

```text
https://raw.githubusercontent.com/thanglequoc/vietnamese-provinces-database/master/json/vn_provinces_wards_geojson.zip
```

It is saved locally as:

```text
data/vietnam_provinces_wards_geojson.zip
```

The current source dataset contains Vietnam's province-level units and GIS GeoJSON boundaries.

## Dry Run

Run this first to inspect how many rows would change:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data/vietnam_destinations_google_maps_browser_hotosm.xlsx --dry-run
```

## Apply Correction

This overwrites the input workbook and creates a timestamped backup first:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data/vietnam_destinations_google_maps_browser_hotosm.xlsx
```

If the workbook is open in Excel, the script may not be able to write to the original file and will save an `_autosave.xlsx` file instead.

## Useful Options

Use full province/city names:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data/vietnam_destinations_google_maps_browser_hotosm.xlsx --name-style full_name
```

Only fill empty `Vị trí` cells:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data/vietnam_destinations_google_maps_browser_hotosm.xlsx --only-missing
```

Do not parse coordinates from `maps_url`:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data/vietnam_destinations_google_maps_browser_hotosm.xlsx --no-url-coordinates
```

Disable nearest-boundary fallback:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data/vietnam_destinations_google_maps_browser_hotosm.xlsx --no-nearest-fallback
```
