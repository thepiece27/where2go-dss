"""Browser smoke for recommendation intent, hard filters and responsive UI."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8010")
    parser.add_argument("--output", type=Path, default=Path("artifacts/policy-v3"))
    args = parser.parse_args()
    base = args.url.rstrip("/")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"policy": "poi-recommendation-3.0", "checks": {}, "javascript_errors": []}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda error: report["javascript_errors"].append(str(error)))
        page.goto(base, wait_until="domcontentloaded")
        page.locator(".extra-settings summary").click()

        def submit():
            with page.expect_response(
                lambda response: response.url.endswith("/api/v2/recommendations")
                and response.request.method == "POST",
                timeout=120000,
            ) as pending:
                page.locator("#recommendButton").click()
            response = pending.value
            assert response.status == 200, response.text()
            data = response.json()
            page.wait_for_function(
                "lastResult !== null && !document.querySelector('#recommendButton').disabled"
            )
            ids = page.locator("#results .poi-card").evaluate_all(
                "rows => rows.map(row => row.dataset.poiId)"
            )
            assert ids == [item["poi_id"] for item in data["items"]]
            assert data["policy_version"] == report["policy"]
            assert data["ranking"]["criteria_order"] == [
                "preference_match",
                "place_quality",
                "travel_cost",
            ]
            return data

        page.locator("#interests").fill("không thích tâm linh")
        negative = submit()
        assert negative["interpreted_request"]["excluded_categories"] == ["temple"]
        assert all(item["category"] != "temple" for item in negative["items"])
        report["checks"]["negative_intent"] = "PASS"

        page.locator("#interests").fill("chỉ bảo tàng")
        only = submit()
        assert only["items"] and all(item["category"] == "museum" for item in only["items"])
        assert only["interpreted_request"]["category_mode"] == "only"
        report["checks"]["natural_only_category"] = "PASS"

        page.locator("#interests").fill("")
        page.locator("#excludedCategories").select_option(["temple"])
        page.locator("#requireKnownHours").check()
        filtered = submit()
        assert all(item["category"] != "temple" for item in filtered["items"])
        assert all(item["explanation"]["hours_known"] for item in filtered["items"])
        report["checks"]["explicit_exclusion_and_known_hours"] = "PASS"

        page.locator("#categories").select_option(["museum"])
        page.locator("#excludedCategories").select_option([])
        page.locator("#categoryMode").select_option("only")
        page.reload(wait_until="domcontentloaded")
        page.locator(".extra-settings summary").click()
        assert page.locator("#categoryMode").input_value() == "only"
        assert page.locator("#categories").input_value() == "museum"
        report["checks"]["draft_persistence"] = "PASS"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(args.output / "recommend-desktop.png"), full_page=True)
        context.close()

        mobile = browser.new_context(viewport={"width": 390, "height": 844})
        page = mobile.new_page()
        page.on("pageerror", lambda error: report["javascript_errors"].append(str(error)))
        page.goto(base, wait_until="domcontentloaded")
        with page.expect_response(
            lambda response: response.url.endswith("/api/v2/recommendations"),
            timeout=120000,
        ):
            page.locator("#recommendButton").click()
        page.locator("#results .poi-card").first.wait_for(timeout=120000)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(args.output / "recommend-mobile.png"), full_page=True)
        report["checks"]["mobile_no_horizontal_overflow"] = "PASS"
        mobile.close()
        browser.close()

    assert not report["javascript_errors"], report["javascript_errors"]
    report["status"] = "PASS"
    (args.output / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
