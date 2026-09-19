"""Run real Chromium/API/OSRM journeys in Da Nang and preserve evidence (no mocks)."""

import argparse
import hashlib
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from where2go.v2.discovery import region_for  # noqa: E402

CITY = "Đà Nẵng"
CENTER = (16.0544, 108.2022)
COAST = (16.0630, 108.2450)
DATE = "2026-09-20"

# Expectations are declared before requesting results, not inferred from scores.
REC_CASES = [
    dict(id="R01", title="Lần đầu đến Đà Nẵng, chưa biết chọn gì", text="", expected="Có gợi ý theo vị trí; không tự nhận đã biết sở thích."),
    dict(id="R02", title="Muốn thiên nhiên và thư giãn", topics=["thiên nhiên"], expected="Tăng ưu tiên công viên, biển, cảnh quan so với yêu cầu văn hóa."),
    dict(id="R03", title="Giữ sở thích thiên nhiên, chuyển sang Đi gần", topics=["thiên nhiên"], preset="nearby", compare="R02", expected="Quan sát khoảng cách và thứ tự; không yêu cầu mọi POI đều gần hơn."),
    dict(id="R04", title="Giữ sở thích thiên nhiên, ưu tiên đánh giá", topics=["thiên nhiên"], preset="quality", compare="R02", expected="Tăng ảnh hưởng chất lượng đã hiệu chỉnh theo số lượt đánh giá."),
    dict(id="R05", title="Muốn tìm hiểu lịch sử, văn hóa", topics=["lịch sử", "văn hóa"], compare="R02", expected="Danh sách chuyển về bảo tàng, di tích và loại hình văn hóa."),
    dict(id="R06", title="Muốn ra biển, chọn rõ loại hình Bãi biển", topics=["thiên nhiên"], categories=["beach"], preset="interests", compare="R02", expected="Biển được ưu tiên; loại hình là ưu tiên mềm, kiểm tra mức pha trộn."),
    dict(id="R07", title="Cùng nhu cầu ra biển nhưng xuất phát gần Mỹ Khê", topics=["thiên nhiên"], categories=["beach"], preset="interests", origin=COAST, compare="R06", expected="Chi phí di chuyển thay đổi theo tọa độ, có thể đổi thứ hạng."),
    dict(id="R08", title="Chỉ muốn đi trong bán kính 1 km từ gần Mỹ Khê", topics=["thiên nhiên"], categories=["beach"], preset="interests", origin=COAST, radius=1, compare="R07", expected="Mọi POI phải trong 1 km đường chim bay; được phép ít hơn 10 kết quả."),
    dict(id="R09", title="Gia đình tìm điểm ở sườn núi, bán kính quá hẹp", topics=["gia đình"], origin=(16.1500, 108.0500), radius=1, expected="Nếu không có dữ liệu phù hợp phải báo rỗng, không tự mở rộng bán kính."),
    dict(id="R10", title="Ngày mưa: muốn bảo tàng, trong nhà", text="bảo tàng, trong nhà", categories=["museum"], preset="interests", expected="Bảo tàng nên nổi bật; kiểm tra có lẫn nơi ngoài trời không."),
    dict(id="R11", title="Nhập ngắn: biển", text="biển", expected="Thiết lập đối chứng để kiểm tra khả năng hiểu phủ định."),
    dict(id="R12", title="Nhập: không thích biển", text="không thích biển", compare="R11", expected="Theo ý định người thật, phải giảm gợi ý biển; nếu vẫn ưu tiên biển là hạn chế ngữ nghĩa."),
    dict(id="R13", title="Tìm cà phê nhưng để nhóm Tham quan và ngoài trời", text="cà phê", categories=["cafe"], preset="interests", tourism=True, expected="Nhóm lọc hiện tại loại cà phê; đánh giá mức dễ hiểu của kết quả đối với người dùng."),
    dict(id="R14", title="Sửa nhóm thành Tất cả loại hình để tìm cà phê", text="cà phê", categories=["cafe"], preset="interests", tourism=False, compare="R13", expected="Cà phê có thể xuất hiện trở lại khi bỏ bộ lọc loại trừ."),
    dict(id="R15", title="Vẫn thích lịch sử, văn hóa nhưng chuyển sang thứ Hai", topics=["lịch sử", "văn hóa"], date="2026-09-21", compare="R05", expected="Chỉ thay đổi do dữ liệu lịch mở cửa; không bắt buộc đảo hạng nếu dữ liệu không khác."),
    dict(id="R16", title="Chọn một điểm rồi xin gợi ý tiếp", topics=["thiên nhiên"], compare="R02", select_first=True, expected="POI đã chọn không bị gợi ý lại, lựa chọn được giữ khi chuyển trang và tải lại."),
    dict(id="R17", title="Thiên nhiên nhưng chỉ 5 km quanh trung tâm", topics=["thiên nhiên"], radius=5, compare="R02", expected="Tất cả kết quả trong 5 km; kiểm tra có dùng được thời gian đường ô tô khi pool nhỏ hơn."),
    dict(id="R18", title="Cùng thiên nhiên, ưu tiên Hợp sở thích", topics=["thiên nhiên"], preset="interests", compare="R02", expected="Tăng trọng số sở thích; kết quả có thể giữ nguyên nếu các tiêu chí cùng ủng hộ một nhóm."),
    dict(id="R19", title="Kiểm tra ranh giới: chọn Đà Nẵng, mở rộng bán kính 30 km", text="bảo tàng, trong nhà", categories=["museum"], preset="interests", radius=30, compare="R10", expected="Ý định chỉ Đà Nẵng không bao gồm Hội An; kiểm tra vùng theo tọa độ, không chỉ nhãn location."),
]

