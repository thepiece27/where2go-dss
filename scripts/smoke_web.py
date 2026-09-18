"""Browser smoke test against a real local API; screenshot is an artifact, not an accuracy metric."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


BASEMAP_PIXEL_CHECK = """() => [...document.querySelectorAll('.leaflet-basemap-pane canvas')].some(canvas => {
      const context=canvas.getContext('2d');
      if(!context||!canvas.width||!canvas.height)return false;
      const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
      for(let index=3;index<pixels.length;index+=64){if(pixels[index]>0)return true;}
      return false;
    })"""


def wait_for_basemap_pixels(page):
    page.wait_for_function(BASEMAP_PIXEL_CHECK, timeout=15000, polling=500)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--url",default="http://127.0.0.1:8000")
    args=parser.parse_args()
    Path("artifacts").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1000})
        errors=[]
        blocked=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        base=args.url.rstrip("/")
        def local_only(route):
            if route.request.url==base or route.request.url.startswith(base+"/"):
                route.continue_()
            else:
                blocked.append(route.request.url)
                route.abort()
        page.route("**/*",local_only)
        page.goto(args.url,wait_until="networkidle",timeout=60000)
        page.wait_for_function("document.querySelector('#map').dataset.basemap==='hanoi'",timeout=60000)
        assert page.locator("#map canvas").count()>0
        wait_for_basemap_pixels(page)
        assert page.locator("#mapStatus").is_hidden()
        page.locator("#poiList .poi-button").first.wait_for()
        page.locator("#poiList .poi-button").first.click()
        page.locator("#savePoi").wait_for()
        page.locator("#savePoi").click()
        assert page.locator("#savePoi").inner_text()=="Đã lưu"
        assert len(page.evaluate("JSON.parse(localStorage.getItem('where2go-saved-v2'))"))==1
        page.locator("#locationFilter").select_option(label="Đà Nẵng")
        page.wait_for_function("state.pois.length>0 && state.pois.every(p=>p.location==='Đà Nẵng')")
        page.wait_for_function("document.querySelector('#map').dataset.basemap==='danang'",timeout=60000)
        wait_for_basemap_pixels(page)
        page.locator("#poiList .poi-button").first.click()
        page.locator("#savePoi").wait_for()
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
                "basemap":"danang","basemap_canvas_count":page.locator('#map canvas').count(),
                "basemap_render_features":page.locator('#map').get_attribute('data-basemap-features'),
                "basemap_canvas_pixels":"PASS","map_warning":page.locator('#mapStatus').inner_text(),
                "blocked_external_requests":len(blocked)}
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
        assert page.locator("#mapStatus").is_hidden()
        assert not page.locator(".leaflet-tile").count()
        report['offline_local_basemap']='PASS'
        assert not errors,errors

        mobile=browser.new_page(viewport={"width":390,"height":844})
        mobile_errors=[]
        mobile_blocked=[]
        mobile.on("pageerror",lambda error:mobile_errors.append(str(error)))
        def mobile_local_only(route):
            if route.request.url==base or route.request.url.startswith(base+"/"):
                route.continue_()
            else:
                mobile_blocked.append(route.request.url)
                route.abort()
        mobile.route("**/*",mobile_local_only)
        mobile.goto(args.url,wait_until="networkidle",timeout=60000)
        mobile.locator("#poiList .poi-button").first.wait_for()
        mobile.locator("#locationFilter").select_option(label="Hà Nội")
        mobile.wait_for_function("document.querySelector('#map').dataset.basemap==='hanoi'",timeout=60000)
        assert mobile.locator("#map canvas").count()>0
        wait_for_basemap_pixels(mobile)
        assert mobile.locator("#mapStatus").is_hidden()
        mobile.locator("#tripDate").fill("2026-09-20")
        mobile.locator("#interests").fill("văn hóa, lịch sử")
        mobile.locator("#planButton").click()
        mobile.wait_for_function("!document.querySelector('#planButton').disabled",timeout=60000)
        assert mobile.locator("#itinerary .stop").count()>=2
        layout=mobile.evaluate("""() => {
          const sidebar=document.querySelector('.sidebar').getBoundingClientRect();
          const map=document.querySelector('.map-panel').getBoundingClientRect();
          return {viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,
                  sidebarRight:sidebar.right,sidebarBottom:sidebar.bottom,mapTop:map.top,mapRight:map.right};
        }""")
        assert layout["scrollWidth"]<=layout["viewport"]+1,layout
        assert layout["sidebarRight"]<=layout["viewport"]+1 and layout["mapRight"]<=layout["viewport"]+1,layout
        assert layout["sidebarBottom"]<=layout["mapTop"]+1,layout
        mobile.locator("#itinerary").scroll_into_view_if_needed()
        mobile.screenshot(path="artifacts/web-mobile.png",full_page=True)
        assert not mobile_errors,mobile_errors
        report['mobile_layout']='PASS'
        report['mobile_stops']=mobile.locator('#itinerary .stop').count()
        report['mobile_blocked_external_requests']=len(mobile_blocked)
        mobile.close()

        Path("artifacts/web-smoke.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(report))
        browser.close()


if __name__=="__main__": main()
