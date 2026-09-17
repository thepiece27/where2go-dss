"""Run a small, resumable Google Maps enrichment pilot and retain raw results locally."""
import argparse
import asyncio
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT


def load_seeds(path, limit=None):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[:limit] if limit is not None else rows


def load_existing(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


async def run(seeds, output, language="en", delay_min=3.0, delay_max=5.0):
    try:
        from gmaps_scraper import GoogleMapsScraper, ScrapeConfig
    except ImportError as error:
        raise RuntimeError(
            "Thiếu collector tùy chọn; cài requirements-scraper-v2.txt và chạy playwright install firefox"
        ) from error

    existing = load_existing(output)
    completed = {row["record_id"] for row in existing}
    rows = list(existing)
    config = ScrapeConfig(
        concurrency=1, headless=True, language=language, timeout=60000,
        max_retries=1, delay_min=delay_min, delay_max=delay_max,
    )
    async with GoogleMapsScraper(config) as scraper:
        for index, seed in enumerate(seeds, 1):
            record_id = seed["record_id"]
            if record_id in completed:
                continue
            if rows:
                await asyncio.sleep(random.uniform(delay_min, delay_max))
            query = seed["query"]
            url = seed.get("maps_url") or (
                "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)
            )
            result = await scraper.scrape(url)
            row = {
                "record_id": record_id,
                "canonical_poi_id": seed.get("canonical_poi_id") or "",
                "seed_name": seed["seed_name"],
                "location_expected": seed["location_expected"],
                "expected_category": seed.get("expected_category") or "",
                "query": query,
                "input_url": url,
                "resolve_method": seed.get("resolve_method") or "search_query",
                "resolve_distance_km": seed.get("resolve_distance_km") or None,
                "success": result.success,
                "error": result.error,
                "scraped_at": result.scraped_at.astimezone(timezone.utc).isoformat(),
                "place": result.place.model_dump(mode="json") if result.place else None,
                "collector": "noworneverev/google-maps-scraper@283f50c179da23f36f2df5bb638df5ba5ab9a15b",
                "rights_status": "restricted_internal",
            }
            rows.append(row)
            save(output, rows)
            print(f"[{index}/{len(seeds)}] {record_id}: {'OK' if result.success else 'FAIL'}", flush=True)
            if result.error and any(token in result.error.lower() for token in ("captcha", "unusual traffic", "blocked")):
                print("Collector stopped because Google returned an access challenge.", flush=True)
                break
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=Path, default=ROOT / "data/google-pilot/seeds.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/google-pilot/results.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--language", default="en")
    args = parser.parse_args()
    seeds = load_seeds(args.seeds, args.limit)
    rows = asyncio.run(run(seeds, args.output, args.language))
    print(json.dumps({"results": len(rows), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
