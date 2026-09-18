"""Three-page journeys, actual API/OSRM, mobile fallback and stale-response checks."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    output = Path("artifacts/recommendations")
    output.mkdir(parents=True, exist_ok=True)
    report = {"human_quality": "NOT GRADED"}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base, wait_until="domcontentloaded")
        page.locator("#date").fill("2026-09-20")
        page.get_by_role("button", name="thiên nhiên", exact=True).click()
        page.locator("#recommendButton").focus()
        page.keyboard.press("Enter")
        page.locator("#results .poi-card").first.wait_for(timeout=90000)
        assert page.locator("#results .poi-card").count() == 10
        page.locator("#results summary").first.click()
        assert "Điểm xếp hạng tương đối" in page.locator("#results").inner_text()
        page.screenshot(path=str(output / "recommend-desktop.png"), full_page=True)
        page.locator("#results .add-place").first.click()
        ident = page.locator("#results .poi-card").first.get_attribute("data-poi-id")
        page.get_by_role("link", name="Lịch trình 1", exact=True).click()
        page.wait_for_function("state.selected.size===1")
        assert page.evaluate("id=>state.selected.has(id)", ident)
        page.locator("#planLocation").select_option("Hà Nội")
        assert page.evaluate("state.selected.size") == 0
        page.locator("#planLocation").select_option("Đà Nẵng")
        assert page.evaluate("state.selected.size") == 1
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("state.selected.size===1")
        report["cross_page_city_drafts"] = "PASS"
        # Reuse the old v1 draft shape; the new pages must preserve its fields.
        page.goto(base + "/explore", wait_until="domcontentloaded")
        page.locator("#poiList .poi-card").first.wait_for(timeout=60000)
        page.evaluate(
            """()=>{const d=tripStore.read('Đà Nẵng');d.selected=[];d.required=[];d.chosen=null;d.result=null;d.manualOrder=null;d.fields.tripDate='2026-09-20';d.fields.latitude=16.0544;d.fields.longitude=108.2022;tripStore.save('Đà Nẵng',d);renderList();}"""
        )
        page.locator("#locationFilter").select_option("Đà Nẵng")
        for query, name in (
            ("my khe", "Bãi biển Mỹ Khê"),
            ("pham van dong", "Bãi tắm Phạm Văn Đồng"),
        ):
            page.locator("#searchInput").fill(query)
            card = (
                page.locator("#poiList .poi-card")
                .filter(has=page.get_by_role("button", name=name, exact=True))
                .first
            )
            card.wait_for(timeout=30000)
            card.locator(".add-place").click()
        page.screenshot(path=str(output / "explore-desktop.png"), full_page=True)
        page.goto(base + "/itinerary", wait_until="domcontentloaded")
        page.wait_for_function("state.selected.size===2")
        for checkbox in page.locator("#selectedList .must-visit").all():
            checkbox.check()
        page.locator("#planButton").click()
        page.wait_for_function(
            "!state.busy&&state.result?.options.length>0", timeout=90000
        )
        assert page.evaluate(
            "state.result.options.every(o=>o.coverage.must===2&&o.geometry.coordinates.length>0)"
        )
        page.locator(".choose-option").first.click()
        page.wait_for_function("state.chosen!==null")
        old_choice = page.evaluate("state.chosen.option_id")
        page.locator("#endTime").fill("09:00")
        page.locator("#planButton").click()
        page.wait_for_function(
            "!state.busy&&state.result?.options.some(o=>o.requires_confirmation)",
            timeout=90000,
        )
        page.get_by_role(
            "button", name="Chọn và xem điều chỉnh", exact=True
        ).first.click()
        assert page.locator("#confirmDialog").is_visible()
        page.locator("#cancelOption").click()
        assert page.evaluate("state.chosen.option_id") == old_choice
        page.screenshot(path=str(output / "itinerary-desktop.png"), full_page=True)
        report["actual_osrm_itinerary_confirmation"] = "PASS"
        page.goto(base, wait_until="domcontentloaded")
        assert page.evaluate("""async()=>{const original=window.fetch,pending=[];
          window.fetch=(u,o)=>String(u).includes('/api/v2/recommendations')?new Promise(resolve=>pending.push(resolve)):original(u,o);
          const a=recommend(),b=recommend();const empty={items:[],message:'new-result',personalized:true,routing_message:'',travel_metric:'geographic_distance'};
          pending[1](new Response(JSON.stringify(empty),{status:200}));await b;
          pending[0](new Response(JSON.stringify({...empty,message:'obsolete-result'}),{status:200}));await a;
          window.fetch=original;return document.querySelector('#resultSummary').textContent==='new-result';}""")
        report["stale_response"] = "PASS"
        page.route("https://images.example.invalid/**", lambda route: route.abort())
        page.evaluate("""()=>{const box=document.createElement('div');box.id='broken-image';
            const img=imageElement('https://images.example.invalid/missing.jpg');img.loading='eager';
            box.append(img);document.body.append(box);}""")
        page.locator("#broken-image").get_by_text("Chưa có ảnh").wait_for()
        page.locator("#broken-image").evaluate("el=>el.remove()")
        report["broken_image_fallback"] = "PASS"
        assert not errors, errors
        mobile = browser.new_page(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        mobile_errors = []
        mobile.on("pageerror", lambda error: mobile_errors.append(str(error)))
        mobile.route(
            "**/*",
            lambda route: (
                route.continue_()
                if route.request.url.startswith(base + "/")
                else route.abort()
            ),
        )
        mobile.goto(base, wait_until="domcontentloaded")
        mobile.locator("#recommendButton").click()
        mobile.locator("#results .poi-card").first.wait_for(timeout=90000)
        assert mobile.evaluate("document.documentElement.scrollWidth<=innerWidth")
        mobile.screenshot(path=str(output / "recommend-mobile.png"), full_page=True)
        mobile.goto(base + "/explore", wait_until="domcontentloaded")
        mobile.locator("#locationFilter").select_option("Đà Nẵng")
        mobile.wait_for_function(
            "document.querySelector('#map').dataset.basemap==='danang'", timeout=60000
        )
        assert mobile.evaluate("document.documentElement.scrollWidth<=innerWidth")
        mobile.screenshot(path=str(output / "explore-mobile.png"), full_page=True)
        assert not mobile_errors, mobile_errors
        report["mobile_offline_basemap"] = "PASS"
        report["javascript_errors"] = errors + mobile_errors
        browser.close()
    (output / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
