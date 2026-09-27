"""Screen live recommendation scenarios and replay selected journeys in Chromium."""

import argparse
from collections import Counter
from copy import deepcopy
import csv
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import statistics
import sys
import time

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.v2.discovery import region_for  # noqa: E402

BASE = dict(location="Đà Nẵng", scope="danang_hoian", tourism_only=True,
            date="2026-09-21", start=dict(latitude=16.0544, longitude=108.2022),
            interests=[], experience_topics=[], preferred_categories=[], excluded_categories=[],
            category_mode="preferred", require_known_hours=False, allow_non_matching=False,
            preset="balanced",
            radius_km=15, top_k=10, selected_poi_ids=[])
POSITIONS = {"center": BASE["start"], "coast": dict(latitude=16.063, longitude=108.245),
             "south": dict(latitude=16.015, longitude=108.25)}


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def summary(data):
    items = data["items"]
    return dict(count=len(items), categories=dict(Counter(p["category"] for p in items)),
                regions=dict(Counter((region_for(p["latitude"], p["longitude"]) or {}).get("region", "unknown") for p in items)),
                first_three=[p["name"] for p in items[:3]],
                mean_km=statistics.mean(p["explanation"]["distance_km"] for p in items) if items else None,
                mean_quality=statistics.mean(p["criteria"]["place_quality"] for p in items) if items else None,
                zero_match=sum(p["criteria"]["preference_match"] <= 1e-12 for p in items),
                images=sum(bool(p.get("image")) for p in items),
                travel_metric=data["travel_metric"], eligible=data["eligible_count"], candidates=data["candidate_count"])


def compare(a, b):
    before = [p["poi_id"] for p in a["response"]["items"]]
    after = [p["poi_id"] for p in b["response"]["items"]]
    return dict(before=a["id"], after=b["id"],
                changed_fields=[k for k in a["request"] if a["request"][k] != b["request"][k]],
                overlap=len(set(before) & set(after)), added=len(set(after) - set(before)),
                removed=len(set(before) - set(after)), identical_order=before == after,
                same_metric=a["response"]["travel_metric"] == b["response"]["travel_metric"],
                same_pool_counts=(a["response"]["eligible_count"], a["response"]["candidate_count"]) == (b["response"]["eligible_count"], b["response"]["candidate_count"]))


