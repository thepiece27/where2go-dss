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
        page.locator("#tripDate").fill("2026-09-20")
        page.locator("#interests").fill("văn hóa, lịch sử")
        page.locator("#planButton").click()
        page.wait_for_function("!document.querySelector('#planButton').disabled",timeout=60000)
        text=page.locator("#itinerary").inner_text()
        assert "Quay về:" in text,text
        assert page.locator("#itinerary .stop").count()>=2
        page.locator("#itinerary").scroll_into_view_if_needed()
        page.wait_for_timeout(1200)
        page.screenshot(path="artifacts/web-itinerary.png",full_page=True)
        # Malformed data goes through DOM setters, never HTML string interpolation.
        safe=page.evaluate("""() => {const x=imageElement('https://upload.wikimedia.org/a.jpg\\" onerror=\\"alert(1)');return !x.getAttribute('onerror');}""")
        assert safe
        assert not errors,errors
        print(json.dumps({"status":"PASS","stops":page.locator('#itinerary .stop').count(),"page_errors":errors}))
        browser.close()


if __name__=="__main__": main()