TRIP_CASES = [
    dict(id="T01", title="Hai bãi biển trong một ngày, cả hai bắt buộc", expected="Có lịch ghé đủ hai điểm và quay về trong 08:00–18:00."),
    dict(id="T02", title="Chỉ còn một giờ nhưng vẫn yêu cầu hai biển", end="09:00", compare="T01", expected="Không âm thầm bỏ điểm bắt buộc hoặc kéo dài; điều chỉnh phải xin xác nhận."),
    dict(id="T03", title="Một giờ, mỗi bãi biển chỉ dừng 10 phút", end="09:00", duration=10, compare="T02", expected="Giữ đúng 10 phút; kiểm tra việc rút thời lượng có giúp đủ hai điểm không."),
    dict(id="T04", title="Một giờ, ưu tiên bắt buộc Mỹ Khê, điểm kia tùy chọn", end="09:00", must_count=1, compare="T02", expected="Tôn trọng điểm bắt buộc, công khai điểm tùy chọn chưa xếp được."),
    dict(id="T05", title="Đổi điểm xuất phát sang gần Mỹ Khê", origin=COAST, compare="T01", expected="Đường đi và thời gian lái xe thay đổi theo điểm xuất phát."),
    dict(id="T06", title="Muốn ghé Phạm Văn Đồng trước Mỹ Khê", reverse=True, compare="T01", expected="Các phương án giữ thứ tự chỉnh tay; công khai ảnh hưởng đến thời gian."),
    dict(id="T07", title="Muốn nghỉ ăn và uống cà phê trong ngày", meals=True, coffee=True, compare="T01", expected="Lịch có khối nghỉ phù hợp; không giả định một nhà hàng đã được đặt hoặc chọn."),
    dict(id="T08", title="Hai biển, bật tự bổ sung điểm tham quan", auto_add=True, compare="T01", expected="Tối đa ba điểm thêm, công khai danh sách và vẫn giữ các điểm bắt buộc."),
    dict(id="T09", title="Muốn ở mỗi biển 6 giờ trong ngày 10 giờ", duration=360, compare="T01", expected="Không thể ghé đủ trong khung ban đầu; phải báo thiếu hoặc đề xuất có xác nhận."),
    dict(id="T10", title="Một giờ, dừng mỗi nơi 10 phút, chỉ Mỹ Khê bắt buộc", duration=10, end="09:00", must_count=1, compare="T03", expected="Nếu chỉ ghé Mỹ Khê thì phải công khai bỏ Phạm Văn Đồng; không cần xác nhận bỏ điểm bắt buộc vì đã đổi thành tùy chọn."),
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def capture(page, out, ident, request, response, elapsed):
    page.screenshot(path=str(out / f"{ident}.png"), full_page=True)
    text = page.locator("body").inner_text()
    (out / f"{ident}.txt").write_text(text, encoding="utf-8")
    write_json(out / f"{ident}.json", dict(request=request, response=response, elapsed_seconds=elapsed))
    return dict(screenshot=str((out / f"{ident}.png").relative_to(ROOT)).replace("\\", "/"),
                visible_text=str((out / f"{ident}.txt").relative_to(ROOT)).replace("\\", "/"),
                raw=str((out / f"{ident}.json").relative_to(ROOT)).replace("\\", "/"))


def post_by_click(page, button, endpoint):
    started = time.perf_counter()
    with page.expect_response(lambda r: r.url.endswith(endpoint) and r.request.method == "POST", timeout=120000) as pending:
        page.locator(button).click()
    response = pending.value
    assert response.status == 200, response.text()
    return response.request.post_data_json, response.json(), round(time.perf_counter() - started, 3)


def rec_case(browser, base, out, case):
    context = browser.new_context(viewport={"width": 1440, "height": 1080})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base, wait_until="domcontentloaded")
    page.locator("#location").select_option(CITY)
    page.locator("#tourismScope").select_option("")
    page.locator("#tourismOnly").select_option(str(case.get("tourism", True)).lower())
    page.locator("#date").fill(case.get("date", DATE))
    page.locator("#preset").select_option(case.get("preset", "balanced"))
    page.locator("#radius").fill(str(case.get("radius", 15)))
    page.locator(".extra-settings summary").click()
    page.locator("#categories").select_option(case.get("categories", []))
    lat, lon = case.get("origin", CENTER)
    page.locator("#latitude").fill(str(lat))
    page.locator("#longitude").fill(str(lon))
    page.locator("#interests").fill(case.get("text", ""))
    for topic in case.get("topics", []):
        page.get_by_role("button", name=topic, exact=True).click()
    request, data, elapsed = post_by_click(page, "#recommendButton", "/api/v2/recommendations")
    page.wait_for_function("lastResult !== null && !document.querySelector('#recommendButton').disabled")
    selected_id = None
    persistence = None
    if case.get("select_first"):
        selected_id = data["items"][0]["poi_id"]
        page.locator("#results .add-place").first.click()
        request, data, elapsed = post_by_click(page, "#recommendButton", "/api/v2/recommendations")
        page.wait_for_function("lastResult !== null && !document.querySelector('#recommendButton').disabled")
    if data["items"]:
        page.locator("#results summary").first.click()
    evidence = capture(page, out, case["id"], request, data, elapsed)
    names_dom = page.locator("#results .poi-card").evaluate_all("els => els.map(e=>e.dataset.poiId)")
    if selected_id:
        page.get_by_role("link", name="Lịch trình 1", exact=True).click()
        page.wait_for_function("typeof state !== 'undefined' && state.selected?.size === 1")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("typeof state !== 'undefined' && state.selected?.size === 1")
        persistence = page.evaluate("id => state.selected.has(id)", selected_id)
    items = [{k: p[k] for k in ("poi_id", "name", "category", "location", "latitude", "longitude", "score", "criteria", "reasons", "warnings", "explanation")} for p in data["items"]]
    for p in items:
        p["geographic_region"] = (region_for(p["latitude"], p["longitude"]) or {}).get("region", "unverified")
    checks = dict(http_200=True, dom_matches_response=names_dom == [p["poi_id"] for p in items],
                  danang_only=all(p["location"] == CITY for p in items),
                  danang_geographic_region=all(p["geographic_region"] == "danang" for p in items),
                  radius_respected=all(p["explanation"]["distance_km"] <= request["radius_km"] + 1e-8 for p in items),
                  selected_excluded=all(p["poi_id"] not in request["selected_poi_ids"] for p in items),
                  no_javascript_errors=not errors)
    if persistence is not None:
        checks["selection_survives_navigation_reload"] = persistence
    result = dict(case=case, request=request, items=items, checks=checks, errors=errors, evidence=evidence,
                  elapsed_seconds=elapsed, summary={k: v for k, v in data.items() if k != "items"},
                  mean_distance_km=statistics.mean(p["explanation"]["distance_km"] for p in items) if items else None,
                  mean_quality=statistics.mean(p["criteria"]["place_quality"] for p in items) if items else None)
    context.close()
    return result


