"""Consumer journey against a running API + OSRM, plus isolated browser race/outage probes."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    output = Path("artifacts/trip-choices")
    output.mkdir(parents=True, exist_ok=True)
    report = {"real_api_osrm": "NOT RUN", "desktop": "NOT RUN", "mobile_offline": "NOT RUN",
              "browser_race_probe": "NOT RUN", "human_usability": "NOT RUN"}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until="domcontentloaded")
        page.wait_for_function("state.pois.length > 0 && Number(document.querySelector('#map').dataset.mapPoiCount)>250", timeout=60000)
        assert page.evaluate("map.getZoom()") <= 7
        assert page.locator("#autoAdd").is_checked() is False
        assert page.locator("#prefQuality").count() == 0
        page.locator("#tripDate").fill("2026-09-20")
        page.locator("#locationFilter").select_option("Đà Nẵng")
        for text, name in (("my khe", "Bãi biển Mỹ Khê"), ("pham van dong", "Bãi tắm Phạm Văn Đồng")):
            page.locator("#searchInput").fill(text)
            card = page.locator("#poiList .poi-card").filter(has=page.get_by_role("button", name=name, exact=True)).first
            card.wait_for(timeout=30000)
            card.get_by_role("button", name="Thêm vào chuyến đi", exact=True).click()
            card.get_by_role("checkbox").check()
        page.wait_for_function("state.selected.size===2&&state.required.size===2")
        page.locator("#locationFilter").select_option("Huế")
        assert page.evaluate("state.selected.size") == 2
        assert page.locator("#planLocation").input_value() == "Đà Nẵng"
        page.locator("#planButton").click()
        page.wait_for_function("!state.busy && state.result?.options.length>0", timeout=90000)
        result = page.evaluate("state.result")
        assert all(o["coverage"]["must"] == 2 for o in result["options"])
        assert all(o["geometry"]["coordinates"] for o in result["options"])
        report["real_api_osrm"] = {"status": "PASS", "options": len(result["options"]), "elapsed_ms": result["elapsed_ms"], "dataset_version": result["dataset_version"]}
        page.locator(".choose-option").first.click()
        page.wait_for_function("state.chosen!==null")
        assert page.locator("#timeline .timeline-stop").count() == 2
        chosen_id = page.evaluate("state.chosen.option_id")
        stop = page.locator("#timeline .timeline-stop").first
        ident = stop.get_attribute("data-poi-id")
        duration = stop.locator('input[type="number"]')
        target = int(duration.input_value()) + 7
        duration.fill(str(target))
        stop.get_by_role("button", name="Tính lại", exact=True).click()
        page.wait_for_function("!state.busy && !state.stale", timeout=90000)
        assert page.evaluate("state.chosen.option_id") == chosen_id, "Previous chosen plan must remain until acceptance"
        assert page.evaluate("([id,d])=>state.result.options.every(o=>o.timeline.find(t=>t.poi_id===id&&t.role==='visit').duration_minutes===d)", [ident, target])
        page.locator(".choose-option").first.click()
        page.wait_for_function("id=>state.chosen.option_id!==id", arg=chosen_id)
        move = page.locator("#timeline .timeline-stop").first.locator('button[aria-label$=" xuống"]')
        move.focus()
        move.press("Enter")
        page.wait_for_function("!state.busy&&!state.stale", timeout=90000)
        assert page.evaluate("state.result.options.every(o=>JSON.stringify(o.scheduled_poi_ids)===JSON.stringify(state.manualOrder))")
        page.locator(".choose-option").first.click()
        page.locator("#workspace").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "desktop-timeline.png"))
        selected_id = page.evaluate("state.chosen.option_id")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("state.selected.size===2&&state.chosen!==null")
        assert page.evaluate("state.chosen.option_id") == selected_id
        page.locator("#planLocation").select_option("Hà Nội")
        assert page.evaluate("state.selected.size") == 0
        page.locator("#planLocation").select_option("Đà Nẵng")
        assert page.evaluate("state.selected.size") == 2
        # A constrained request must explain what choosing the partial/shifted option accepts.
        page.locator("#endTime").fill("09:00")
        page.locator("#planButton").click()
        page.wait_for_function("!state.busy&&state.result.options.some(o=>o.requires_confirmation)", timeout=90000)
        page.locator(".option-card").filter(has=page.get_by_role("button", name="Chọn và xem điều chỉnh", exact=True)).first.locator(".choose-option").click()
        assert page.locator("#confirmDialog").is_visible()
        assert page.locator("#confirmationChanges").inner_text().strip()
        page.locator("#cancelOption").click()
        assert page.evaluate("state.chosen.option_id") == selected_id
        page.locator(".option-card").filter(has=page.get_by_role("button", name="Chọn và xem điều chỉnh", exact=True)).first.locator(".choose-option").click()
        page.locator("#confirmOption").click()
        page.wait_for_function("!document.querySelector('#confirmDialog').open")
        report["desktop"] = "PASS"
        # Resolve two deliberately controlled responses in reverse order. Real backend tested above.
        assert page.evaluate("""async () => {
          const realFetch=window.fetch,pending=[];window.fetch=(url,options)=>String(url).includes('/trip-suggestions')?new Promise(resolve=>pending.push(resolve)):realFetch(url,options);
          const result=structuredClone(state.result);const first=submitPlan();const second=submitPlan();
          pending[1](new Response(JSON.stringify({...result,message:'newest-request'}),{status:200}));await second;
          pending[0](new Response(JSON.stringify({...result,message:'obsolete-request'}),{status:200}));await first;
          window.fetch=realFetch;return state.result.message==='newest-request'&&!state.busy;
        }""")
        report["browser_race_probe"] = "PASS"
        page.route("https://images.example.invalid/**", lambda route: route.abort())
        page.evaluate("()=>{const box=document.createElement('div');box.id='broken-image';const img=imageElement('https://images.example.invalid/a.jpg');img.loading='eager';box.append(img);document.body.append(box);}")
        page.locator("#broken-image").get_by_text("Chưa có ảnh").wait_for()
        report["image_error"] = "PASS"
        assert not errors, errors
        report["desktop_page_errors"] = errors

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mobile_errors = []
        mobile.on("pageerror", lambda e: mobile_errors.append(str(e)))
        mobile.route("**/*", lambda route: route.continue_() if route.request.url.startswith(args.url.rstrip('/') + '/') else route.abort())
        mobile.goto(args.url, wait_until="domcontentloaded")
        mobile.wait_for_function("state.pois.length>0", timeout=60000)
        mobile.locator("#locationFilter").select_option("Đà Nẵng")
        mobile.locator("#searchInput").fill("pham van dong")
        card = mobile.locator("#poiList .poi-card").filter(has=mobile.get_by_role("button", name="Bãi tắm Phạm Văn Đồng", exact=True)).first
        card.wait_for(timeout=30000)
        card.locator(".add-place").click()
        card.get_by_role("checkbox").check()
        mobile.locator('[data-view="selected"]').click()
        assert mobile.locator("#selectedList .selected-card").count() == 1
        must = mobile.locator("#selectedList .must-visit")
        must.focus()
        must.press("Space")
        assert not mobile.locator("#selectedList .must-visit").is_checked()
        assert mobile.evaluate("document.activeElement.classList.contains('must-visit')")
        mobile.locator("#selectedList .must-visit").press("Space")
        assert mobile.locator("#selectedList .must-visit").is_checked()
        report["keyboard_controls"] = "PASS"
        mobile.locator("#selectedPlan").click()
        mobile.wait_for_function("!state.busy && state.result?.options.length>0", timeout=90000)
        mobile.locator(".choose-option").first.click()
        mobile.locator("#workspace").scroll_into_view_if_needed()
        assert mobile.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        mobile.screenshot(path=str(output / "mobile-timeline.png"))
        mobile.locator('.view-tabs [data-view="map"]').click()
        mobile.wait_for_function("offline && document.querySelector('#map').dataset.basemap==='danang'", timeout=30000)
        assert mobile.locator("#mapStatus").is_visible()
        assert mobile.evaluate("nationalLayer.getLayers().length") == 34
        mobile.locator("#mapPanel").scroll_into_view_if_needed()
        mobile.screenshot(path=str(output / "mobile-map-offline.png"))
        assert not mobile_errors, mobile_errors
        report["mobile_offline"] = "PASS"
        report["mobile_page_errors"] = mobile_errors
        browser.close()
    (output / "smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
