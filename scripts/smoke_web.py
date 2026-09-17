"""Browser smoke test against a real local API; screenshot is an artifact, not an accuracy metric."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--url",default="http://127.0.0.1:8000")
    args=parser.parse_args()
    Path("artifacts").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1000})
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until="networkidle",timeout=60000)
        page.locator("#savePoi").wait_for()
        page.locator("#savePoi").click()
        assert page.locator("#savePoi").inner_text()=="Đã lưu"
        assert len(page.evaluate("JSON.parse(localStorage.getItem('where2go-saved-v2'))"))==1
        page.locator("#locationFilter").select_option(label="Đà Nẵng")
        page.wait_for_function("document.querySelector('#detailPanel').textContent.includes('Đà Nẵng')")
        page.locator("#savePoi").click()
        assert len(page.evaluate("JSON.parse(localStorage.getItem('where2go-saved-v2'))"))==2
        page.locator("#tripDate").fill("2026-09-20")
        page.locator("#interests").fill("văn hóa, lịch sử")
        page.locator('#tripCategories input[value="historic"]').check()
        page.locator("#planButton").click()
        page.wait_for_function("!document.querySelector('#planButton').disabled",timeout=60000)
        text=page.locator("#itinerary").inner_text()
        assert "Quay về:" in text,text
        assert page.locator("#itinerary .stop").count()>=2
        attraction=page.locator('#itinerary .stop').filter(has=page.locator('.duration-editor')).first
        duration=attraction.locator('input[type="number"]')
        required_id=page.evaluate("state.lastPlan.blocks.find(b=>b.role==='attraction').poi_id")
        page.evaluate("id=>state.required.add(id)",required_id)
        requested=min(720,int(duration.input_value())+5)
        duration.fill(str(requested))
        attraction.get_by_role("button",name="Tính lại").click()
        page.wait_for_function("!document.querySelector('#planButton').disabled",timeout=60000)
        assert page.locator('#itinerary .duration-editor input').first.input_value()==str(requested)
        page.locator("#itinerary").scroll_into_view_if_needed()
        page.wait_for_timeout(1200)
        page.screenshot(path="artifacts/web-itinerary.png",full_page=True)
        # Malformed data goes through DOM setters, never HTML string interpolation.
        safe=page.evaluate("""() => {const x=imageElement('https://upload.wikimedia.org/a.jpg\\" onerror=\\"alert(1)');return !x.getAttribute('onerror');}""")
        assert safe
        assert not errors,errors
        page.evaluate("()=>{state.required.clear();state.durationOverrides={};}")
        report={"status":"PASS","stops":page.locator('#itinerary .stop').count(),"page_errors":errors,
                "map_tiles_loaded":page.locator('.leaflet-tile').evaluate_all('(xs)=>xs.filter(x=>x.naturalWidth>0).length'),
                "map_warning":page.locator('#mapStatus').inner_text()}
        page.locator("#typeFilter").select_option("museum")
        page.wait_for_function("state.pois.length>0 && state.pois.every(p=>p.category==='museum')")
        assert page.locator('#itinerary .stop').count()==0
        page.locator("#planButton").click()
        page.wait_for_function("!document.querySelector('#planButton').disabled",timeout=60000)
        assert page.locator('#itinerary .stop').count()>=2
        assert page.evaluate("state.pois.every(p=>p.location==='Đà Nẵng')")
        assert page.evaluate("state.lastPlan.blocks.filter(b=>b.role==='attraction').some(b=>b.category!=='museum')")
        report['list_filter_separate_from_trip_preference']='PASS'
        page.locator('#onlyCategories').check()
        page.locator("#planButton").click()
        page.wait_for_function("!document.querySelector('#planButton').disabled",timeout=60000)
        assert page.evaluate("state.lastPlan.blocks.filter(b=>b.role==='attraction').every(b=>b.category==='historic')")
        report['thematic_mode']='PASS'
        # Simulate only loss of external tiles; local route/API remain real.
        page.route("https://tile.openstreetmap.org/**",lambda route:route.abort())
        page.reload(wait_until="networkidle")
        page.wait_for_function("!document.querySelector('#mapStatus').hidden")
        assert "Không tải được" in page.locator('#mapStatus').inner_text()
        report['tile_failure_message']='PASS'
        assert not errors,errors
        Path("artifacts/web-smoke.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(report))
        browser.close()


if __name__=="__main__": main()
