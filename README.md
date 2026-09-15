# Vietnam POI Recommendation System

This project builds a Vietnam point-of-interest dataset, enriches it with Google Maps fields, shows it in a local web explorer, and implements a POI recommendation system with **Fuzzy AHP**.

## Main Features

- Clean and inspect Vietnam POI data from Excel.
- Fill missing Google Maps fields with a browser scraper.
- Correct province/city names from latitude and longitude.
- Export POIs to a static web app.
- Explore POIs on a map with search and filters.
- Recommend POIs in `poi_recommendation_system.ipynb` using Fuzzy AHP.
- Evaluate the recommendation model against baseline models.

## Project Structure

```text
data/
  vietnam_destinations.xlsx
  vietnam_destinations_google_maps_browser_hotosm.xlsx
  poi_recommendation_cleaned.xlsx
  poi_sample_recommendations.xlsx
  poi_evaluation_metrics.xlsx
  vietnam_provinces_wards_geojson.zip

docs/
  fuzzy_ahp.md
  poi_recommendation_system.md
  google_places_enrichment.md
  location_from_coordinates.md
  osm_hotosm_enrichment.md

scripts/
  scrape_google_maps_browser.py
  fill_location_from_coordinates.py
  export_web_data.py

web/
  index.html
  styles.css
  app.js
  data/pois.json

poi_recommendation_system.ipynb
requirements.txt
```

## Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

If you run the Google Maps browser scraper, install Playwright browser support if needed:

```powershell
python -m playwright install
```

The scraper can also use Microsoft Edge with `--browser-channel msedge`.

## Current Main Dataset

The main workbook is:

```text
data/vietnam_destinations_google_maps_browser_hotosm.xlsx
```

Important columns:

- `Tên địa điểm`
- `Vị trí`
- `Mô tả`
- `Đánh giá `
- `Ảnh`
- `Từ Khóa`
- `maps_latitude`
- `maps_longitude`
- `maps_destination_type`
- `maps_review_count`
- `maps_review_label`
- `maps_first_open_hours`
- `maps_open_hours`
- `maps_url`

## Fill Missing Google Maps Type And Review Count

The scraper currently preserves existing values and only fills missing cells in:

```text
maps_destination_type
maps_review_count
```

Run:

```powershell
python -X utf8 .\scripts\scrape_google_maps_browser.py --input data\vietnam_destinations_google_maps_browser_hotosm.xlsx --output data\vietnam_destinations_google_maps_browser_hotosm.xlsx --browser-channel msedge --timeout-ms 25000 --sleep 1 --workers 3 --save-every 10
```

Small test run:

```powershell
python -X utf8 .\scripts\scrape_google_maps_browser.py --input data\vietnam_destinations_google_maps_browser_hotosm.xlsx --output data\vietnam_destinations_google_maps_browser_hotosm.xlsx --browser-channel msedge --limit 50 --timeout-ms 25000 --sleep 1 --workers 3 --save-every 10
```

## Correct `Vị trí` From Coordinates

Dry run first:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data\vietnam_destinations_google_maps_browser_hotosm.xlsx --dry-run
```

Apply correction:

```powershell
python -X utf8 .\scripts\fill_location_from_coordinates.py --input data\vietnam_destinations_google_maps_browser_hotosm.xlsx
```

The script:

- parses better coordinates from `maps_url` when available;
- maps coordinates to Vietnam province/city GeoJSON polygons;
- writes the corrected province/city name to `Vị trí`;
- creates a timestamped backup before overwriting the workbook.

More details: `docs/location_from_coordinates.md`.

## Run The Web Explorer

Export the Excel workbook to JSON:

```powershell
python -X utf8 .\scripts\export_web_data.py
```

Start the local web server:

```powershell
python -m http.server 8000 --directory web
```

Open:

```text
http://localhost:8000
```

The web app supports:

- map markers;
- search by name, description, location, type, and keywords;
- filters by province/city, type, rating, reviews, and opening hours;
- sorting by quality, review count, rating, or name;
- detail panel with image and Google Maps link.

## Recommendation Notebook

Open:

```text
poi_recommendation_system.ipynb
```

The notebook pipeline:

1. Inspect input data.
2. Clean rows and coordinates.
3. Fill missing values.
4. Normalize rating/review signals.
5. Build separate criteria: content, type, location, distance, quality.
6. Compute Fuzzy AHP ranking.
7. Generate recommendations.
8. Evaluate against baseline models.
9. Export cleaned data, sample recommendations, and metrics.

## Fuzzy AHP Model

The final ranking model is **Fuzzy AHP only**.

Criteria:

```text
content, type, location, distance, quality
```

The pairwise comparison matrix is expert/user input. The notebook does not create this matrix from preset weights.

Main formula:

```text
final_score = fuzzy_ahp_norm
```

Full math reference:

```text
docs/fuzzy_ahp.md
```

System details:

```text
docs/poi_recommendation_system.md
```

## Evaluation

The dataset does not contain real user-click labels, so evaluation uses pseudo relevance labels from held-out profiles.

Baseline models:

- `popularity_baseline`
- `distance_baseline`
- `content_baseline`
- `type_location_baseline`
- `equal_weight_baseline`
- `crisp_ahp_weighted_baseline`
- `fuzzy_ahp`

Metrics:

- Precision@10
- Recall@10
- MAP@10
- MRR@10
- NDCG@10
- type diversity@10
- catalog coverage@10

## Generated Outputs

Recommendation outputs:

```text
data/poi_recommendation_cleaned.xlsx
data/poi_sample_recommendations.xlsx
data/poi_evaluation_metrics.xlsx
```

Web output:

```text
web/data/pois.json
```

## Notes

- Close the Excel workbook before scripts write to it.
- If the scraper cannot write to the original workbook, it may save an `_autosave.xlsx` file.
- Google Maps scraping can produce wrong matches, so suspicious rows should be reviewed.
- The location correction uses current Vietnam province/city boundaries; old province names may be mapped to newer merged units.
