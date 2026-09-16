# Google Maps Browser Scraper

The Google Maps enrichment script is:

```text
scripts/scrape_google_maps_browser.py
```

It enriches POIs by opening Google Maps in a browser, searching each destination name, and reading fields from the result page.

The current script is configured for a safe resume run: it only fills missing `maps_destination_type` and `maps_review_count`, and it preserves existing values in all other columns.

## Input And Output

Current workbook:

```text
data/vietnam_destinations_google_maps_browser_hotosm.xlsx
```

The same file can be used as both input and output when continuing an interrupted scrape.

## What The Scraper Fills On Resume

When rerun on the current workbook, the scraper writes only these missing fields:

- `maps_destination_type`
- `maps_review_count`

It reads the place heading, type, and review label from the page. Rating, image, and opening-hour collection has been removed because these results were discarded. Existing workbook values for coordinates, opening hours, URL, status, and error fields are preserved. Duplicate rating/image columns are still merged before processing.

If `maps_review_count` is missing but `maps_review_label` already exists, the script parses the count from the existing label before opening the browser for that row.

The recommendation notebook does not run this scraper. It only reads the workbook after scraping is done.

## Command

Example command for continuing the current workbook:

```powershell
python -X utf8 .\scripts\scrape_google_maps_browser.py --input data/vietnam_destinations_google_maps_browser_hotosm.xlsx --output data/vietnam_destinations_google_maps_browser_hotosm.xlsx --browser-channel msedge --start-index 315 --limit 100 --timeout-ms 25000 --sleep 1
```

Useful options:

- `--start-index`: row index to start from
- `--limit`: maximum number of rows to process in this run
- `--skip-existing`: kept for compatibility; existing values are always preserved
- `--browser-channel msedge`: use Microsoft Edge
- `--timeout-ms`: page/action timeout
- `--sleep`: delay between rows

## Notes

Use this scraper when you need to complete missing Google Maps type or review-count fields in the current workbook.

The Fuzzy AHP notebook does not scrape live data. It uses the already saved workbook:

```text
data/vietnam_destinations_google_maps_browser_hotosm.xlsx
```
