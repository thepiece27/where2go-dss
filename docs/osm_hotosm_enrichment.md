# OSM/HOTOSM Enrichment Status

The OSM/HOTOSM enrichment step has already been applied to the current workbook.

Current final input for the recommendation notebook:

```text
data/vietnam_destinations_google_maps_browser_hotosm.xlsx
```

The old OSM/HOTOSM helper scripts were removed from `/scripts` after the workbook was completed. The active workflow no longer rebuilds the dataset from OSM/HOTOSM during normal recommendation-system runs.

## Current Data Shape

The workbook now keeps the useful coordinate/location result in the Google Maps-style columns:

- `maps_latitude`
- `maps_longitude`
- `Vị trí`

Temporary OSM/HOTOSM columns were removed from the workbook after copying:

```text
osm_lat       -> maps_latitude
osm_lng       -> maps_longitude
osm_city      -> Vị trí
```

Removed temporary columns included OSM source fields such as name, kind, tags, address, id, type, URL, and source file.

## How The Recommendation Notebook Uses This Data

The notebook reads:

```text
maps_latitude
maps_longitude
Vị trí
```

Then it:

- validates coordinates with a Vietnam bounding box
- removes rows without usable coordinates
- uses `Vị trí` for the location criterion
- uses coordinates for the distance criterion

## Data Source Note

The enriched workbook includes data derived from OpenStreetMap/HOTOSM and Google Maps scraping. When displaying or publishing OSM-derived data, attribute OpenStreetMap contributors according to the OpenStreetMap license requirements.
