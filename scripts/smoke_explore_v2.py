"""Exercise national discovery, live tiles, named beaches, pagination and offline fallback."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    output = Path("artifacts/enrichment-web")
    output.mkdir(parents=True, exist_ok=True)
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until="domcontentloaded")
        page.wait_for_function("state.pois.length>0 && Number(document.querySelector('#map').dataset.mapPoiCount)>250", timeout=60000)
        page.wait_for_function("document.querySelectorAll('.leaflet-tile-loaded').length>0", timeout=20000)
        assert page.locator("#locationFilter").input_value() == ""
        assert page.evaluate("map.getZoom()") <= 7
        assert page.locator("#locationFilter option").count() == 35
        first_count = page.locator("#poiList .poi-title").count()
        page.locator("#loadMorePois").click()
        page.wait_for_function("document.querySelectorAll('#poiList .poi-title').length>250")
        report["national_discovery"] = {"status": "PASS", "markers": int(page.locator("#map").get_attribute("data-map-poi-count")), "list_first_page": first_count}
        page.locator("#map").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "national-online.png"))
        page.locator("#locationFilter").select_option("Đà Nẵng")
        for query, name in (("my khe", "Bãi biển Mỹ Khê"), ("pham van dong", "Bãi tắm Phạm Văn Đồng")):
            page.locator("#searchInput").fill(query)
            button = page.locator("#poiList .poi-title").filter(has_text=name).first
            button.wait_for(timeout=20000)
            button.click()
            page.wait_for_function("name=>document.querySelector('#detailPanel h2')?.textContent===name", arg=name)
            page.wait_for_function("(()=>{const img=document.querySelector('#detailPanel img');return img&&img.complete&&img.naturalWidth>=200})()", timeout=20000)
            report[query] = {"status": "PASS", "name": name, "image_loaded": True}
        page.locator("#map").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "danang-beach-online.png"))
        page.locator("#locationFilter").select_option("Huế")
        assert page.locator("#planLocation").input_value() == "Đà Nẵng"
        assert page.evaluate("requestPayload().location") == "Đà Nẵng"
        page.locator("#viewVietnam").click()
        assert page.locator("#locationFilter").input_value() == ""
        assert not errors, errors
        report["online"] = "PASS"
        report["page_errors"] = errors
        page.route("https://images.example.invalid/**", lambda route: route.abort())
        page.evaluate("()=>{const box=document.createElement('div');box.id='image-fallback-probe';document.body.append(box);const img=imageElement('https://images.example.invalid/missing.jpg');img.loading='eager';box.append(img);}")
        page.locator("#image-fallback-probe").get_by_text("Chưa có ảnh").wait_for()
        report["broken_image_fallback"] = "PASS"
        page.close()

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_errors = []
        mobile.on("pageerror", lambda e: mobile_errors.append(str(e)))
        mobile.route("**/*", lambda route: route.continue_() if route.request.url.startswith(args.url.rstrip('/') + '/') else route.abort())
        mobile.goto(args.url, wait_until="domcontentloaded")
        mobile.wait_for_function("state.pois.length>0", timeout=60000)
        assert mobile.evaluate("nationalLayer.getLayers().length") == 34
        mobile.locator("#locationFilter").select_option("Đà Nẵng")
        mobile.locator('.view-tabs [data-view="map"]').click()
        mobile.wait_for_function("document.querySelector('#map').dataset.basemap==='danang'", timeout=60000)
        assert mobile.locator("#mapStatus").is_visible()
        assert mobile.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        mobile.locator("#map").scroll_into_view_if_needed()
        mobile.screenshot(path=str(output / "mobile-offline.png"))
        assert not mobile_errors, mobile_errors
        report["mobile_offline"] = "PASS"
        report["mobile_page_errors"] = mobile_errors
        browser.close()
    (output / "smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
