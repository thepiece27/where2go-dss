"""Resolve curated Google search seeds to stable place URLs using name and OSM proximity."""
import argparse
import asyncio
import csv
import json
from pathlib import Path
import random
import re
import sys
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright
from where2go.catalog import haversine
from where2go.config import ROOT
from where2go.v2.catalog import load_catalog
from scripts.review_google_pilot_v2 import name_score


COORDINATES = re.compile(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)")
VIEWPORT_COORDINATES = re.compile(r"/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


def read_seeds(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_seeds(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["record_id", "query", "maps_url"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def candidate_from_anchor(anchor, seed, canonical):
    href = anchor.get("href") or ""
    if "/maps/place/" not in href:
        return None
    label = (anchor.get("aria") or anchor.get("text") or "").strip()
    match = COORDINATES.search(href) or VIEWPORT_COORDINATES.search(href)
    distance = None
    if canonical and match:
        distance = haversine(
            (canonical["latitude"], canonical["longitude"]),
            (float(match.group(1)), float(match.group(2))),
        )
    return {"label": label, "href": href, "name_score": name_score(seed["seed_name"], label),
            "distance_km": distance}


def choose(seed, anchors, catalog):
    canonical = catalog.get(seed.get("canonical_poi_id") or "")
    candidates = [candidate_from_anchor(anchor, seed, canonical) for anchor in anchors]
    candidates = [candidate for candidate in candidates if candidate]
    if canonical:
        broad = seed.get("expected_category") in {"theme_park", "nature_area", "beach", "old_quarter"}
        maximum = 10.0 if broad else 2.0
        acceptable = [candidate for candidate in candidates
                      if candidate["distance_km"] is not None and candidate["distance_km"] <= maximum
                      and candidate["name_score"] >= .15]
        if acceptable:
            return min(acceptable, key=lambda row: (row["distance_km"], -row["name_score"])), candidates
    acceptable = [candidate for candidate in candidates if candidate["name_score"] >= .72]
    return (max(acceptable, key=lambda row: row["name_score"]), candidates) if acceptable else (None, candidates)


async def resolve(seeds, output, report, delay_min=2.0, delay_max=4.0):
    catalog = {poi["poi_id"]: poi for poi in load_catalog()[0]}
    resolved, audit = [], []
    async with async_playwright() as playwright:
        browser = await playwright.firefox.launch(headless=True)
        page = await browser.new_page(locale="en-US")
        for index, seed in enumerate(seeds, 1):
            if index > 1:
                await asyncio.sleep(random.uniform(delay_min, delay_max))
            url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(seed["query"])
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_function(
                    "location.href.includes('/maps/place/') || !!document.querySelector(\"a[href*='/maps/place/']\")",
                    timeout=10000,
                )
            except PlaywrightTimeoutError:
                pass
            await page.wait_for_timeout(1000)
            body = (await page.locator("body").inner_text()).lower()
            if any(token in body for token in ("unusual traffic", "our systems have detected", "captcha")):
                audit.append({"record_id": seed["record_id"], "status": "blocked", "url": page.url})
                break
            anchors = await page.locator("a").evaluate_all(
                "els => els.map(a => ({text:(a.innerText||'').trim(), aria:a.getAttribute('aria-label')||'', href:a.href||''}))"
            )
            if "/maps/place/" in page.url:
                title = (await page.title()).replace(" - Google Maps", "").strip()
                anchors.insert(0, {"text": title, "aria": title, "href": page.url})
            selected, candidates = choose(seed, anchors, catalog)
            audit.append({
                "record_id": seed["record_id"], "seed_name": seed["seed_name"],
                "status": "resolved" if selected else "unresolved", "selected": selected,
                "candidates": candidates[:20],
            })
            if selected:
                resolved.append({
                    **seed, "maps_url": selected["href"],
                    "resolve_method": "search_anchor_name_and_osm_proximity",
                    "resolve_distance_km": "" if selected["distance_km"] is None else round(selected["distance_km"], 4),
                })
            print(f"[{index}/{len(seeds)}] {seed['record_id']}: {'RESOLVED' if selected else 'UNRESOLVED'}", flush=True)
        await browser.close()
    write_seeds(output, resolved)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"resolved": len(resolved), "total": len(seeds), "rows": audit}, ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/google-focus/seeds.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/google-focus-resolved/seeds.csv")
    parser.add_argument("--report", type=Path, default=ROOT / "data/google-focus-resolved/resolution_report.json")
    parser.add_argument("--record-id", action="append", default=[], help="Chỉ resolve các record ID được chỉ định")
    args = parser.parse_args()
    seeds = read_seeds(args.input)
    if args.record_id:
        wanted = set(args.record_id)
        seeds = [row for row in seeds if row["record_id"] in wanted]
    rows = asyncio.run(resolve(seeds, args.output, args.report))
    print(json.dumps({"resolved": len(rows), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
