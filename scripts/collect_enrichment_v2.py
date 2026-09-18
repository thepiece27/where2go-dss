"""Collect a bounded missing-field queue with resumable per-attempt checkpoints."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.v2.google_collector import collect_page


async def collect(seeds, output, retry=False, retry_status=("transient_error", "unresolved")):
    from playwright.async_api import async_playwright
    rows = json.loads(output.read_text(encoding="utf-8")) if output.exists() else []
    latest = {row["record_id"]: row for row in rows}
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(locale="en-US", viewport={"width": 1440, "height": 1000})
        for seed in seeds:
            previous = latest.get(seed["record_id"])
            if previous and (not retry or previous["status"] not in retry_status):
                continue
            page = await context.new_page()
            try:
                result = await collect_page(page, seed)
            except Exception as error:
                result = {"status": "transient_error", "success": False, "error": str(error)[:500], "place": None}
            finally:
                await page.close()
            row = {**seed, **result, "scraped_at": datetime.now(timezone.utc).isoformat(),
                   "collector": "where2go.google_collector.v1", "rights_status": "restricted_internal"}
            rows.append(row)
            output.parent.mkdir(parents=True, exist_ok=True)
            temp = output.with_suffix(".tmp")
            temp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(output)
            print(json.dumps({"record_id": row["record_id"], "name": seed["seed_name"], "status": row["status"],
                              "image": bool((row.get("place") or {}).get("image_url"))}, ensure_ascii=False), flush=True)
            if row["status"] == "blocked":
                break
            await asyncio.sleep(3)
        await browser.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--retry-status", default="transient_error,unresolved")
    parser.add_argument("--gate", type=Path, default=Path("data/reports/v2/collection_pilot.json"))
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error("limit phải thuộc [1,200]")
    if args.limit > 20:
        gate = json.loads(args.gate.read_text(encoding="utf-8")) if args.gate.exists() else {}
        if gate.get("expansion_gate") != "PASS" or gate.get("unique_results") != 20 or gate.get("accepted", 0) < 19:
            parser.error("Pilot 20 POI chưa đạt điều kiện mở rộng 19/20")
    seeds = json.loads(args.seeds.read_text(encoding="utf-8-sig"))[:args.limit]
    asyncio.run(collect(seeds, args.output, args.retry, tuple(args.retry_status.split(","))))


if __name__ == "__main__":
    main()