def trip_case(browser, base, out, case):
    context = browser.new_context(viewport={"width": 1440, "height": 1080})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base + "/explore", wait_until="domcontentloaded")
    page.locator('#locationFilter option[value="Đà Nẵng"]').wait_for(state="attached")
    page.locator("#locationFilter").select_option(CITY)
    selected = []
    for query, name in [("my khe", "Bãi biển Mỹ Khê"), ("pham van dong", "Bãi tắm Phạm Văn Đồng")]:
        page.locator("#searchInput").fill(query)
        card = page.locator("#poiList .poi-card").filter(has=page.get_by_role("button", name=name, exact=True)).first
        card.wait_for()
        selected.append(card.get_attribute("data-poi-id"))
        card.locator(".add-place").click()
    page.get_by_role("link", name="Lịch trình 2", exact=True).click()
    page.wait_for_function("typeof state !== 'undefined' && state.selected?.size === 2")
    page.locator(".extra-settings summary").click()
    page.locator("#tripDate").fill(DATE)
    page.locator("#startTime").fill("08:00")
    page.locator("#endTime").fill(case.get("end", "18:00"))
    page.locator("#includeMeals").set_checked(case.get("meals", False))
    page.locator("#includeCoffee").set_checked(case.get("coffee", False))
    page.locator("#autoAdd").set_checked(case.get("auto_add", False))
    page.locator('button[data-view="selected"]').click()
    for i in range(case.get("must_count", 2)):
        page.locator("#selectedList .must-visit").nth(i).check()
    if "duration" in case:
        for i in range(2):
            page.locator('#selectedList input[type="number"]').nth(i).fill(str(case["duration"]))
            page.locator('#selectedList input[type="number"]').nth(i).press("Tab")
    if case.get("reverse"):
        page.get_by_role("button", name="Đưa Bãi tắm Phạm Văn Đồng lên", exact=True).click()
    if "origin" in case:
        page.locator("#latitude").fill(str(case["origin"][0]))
        page.locator("#longitude").fill(str(case["origin"][1]))
    request, data, elapsed = post_by_click(page, "#planButton", "/api/v2/trip-suggestions")
    page.wait_for_function("!state.busy && state.result !== null")
    extra = {}
    options = data.get("options", [])
    if options:
        original_choice = page.evaluate("state.chosen?.option_id || null")
        page.locator(".choose-option").first.click()
        if options[0]["requires_confirmation"]:
            page.locator("#confirmDialog").wait_for(state="visible")
            extra["confirmation_text"] = page.locator("#confirmationChanges").inner_text()
            page.screenshot(path=str(out / (case["id"] + "-confirmation.png")), full_page=True)
            page.locator("#cancelOption").click()
            extra["cancel_preserves_choice"] = page.evaluate("state.chosen?.option_id || null") == original_choice
            page.locator(".choose-option").first.click()
            page.locator("#confirmOption").click()
        page.wait_for_function("state.chosen !== null")
        extra["chosen_option"] = page.evaluate("state.chosen.option_id")
        extra["map_has_route"] = page.evaluate("routeLayer !== null && routeLayer.getLayers().length > 0")
    extra["map_poi_count"] = page.evaluate("typeof mapFeatures !== 'undefined' ? mapFeatures.length : null")
    extra["map_filter_available"] = page.evaluate("typeof exploreFilters === 'function'")
    evidence = capture(page, out, case["id"], request, data, elapsed)
    compact = []
    for o in options:
        compact.append({k: v for k, v in o.items() if k not in ("geometry", "stops")} | {
            "geometry_points": len(o.get("geometry", {}).get("coordinates", [])),
            "stops": [{k: p.get(k) for k in ("poi_id", "name", "location", "latitude", "longitude")} for p in o.get("stops", [])]})
    checks = dict(http_200=True, selected_exactly_two=selected == request["selected_poi_ids"],
                  no_javascript_errors=not errors,
                  routes_have_geometry=all(o["geometry_points"] > 1 for o in compact),
                  missing_must_requires_confirmation=all(not o["missing_must_visit_poi_ids"] or o["requires_confirmation"] for o in compact),
                  extended_time_requires_confirmation=all(o["return_time"] <= request["end_time"] or o["requires_confirmation"] for o in compact),
                  max_three_auto_added=all(len(o["auto_added"]) <= 3 for o in compact))
    checks["danang_geographic_region"] = all((region_for(p["latitude"], p["longitude"]) or {}).get("region") == "danang" for o in compact for p in o["stops"])
    if "duration" in case:
        checks["explicit_durations_preserved"] = all(abs(t["duration_minutes"] - case["duration"]) < 1e-8 for o in compact for t in o["timeline"] if t["role"] == "visit" and t["poi_id"] in selected)
    if case.get("reverse"):
        checks["manual_order_preserved"] = all(o["scheduled_poi_ids"] == [i for i in request["manual_order"] if i in o["scheduled_poi_ids"]] for o in compact)
    if "cancel_preserves_choice" in extra:
        checks["cancel_preserves_choice"] = extra["cancel_preserves_choice"]
    if options:
        checks["selected_option_draws_route"] = extra["map_has_route"]
    context.close()
    return dict(case=case, request=request, options=compact, summary={k: v for k, v in data.items() if k != "options"},
                checks=checks, errors=errors, evidence=evidence, interaction=extra, elapsed_seconds=elapsed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--only", help="Comma-separated scenario IDs, for diagnosis")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    out = ROOT / "artifacts" / "danang-demo" / stamp
    out.mkdir(parents=True, exist_ok=True)
    health = requests.get(base + "/api/health", timeout=60).json()
    report = dict(started_at=datetime.now().astimezone().isoformat(), url=base, health=health,
                  date_of_trip=DATE, execution="Real Chromium clicks, live local API and OSRM; no response mocks", cases=[])
    selected = set(args.only.split(",")) if args.only else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        report["browser_version"] = browser.version
        for case in REC_CASES + TRIP_CASES:
            if selected and case["id"] not in selected:
                continue
            try:
                runner = rec_case if case["id"].startswith("R") else trip_case
                result = runner(browser, base, out, case)
            except Exception as error:
                result = dict(case=case, execution_error=repr(error), checks={"completed": False})
            report["cases"].append(result)
            write_json(out / "results.json", report)
            print(json.dumps({"id": case["id"], "checks": result["checks"],
                              "error": result.get("execution_error"),
                              "top3": [p["name"] for p in result.get("items", [])[:3]],
                              "options": len(result.get("options", []))}, ensure_ascii=False), flush=True)
        browser.close()
    report["finished_at"] = datetime.now().astimezone().isoformat()
    report["health_after"] = requests.get(base + "/api/health", timeout=60).json()
    report["same_dataset_during_run"] = report["health_after"]["dataset_version"] == health["dataset_version"]
    report["evidence_directory"] = str(out.relative_to(ROOT)).replace("\\", "/")
    report["evidence_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.name != "results.json"}
    write_json(out / "results.json", report)
    if not selected:
        write_json(ROOT / "data/reports/demo_danang/results.json", report)
    print(f"Evidence: {out}", flush=True)
    if any(not all(c["checks"].values()) for c in report["cases"]) or not report["same_dataset_during_run"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
