"""Exercise preference edits in one real browser session against the live catalog/API."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.v2.discovery import region_for  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--before", action="store_true", help="Record the unfixed behavior")
    args = parser.parse_args()
    phase = "before" if args.before else "after"
    output = Path("artifacts/preference_updates") / phase
    output.mkdir(parents=True, exist_ok=True)
    report = {"recorded_at": datetime.now(timezone.utc).isoformat(), "phase": phase, "cases": []}
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))
        # Images are unrelated to this check; API, scripts and DOM are all real.
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(args.url) else route.abort())
        page.goto(args.url, wait_until="domcontentloaded")
        page.locator("#date").fill("2026-09-21")
        page.locator(".extra-settings summary").click()
        page.locator("#latitude").fill("16.0544")
        page.locator("#longitude").fill("108.2022")

        def run(ident, expected_category=None, invalidated=False):
            if invalidated:
                assert page.locator("#results .poi-card").count() == 0
                assert "Nhu cầu đã thay đổi" in page.locator("#resultSummary").inner_text()
            with page.expect_response(lambda r: r.url.endswith("/api/v2/recommendations") and r.request.method == "POST", timeout=120000) as pending:
                page.locator("#recommendButton").click()
            response = pending.value
            assert response.status == 200, response.text()
            payload, data = response.request.post_data_json, response.json()
            page.wait_for_function("lastResult !== null && !document.querySelector('#recommendButton').disabled")
            dom = page.locator("#results .poi-card").evaluate_all("els => els.map(e => e.dataset.poiId)")
            assert dom == [p["poi_id"] for p in data["items"]]
            assert payload["tourism_only"] is True and payload["location"] == "Đà Nẵng"
            assert all(p["explanation"]["distance_km"] <= payload["radius_km"] for p in data["items"])
            if expected_category and not args.before:
                assert data["items"] and data["items"][0]["category"] == expected_category, ident
            record = {"id": ident, "request": payload, "response": data,
                      "categories": dict(Counter(p["category"] for p in data["items"])),
                      "geographic_regions": dict(Counter((region_for(p["latitude"], p["longitude"]) or {}).get("region", "unknown") for p in data["items"])),
                      "checks": {"dom_matches_response": True, "radius_respected": True,
                                 "old_results_cleared_on_edit": invalidated}}
            report["cases"].append(record)
            (output / f"{ident}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"id": ident, "categories": record["categories"],
                              "first": data["items"][0]["name"] if data["items"] else None,
                              "eligible": data["eligible_count"], "candidates": data["candidate_count"]}, ensure_ascii=False), flush=True)
            return data

        baseline = run("P01_default")
        nature_button = page.get_by_role("button", name="thiên nhiên", exact=True)
        spiritual_button = page.get_by_role("button", name="tâm linh", exact=True)
        nature_button.click()
        nature = run("P02_nature", invalidated=True)
        nature_button.click()
        spiritual_button.click()
        spiritual = run("P03_spiritual", "temple", invalidated=True)
        page.screenshot(path=str(output / "spiritual.png"), full_page=True)
        spiritual_button.click()
        nature_button.click()
        repeated = run("P04_back_to_nature", invalidated=True)
        assert [p["poi_id"] for p in repeated["items"]] == [p["poi_id"] for p in nature["items"]]
        if not args.before:
            assert [p["poi_id"] for p in nature["items"]] != [p["poi_id"] for p in spiritual["items"]]
            assert not any(p["category"] == "temple" for p in baseline["items"])
            nature_button.click()
            page.locator("#interests").fill("TAM LINH")
            run("P05_spiritual_text", "temple", invalidated=True)
            page.locator("#interests").fill("")
            page.locator("#categories").select_option(["temple"])
            run("P06_temple_category", "temple", invalidated=True)
            page.locator("#categories").select_option(["cafe"])
            run("P07_cafe_category", "cafe", invalidated=True)
            page.locator("#categories").select_option(["museum"])
            run("P08_museum_category", "museum", invalidated=True)
            page.locator("#categories").select_option([])
            spiritual_button.click()
            page.locator("#preset").select_option("nearby")
            run("P09_spiritual_nearby", "temple", invalidated=True)
            page.locator("#radius").fill("1")
            page.locator("#radius").blur()
            run("P10_spiritual_radius_1", invalidated=True)
            page.locator("#latitude").fill("16.0630")
            page.locator("#longitude").fill("108.2450")
            page.locator("#longitude").blur()
            run("P11_spiritual_coast", invalidated=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#radius").fill("30")
            page.locator("#radius").blur()
            run("P12_spiritual_mobile", "temple", invalidated=True)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "spiritual-mobile.png"), full_page=True)
            page.locator("#latitude").fill("16.0544")
            page.locator("#longitude").fill("108.2022")
            page.locator("#radius").fill("15")
            page.locator("#preset").select_option("balanced")
            local = run("P13_spiritual_danang_only", "temple", invalidated=True)
            assert all((region_for(p["latitude"], p["longitude"]) or {}).get("region") == "danang" for p in local["items"])
        assert not errors, errors
        report["javascript_errors"] = errors
        report["status"] = "RECORDED" if args.before else "PASS"
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()


if __name__ == "__main__":
    main()
