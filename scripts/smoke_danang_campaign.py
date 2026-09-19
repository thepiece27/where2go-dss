"""Live desktop/mobile smoke for the campaign scope, filters, photos and fallback."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="http://127.0.0.1:8001")
    args = parser.parse_args()
    out = Path("artifacts/danang-smoke"); out.mkdir(parents=True,exist_ok=True)
    report = {"screens":[],"errors":[]}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width, height in [(1440,1000),(390,844)]:
            context = browser.new_context(viewport={"width":width,"height":height})
            page = context.new_page()
            page.on("pageerror",lambda error: report["errors"].append(str(error)))
            page.goto(args.url + "/explore",wait_until="domcontentloaded")
            page.locator("#poiList .poi-card").first.wait_for(timeout=60000)
            assert page.locator("#locationFilter").input_value() == "danang_hoian"
            assert page.locator("#typeFilter").input_value() == "tourism"
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            for category in ("beach","park","water_park","museum"):
                page.locator("#typeFilter").select_option(category)
                page.wait_for_function("category => state.pois.length > 0 && state.pois.every(p => p.category === category)",arg=category)
            page.locator("#typeFilter").select_option("beach")
            page.wait_for_function("state.pois.length > 0 && state.pois.every(p => p.category === 'beach')")
            visible = page.evaluate("state.pois.filter(p => p.image).length")
            assert visible > 0
            page.locator("#poiList .poi-card button").first.click()
            page.locator("#detailPanel h2").wait_for()
            page.screenshot(path=str(out / f"explore-{width}.png"),full_page=True)
            page.goto(args.url,wait_until="domcontentloaded")
            assert page.locator("#tourismScope").input_value() == "danang_hoian"
            assert page.locator("#tourismOnly").input_value() == "true"
            page.locator("#recommendButton").click()
            page.locator("#results .poi-card").first.wait_for(timeout=90000)
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.screenshot(path=str(out / f"recommend-{width}.png"),full_page=True)
            report["screens"].append({"width":width,"status":"PASS","beach_cards_with_image":visible})
            context.close()
        # Offline basemap uses the same campaign filter and is a UI check only.
        context = browser.new_context(viewport={"width":390,"height":844})
        context.route("**/*",lambda route: route.continue_() if route.request.url.startswith(args.url + "/") else route.abort())
        page = context.new_page(); page.goto(args.url + "/explore",wait_until="domcontentloaded")
        page.wait_for_function("document.querySelector('#map').dataset.basemap==='danang'",timeout=60000)
        report["offline_basemap"] = "PASS"
        browser.close()
    assert not report["errors"],report["errors"]
    (out / "verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))


if __name__ == "__main__":
    main()