def sweep(args):
    cases = {}
    def add(ident, **changes):
        cases[ident] = deepcopy(BASE) | changes

    topics = {"nature": ["thiên nhiên"], "history": ["lịch sử"], "culture": ["văn hóa"],
              "history_culture": ["lịch sử", "văn hóa"], "spiritual": ["tâm linh"],
              "family": ["gia đình"], "art": ["nghệ thuật"], "photo": ["chụp ảnh"],
              "relax": ["thư giãn"], "food": ["ẩm thực"]}
    add("default")
    for topic, preset in itertools.product(topics, ["balanced", "interests", "nearby", "quality"]):
        add(f"topic_{topic}_{preset}", experience_topics=topics[topic], preset=preset)
    texts = {"sea": "biển", "museum": "bảo tàng", "indoor": "trong nhà", "museum_indoor": "bảo tàng, trong nhà",
             "avoid_sea": "không thích biển", "spiritual_ascii": "tam linh"}
    for key, preset in itertools.product(texts, ["balanced", "interests", "nearby", "quality"]):
        add(f"text_{key}_{preset}", interests=[t.strip() for t in texts[key].split(",")], preset=preset)
    for category, preset in itertools.product(["beach", "museum", "temple", "park", "historic", "cafe"], ["balanced", "interests"]):
        add(f"category_{category}_{preset}", preferred_categories=[category], preset=preset)
    for position, radius, profile in itertools.product(POSITIONS, [1, 3, 5, 10, 15], ["nature", "sea"]):
        add(f"geo_{position}_{radius}_{profile}", start=POSITIONS[position], radius_km=radius,
            experience_topics=["thiên nhiên"] if profile == "nature" else ["biển"], preset="nearby")
    add("nature_with_beach", experience_topics=["thiên nhiên"], preferred_categories=["beach"], preset="interests")
    add("sea_with_beach", experience_topics=["biển"], preferred_categories=["beach"], preset="interests")
    for date in ["2026-09-22", "2026-09-27"]:
        add(f"date_{date}", interests=["lịch sử", "văn hóa"], date=date)
    add("spiritual_radius_1", interests=["tâm linh"], radius_km=1)
    add("empty_mountains", interests=["gia đình"], start=dict(latitude=16.15, longitude=108.05), radius_km=1)
    out = Path(args.output)
    evidence = dict(started_at=datetime.now(timezone.utc).isoformat(),
                    selection_criteria=["single changed field", "all displayed coordinates in danang",
                                        "clear Top-3 and membership change", "same cost metric for causal comparison",
                                        "browser replay and repeatability", "retain weak cases in evidence"], cases=[])
    session = requests.Session()
    evidence["health_before"] = session.get(args.url + "/api/health", timeout=30).json()
    for i, (ident, request) in enumerate(cases.items(), 1):
        start = time.perf_counter()
        response = session.post(args.url + "/api/v2/recommendations", json=request, timeout=120)
        response.raise_for_status()
        data = response.json()
        assert all(p["explanation"]["distance_km"] <= request["radius_km"] + 1e-8 for p in data["items"])
        row = dict(id=ident, request=request, response=data, summary=summary(data), seconds=round(time.perf_counter()-start, 3))
        evidence["cases"].append(row)
        dump(out / "sweep" / f"{ident}.json", row)
        if i % 10 == 0 or i == len(cases):
            print(f"Completed {i}/{len(cases)}: {ident}", flush=True)
    evidence["health_after"] = session.get(args.url + "/api/health", timeout=30).json()
    evidence["completed_at"] = datetime.now(timezone.utc).isoformat()
    pairs = []
    for a, b in itertools.combinations(evidence["cases"], 2):
        c = compare(a, b)
        if len(c["changed_fields"]) == 1:
            c["all_danang"] = all(set(r["summary"]["regions"]) == {"danang"} for r in (a, b))
            pairs.append(c)
    evidence["comparisons"] = pairs
    dump(out / "screening.json", evidence)
    with (out / "comparisons.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(sorted(pairs, key=lambda r: (-r["added"], r["before"], r["after"])))
    print(json.dumps({"cases": len(cases), "single_field_comparisons": len(pairs)}, ensure_ascii=False))


def browser_run(args):
    from playwright.sync_api import sync_playwright

    root = Path(args.output)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    source = {c["id"]: c for c in json.loads((root / "screening.json").read_text(encoding="utf-8"))["cases"]}
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "journeys": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        report["chromium"] = browser.version
        for journey in plan:
            context = browser.new_context(viewport={"width": 1440, "height": 1080})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(args.url, wait_until="domcontentloaded")
            page.locator(".extra-settings summary").click()
            rows = []
            for index, step in enumerate(journey["steps"]):
                target = source[step["case"]]["request"]
                # User-visible fields only; retain local draft and the browser session.
                for selector, val in [("location", target["location"]), ("tourismScope", target["scope"]),
                                      ("tourismOnly", str(target["tourism_only"]).lower()),
                                      ("categoryMode", target["category_mode"]), ("preset", target["preset"])]:
                    if page.locator("#" + selector).input_value() != val:
                        page.locator("#" + selector).select_option(val)
                for selector, val in [("date", target["date"]), ("radius", str(target["radius_km"])),
                                      ("latitude", str(target["start"]["latitude"])), ("longitude", str(target["start"]["longitude"]))]:
                    if page.locator("#" + selector).input_value() != val:
                        page.locator("#" + selector).fill(val)
                        page.locator("#" + selector).blur()
                page.locator("#categories").select_option(target["preferred_categories"])
                page.locator("#excludedCategories").select_option(target["excluded_categories"])
                page.locator("#requireKnownHours").set_checked(target["require_known_hours"])
                page.locator("#allowNonMatching").set_checked(target["allow_non_matching"])
                wanted_topics = target["experience_topics"]
                for text in page.locator('#topics button[aria-pressed="true"]').all_text_contents():
                    if text not in wanted_topics:
                        page.get_by_role("button", name=text, exact=True).click()
                for text in wanted_topics:
                    button = page.get_by_role("button", name=text, exact=True)
                    if button.get_attribute("aria-pressed") != "true":
                        button.click()
                page.locator("#interests").fill(step.get("text", ""))
                assert page.locator("#results .poi-card").count() == 0
                with page.expect_response(lambda r: r.url.endswith("/api/v2/recommendations") and r.request.method == "POST", timeout=120000) as pending:
                    page.locator("#recommendButton").click()
                response = pending.value
                assert response.status == 200
                actual_request, data = response.request.post_data_json, response.json()
                assert actual_request == target, (step, actual_request, target)
                page.wait_for_function("lastResult !== null && !document.querySelector('#recommendButton').disabled")
                ids = page.locator("#results .poi-card").evaluate_all("els=>els.map(e=>e.dataset.poiId)")
                assert ids == [p["poi_id"] for p in data["items"]]
                assert ids == [p["poi_id"] for p in source[step["case"]]["response"]["items"]]
                assert all((region_for(p["latitude"], p["longitude"]) or {}).get("region") == "danang" for p in data["items"])
                first = page.locator("#results .score-detail summary").first
                if first.count():
                    first.click()
                folder = root / "browser" / journey["id"]
                folder.mkdir(parents=True, exist_ok=True)
                page.locator("#resultSummary").scroll_into_view_if_needed()
                page.screenshot(path=str(folder / f"{index+1:02}.png"))
                (folder / f"{index+1:02}.txt").write_text(page.locator("body").inner_text(), encoding="utf-8")
                # Load lazy images before recording their actual browser state.
                # An image may be replaced by its fallback while loading. Scroll
                # the stable cards so an image error cannot detach our locator.
                for card in page.locator("#results .poi-card").all():
                    card.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                images = page.locator("#results .poi-card").evaluate_all("els=>els.map(e=>({id:e.dataset.poiId,loaded:!!e.querySelector('img')?.naturalWidth,fallback:e.querySelector('.photo')?.textContent==='Chưa có ảnh'}))")
                row = dict(id=step["case"], request=actual_request, response=data, summary=summary(data),
                           checks=dict(http_200=True, dom_matches_response=True, matches_screening=True, all_danang=True),
                           images=images)
                if rows:
                    row["difference"] = compare(rows[-1], row)
                rows.append(row)
                dump(folder / f"{index+1:02}.json", row)
                print(f"Browser {journey['id']} step {index+1}: {step['case']} PASS", flush=True)
            # Send the last request again with no edits to verify deterministic UI output.
            with page.expect_response(lambda r: r.url.endswith("/api/v2/recommendations") and r.request.method == "POST", timeout=120000) as pending:
                page.locator("#recommendButton").click()
            repeat = pending.value.json()
            assert [p["poi_id"] for p in repeat["items"]] == [p["poi_id"] for p in rows[-1]["response"]["items"]]
            assert not errors, errors
            report["journeys"].append(dict(id=journey["id"], steps=rows, javascript_errors=errors, repeat_same_order=True))
            context.close()
        browser.close()
    report["status"] = "PASS"
    dump(root / "browser_report.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["sweep", "browser"])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", default="artifacts/demo_selection_20260921")
    parser.add_argument("--plan", default="scripts/demo_danang_selected_plan.json")
    args = parser.parse_args()
    sweep(args) if args.mode == "sweep" else browser_run(args)
