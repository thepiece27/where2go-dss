"""Resumable Google Maps discovery and entity collection for Da Nang / Hoi An."""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shapely.geometry import box
from where2go.config import ROOT
from where2go.v2.catalog import load_catalog
from where2go.v2.discovery import TOPICS, SCOPE_PATH, exclusion_reason, region_for, regions
from where2go.v2.google_collector import collect_page, google_identity, name_similarity, spotlit_entity
from where2go.v2.observations import stable_id
from where2go.v2.taxonomy import canonical_category
from scripts.merge_sources_v2 import Matcher

CAMPAIGN = ROOT / "data/enrichment/danang_hoian"


class CampaignLock:
    """OS releases the byte-range lock even if a Windows worker is terminated."""
    def __enter__(self):
        CAMPAIGN.mkdir(parents=True, exist_ok=True)
        self.handle = (CAMPAIGN / "worker.lock").open("a+b")
        if self.handle.tell() == 0:
            self.handle.write(b"0"); self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            raise RuntimeError("Another campaign worker or publisher is already running") from None
        return self

    def __exit__(self, *args):
        self.handle.close()
PILOT = {
    "coast": ["Bãi biển Mỹ Khê", "Bãi biển Non Nước", "Bãi tắm Phạm Văn Đồng", "Bãi biển An Bàng Hội An"],
    "parks": ["Công viên APEC", "Công viên Biển Đông", "Công viên 29 tháng 3", "Công viên Thanh Niên"],
    "nature": ["Danh thắng Ngũ Hành Sơn", "Đỉnh Bàn Cờ", "Hồ Đồng Xanh Đồng Nghệ", "Khu du lịch Suối Hoa"],
    "entertainment": ["Sun World Bà Nà Hills", "Fantasy Park Bà Nà", "Helio Center", "Công viên nước Mikazuki 365"],
    "culture": ["Bảo tàng Điêu khắc Chăm", "Bảo tàng Đà Nẵng", "Bảo tàng Mỹ thuật Đà Nẵng", "Làng gốm Thanh Hà Hội An"],
}
PILOT_ALIASES = {
    "Bãi biển Mỹ Khê": ["My Khe Beach"], "Bãi biển Non Nước": ["Non Nuoc Beach"],
    "Bãi biển An Bàng Hội An": ["An Bang Beach"], "Công viên APEC": ["APEC Park"],
    "Công viên Biển Đông": ["East Sea Park"], "Công viên Thanh Niên": ["Youth Park", "Thanh Nien Park"],
    "Danh thắng Ngũ Hành Sơn": ["The Marble Mountains", "Marble Mountains"],
    "Sun World Bà Nà Hills": ["Ba Na Hills SunWorld", "Sun World Ba Na Hills"],
    "Fantasy Park Bà Nà": ["Fantasy Park"], "Da Nang Downtown": ["Asia Park", "Sun World Danang Wonders"],
    "Bảo tàng Điêu khắc Chăm": ["Da Nang Museum of Cham Sculpture", "Museum of Cham Sculpture"],
    "Bảo tàng Đà Nẵng": ["Da Nang Museum", "Museum of Da Nang"],
    "Bảo tàng Mỹ thuật Đà Nẵng": ["Da Nang Fine Arts Museum"],
    "Làng gốm Thanh Hà Hội An": ["Thanh Ha Pottery Village"],
    "Công viên nước Mikazuki 365": ["Mikazuki Water Park 365"],
    "Hồ Đồng Xanh Đồng Nghệ": ["Dong Xanh Dong Nghe Lake"],
}
PILOT_POSITIONS = {"Công viên Thanh Niên": (16.027106, 108.216534), "Fantasy Park Bà Nà": (15.9968339, 107.9888036)}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def cells():
    result = []
    for props, polygon in regions():
        west, south, east, north = polygon.bounds
        dy = props["grid_km"] / 111.32
        dx = dy / math.cos(math.radians((south + north) / 2))
        for y in range(math.ceil((north - south) / dy)):
            for x in range(math.ceil((east - west) / dx)):
                bounds = [west + x * dx, south + y * dy, min(east, west + (x + 1) * dx), min(north, south + (y + 1) * dy)]
                clip = polygon.intersection(box(*bounds))
                if clip.is_empty or clip.area == 0:
                    continue
                center = clip.representative_point()
                result.append({"id": f"{props['ward_code']}-{x}-{y}", "bounds": bounds,
                               "latitude": center.y, "longitude": center.x, "size_km": props["grid_km"],
                               "area": props["search_name"], "ward_code": props["ward_code"]})
    priorities = ["20275", "20263", "20285", "20242", "20257", "20410", "20413", "20401", "20434"]
    result.sort(key=lambda c: (priorities.index(c["ward_code"]) if c["ward_code"] in priorities else 99, c["id"]))
    return result


def round_queries(grid, number):
    rows = []
    for cell in grid:
        for topic, phrases in TOPICS.items():
            phrase = phrases[(number - 1) % len(phrases)]
            rows.append({"id": f"r{number}:{cell['id']}:{topic}", "round": number, "topic": topic,
                         "query": f"{phrase} {cell['area']}", "cell": cell, "status": "pending", "attempts": 0})
    return rows


def saturation(history, unresolved):
    if unresolved or len(history) < 3:
        return False
    for result in history[-2:]:
        if not result.get("complete"):
            return False
        for topic in TOPICS:
            values = result["topics"][topic]
            if values["new"] / max(values["before"], 1) >= .01:
                return False
    # Exercise every configured bilingual query variant at least once.
    return len(history) >= max(map(len, TOPICS.values()))


def is_blocked(text):
    return any(s in text.lower() for s in ("unusual traffic", "our systems have detected", "verify you're human", "before you continue to google", "recaptcha", "không phải là rô-bốt"))


async def discover(page, item):
    c = item["cell"]
    zoom = 15 if c["size_km"] <= 2 else 13
    url = f"https://www.google.com/maps/search/{quote(item['query'])}/@{c['latitude']},{c['longitude']},{zoom}z?hl=en"
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(2200)
    if not is_blocked(await page.locator("body").inner_text()):
        try:
            await page.locator('[role="feed"], h1.DUwDvf').first.wait_for(timeout=12000)
        except Exception:
            pass
    found, idle = {}, 0
    for _ in range(80):
        body = await page.locator("body").inner_text()
        if is_blocked(body):
            return "blocked", list(found.values())
        anchors = await page.locator('a[href*="/maps/place/"]').evaluate_all("els=>els.map(e=>({url:e.href,name:e.getAttribute('aria-label')||e.innerText}))")
        previous = len(found)
        for anchor in anchors:
            ident = google_identity(anchor["url"])
            if ident and anchor["name"]:
                found[ident] = {"external_id": ident, **anchor}
        if "you've reached the end" in body.lower() or "bạn đã xem hết" in body.lower():
            return "complete", list(found.values())
        if any(s in body.lower() for s in ("no results found", "can't find", "không tìm thấy kết quả")):
            return "complete", list(found.values())
        feed = page.locator('[role="feed"]')
        if not await feed.count():
            # Search can resolve directly to one entity.
            title = page.locator('h1.DUwDvf')
            ident = google_identity(page.url)
            if not ident and await title.count():
                marker = spotlit_entity(await page.evaluate("()=>window.APP_INITIALIZATION_STATE?.[2]||null"))
                if marker:
                    name = await title.first.inner_text()
                    url = ("https://www.google.com/maps/place/" + quote(name) + "/data=!4m6!3m5!1s" + marker["place_id"]
                           + f"!8m2!3d{marker['latitude']}!4d{marker['longitude']}")
                    return "complete", [{"external_id":marker["place_id"],"url":url,"name":name}]
            if ident and await title.count():
                return "complete", [{"external_id": ident, "url": page.url, "name": await title.first.inner_text()}]
            return "unresolved", list(found.values())
        idle = idle + 1 if len(found) == previous else 0
        if idle >= 4:
            return "limited", list(found.values())
        await feed.first.evaluate("e=>e.scrollTo(0,e.scrollHeight)")
        await page.wait_for_timeout(1400)
    return "limited", list(found.values())


def split_query(item):
    c = item["cell"]
    if c["size_km"] <= .5:
        return []
    w, s, e, n = c["bounds"]
    mx, my = (w + e) / 2, (s + n) / 2
    polygon = next(g for p, g in regions() if p["ward_code"] == c["ward_code"])
    children = []
    for i, bounds in enumerate(((w,s,mx,my),(mx,s,e,my),(w,my,mx,n),(mx,my,e,n))):
        clipped = polygon.intersection(box(*bounds))
        if clipped.is_empty or clipped.area == 0:
            continue
        point = clipped.representative_point()
        cell = {**c, "id": f"{c['id']}.{i}", "bounds": list(bounds), "latitude": point.y,
                "longitude": point.x, "size_km": c["size_km"] / 2}
        children.append({**item, "id": f"{item['id']}.{i}", "cell": cell, "status": "pending", "attempts": 0})
    return children


class Reviewer:
    def __init__(self):
        pois, _ = load_catalog()
        self.by_external = {e["id"]: p for p in pois for e in p.get("external_ids", []) if e["provider"] == "Google Maps"}
        geometries = read(ROOT / "data/cache/poi_geometries_v2.json", {}).get("geometries", {})
        self.matcher = Matcher({p["poi_id"]:p for p in pois if p.get("latitude") is not None and p.get("longitude") is not None}, geometries)
        baseline = read(ROOT / "data/reports/v2/danang_campaign/baseline.json", {})
        self.catalog_ids = set(baseline.get("poi_ids", [p["poi_id"] for p in pois]))
        self.decisions = read(ROOT / "data/curation/danang_campaign_reviews.json", {})

    def review(self, row):
        row.pop("canonical_poi_id", None)
        p = row.get("place") or {}
        ident = google_identity(p.get("google_maps_url"))
        region = region_for(p.get("latitude"), p.get("longitude"))
        category = canonical_category(p.get("category"), p.get("name"))
        if not category:
            category = {"Sculpture":"historic", "Cultural center":"attraction"}.get(p.get("category"))
        reason = exclusion_reason(p.get("name", ""), p.get("category", ""))
        if row.get("status") in {"blocked", "unresolved", "transient_error"}:
            reason = row["status"]
        elif not ident or not region:
            reason = "outside_scope_or_missing_identity"
        elif reason:
            pass
        elif not category:
            reason = "unknown_category"
        elif row.get("expected_place_id") and row["expected_place_id"] != ident:
            reason = "redirected_to_different_entity"
        elif not row.get("expected_place_id") and max(name_similarity(n, p.get("name", "")) for n in [row["seed_name"], *PILOT_ALIASES.get(row["seed_name"], [])]) < .65:
            reason = "pilot_name_mismatch"
        decision = getattr(self, "decisions", {}).get(ident)
        if decision:
            reason = decision["reason"]
            row["source_review"] = decision
        if p.get("name", "").strip().lower() in {"khu vui chơi trẻ em", "tourist attraction", "park", "beach"}:
            reason = "generic_name_needs_review"
        match = self.by_external.get(ident)
        method = "same_google_external_id" if match else "google_entity_panel_and_scope"
        if not reason and not match:
            candidates, method = self.matcher.match([p["name"]], (p["latitude"], p["longitude"]), category)
            possible = self.matcher.possible_duplicates(p["name"], (p["latitude"], p["longitude"]), category)
            if len(candidates) == 1:
                match = candidates[0]
            elif candidates or possible:
                reason = "ambiguous_catalog_match"
        row.update(accepted=not reason, review_reason=reason, expected_category=category,
                   location_expected="Đà Nẵng", campaign="danang_hoian",
                   review_evidence=json.dumps({"method": method, "source_url": p.get("google_maps_url"),
                                              "region": region, "not_field_verified": True}, ensure_ascii=False))
        row["identity"] = {**row.get("identity", {}), "status": "tool_confirmed" if not reason else "needs_review"}
        if match:
            row["canonical_poi_id"] = match["poi_id"]
        row["is_new_entity"] = not match or match["poi_id"] not in getattr(self, "catalog_ids", set(self.matcher.pois))
        if not reason:
            canonical = match or {"poi_id": stable_id("poi-google", ident), "name": p["name"], "category": category,
                                  "latitude": p["latitude"], "longitude": p["longitude"], "data_status": "usable"}
            self.by_external[ident] = canonical
            if canonical["poi_id"] not in self.matcher.pois:
                self.matcher.pois[canonical["poi_id"]] = canonical
                self.matcher.index(canonical)
        return row


def export(rows, state):
    latest = {r["record_id"]:r for r in rows}
    accepted = [r for r in latest.values() if r.get("accepted")]
    save(ROOT / "data/enrichment/accepted-danang-hoian.json", accepted)
    save(CAMPAIGN / "review_queue.json", [r for r in latest.values() if not r.get("accepted")])
    summary = {"updated_at": now(), "status": state.get("status"), "pilot": state.get("pilot"),
               "queries": dict(Counter(q["status"] for q in state.get("queries", []))),
               "discovered": len(state.get("candidates", {})), "collected": len(latest), "accepted": len(accepted),
               "new_entities": len({google_identity(r["place"]["google_maps_url"]) for r in accepted if r.get("is_new_entity")}),
               "categories": dict(Counter(r["expected_category"] for r in accepted)),
               "rejected_or_review": dict(Counter(r.get("review_reason") for r in latest.values() if not r.get("accepted"))),
               "with_image_candidate": sum(bool(r["place"].get("image_url")) for r in accepted),
               "history": state.get("history", []), "saturated": state.get("status") == "saturated"}
    save(ROOT / "data/reports/v2/danang_campaign/collection.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


async def run(args):
    from playwright.async_api import async_playwright
    scope_hash = hashlib.sha256(SCOPE_PATH.read_bytes()).hexdigest()
    revision = hashlib.sha256(Path(__file__).read_bytes() + (ROOT / "where2go/v2/google_collector.py").read_bytes()).hexdigest()[:16]
    state_path, rows_path = CAMPAIGN / "checkpoint.json", CAMPAIGN / "observations.json"
    state = read(state_path, {"scope_sha256": scope_hash, "queries": [], "candidates": {}, "history": [], "round": 0})
    if state.get("collector_revision") != revision:
        for q in state["queries"]:
            if q["status"] in {"transient_error", "unresolved"}:
                q.setdefault("previous_attempts", []).append({"status":q["status"],"attempts":q["attempts"],"revision":state.get("collector_revision")})
                q.update(status="pending",attempts=0)
        state["collector_revision"] = revision
    if state["scope_sha256"] != scope_hash:
        if state["queries"]:
            raise RuntimeError("Boundary changed; use a separate campaign checkpoint")
        state["scope_sha256"] = scope_hash
    if state.get("status") == "blocked" and not args.review_only:
        if not args.resume_after_block:
            raise RuntimeError("Campaign paused on access challenge. Resolve access normally before --resume-after-block.")
        for q in state["queries"]:
            if q["status"] == "blocked":
                q["status"] = "pending"
    rows = read(rows_path, [])
    reviewer = Reviewer()
    # Re-review saved evidence under the current policy, retaining every prior attempt.
    reviewed = [reviewer.review(dict(row)) for row in {r["record_id"]:r for r in rows}.values()]
    rows.extend(reviewed)
    save(rows_path, rows)
    latest = {r["record_id"]:r for r in rows}
    state["status"] = "running"
    export(rows, state)
    if args.review_only or (CAMPAIGN / "PAUSE").exists():
        state["status"] = "paused"
        save(state_path, state)
        export(rows, state)
        return
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        context = await browser.new_context(locale="en-US", viewport={"width":1440,"height":1000})
        if args.diagnose_topic:
            page = await context.new_page()
            item = next(q for q in state["queries"] if q["topic"] == args.diagnose_topic)
            status, found = await discover(page, item)
            save(CAMPAIGN / "diagnostic.json", {"status":status,"url":page.url,"found":found,
                 "body":(await page.locator("body").inner_text())[:12000]})
            await page.screenshot(path=str(CAMPAIGN / "diagnostic.png"))
            state["status"] = "paused"; save(state_path,state)
            await browser.close()
            return
        async def collect(seed):
            previous = latest.get(seed["record_id"])
            if previous and previous.get("status") not in {"transient_error", "unresolved", "blocked"}:
                reviewed = reviewer.review(dict(previous))
                latest[seed["record_id"]] = reviewed
                rows.append(reviewed)
                save(rows_path, rows)
                return reviewed
            start_attempt = previous.get("attempt", 0) + 1 if previous and previous.get("collector_revision") == revision else 1
            if start_attempt > 3:
                return previous
            for attempt in range(start_attempt, 4):
                page = await context.new_page()
                try:
                    result = await collect_page(page, seed)
                except Exception as error:
                    result = {"status":"transient_error", "success":False, "error":str(error)[:500]}
                finally:
                    await page.close()
                row = reviewer.review({**seed, **result, "attempt":attempt, "scraped_at":now(),
                                       "collector":"danang_browser_v1", "collector_revision":revision, "rights_status":"restricted_internal"})
                rows.append(row); latest[row["record_id"]] = row
                save(rows_path, rows)
                print(json.dumps({"name":seed["seed_name"], "status":row["status"], "accepted":row["accepted"], "reason":row["review_reason"]}, ensure_ascii=False), flush=True)
                await asyncio.sleep(3 * attempt)
                if row["status"] == "blocked":
                    state["status"] = "blocked"
                    break
                if (CAMPAIGN / "PAUSE").exists():
                    state["status"] = "paused"
                    break
                if row["status"] not in {"transient_error", "unresolved"}:
                    break
            return row
        async def collect_pending():
            for ident, candidate in state["candidates"].items():
                if candidate.get("excluded"):
                    continue
                if exclusion_reason(candidate["name"]):
                    candidate["excluded"] = "name_policy"
                    continue
                key = stable_id("dn-discovery", ident)
                previous = latest.get(key)
                if previous and previous.get("status") not in {"transient_error", "unresolved", "blocked"}:
                    continue
                await collect({"record_id":key,"seed_name":candidate["name"],"maps_url":candidate["url"],
                    "expected_place_id":ident,"location_expected":"Đà Nẵng","topic":candidate["topics"][0],
                    "query":candidate.get("query", ""),"discovered_by":candidate["query_ids"]})
                save(state_path, state)
                if state["status"] in {"blocked", "paused"}:
                    break
        try:
            if state.get("pilot", {}).get("status") != "PASS":
                pilot_rows = []
                for topic, names in PILOT.items():
                    for name in names:
                        lat, lon = PILOT_POSITIONS.get(name, (None, None))
                        row = await collect({"record_id":stable_id("dn-pilot", name), "seed_name":name,
                            "query":name + ("" if "Hội An" in name else " Đà Nẵng"), "topic":topic,
                            "location_expected":"Đà Nẵng", "pilot":True, "aliases":PILOT_ALIASES.get(name, []), "latitude":lat,"longitude":lon})
                        pilot_rows.append(row)
                        if state["status"] in {"blocked", "paused"}:
                            break
                    if state["status"] in {"blocked", "paused"}:
                        break
                accepted = sum(r["accepted"] for r in pilot_rows)
                if state.get("pilot"):
                    state.setdefault("pilot_history", []).append(state["pilot"])
                state["pilot"] = {"total":len(pilot_rows), "accepted":accepted, "status":"PASS" if len(pilot_rows)==20 and accepted>=19 else "NOT_PASSED"}
                if state["pilot"]["status"] != "PASS":
                    if state["status"] not in {"blocked", "paused"}:
                        state["status"] = "pilot_needs_review"
                    return
            if args.pilot_only:
                state["status"] = "pilot_complete"
                return
            grid = cells()
            await collect_pending()
            if state["status"] in {"blocked", "paused"}:
                return
            count = 0
            while True:
                if (CAMPAIGN / "PAUSE").exists():
                    state["status"] = "paused"
                    break
                if not state["queries"] or all(q["status"] in {"complete", "subdivided"} for q in state["queries"]):
                    if state["queries"]:
                        topics = {}
                        for topic in TOPICS:
                            candidates = [v for v in state["candidates"].values() if topic in v["topics"]]
                            topics[topic] = {"before":sum(v["first_round"] < state["round"] for v in candidates),
                                             "new":sum(v["first_round"] == state["round"] for v in candidates)}
                        state["history"].append({"round":state["round"], "complete":True, "topics":topics})
                        save(CAMPAIGN / f"queries_round_{state['round']}.json", state["queries"])
                        if saturation(state["history"], False):
                            unresolved = [r for r in latest.values() if not r.get("pilot") and r.get("status") in {"unresolved", "transient_error", "blocked"}]
                            state["status"] = "incomplete_entities" if unresolved else "saturated"
                            break
                    state["round"] += 1
                    state["queries"] = round_queries(grid, state["round"])
                pending = next((q for q in state["queries"] if q["status"] in {"pending", "transient_error", "unresolved"} and q["attempts"] < 3), None)
                if pending is None:
                    state["status"] = "incomplete_queries"
                    break
                page = await context.new_page()
                try:
                    status, found = await discover(page, pending)
                except Exception as error:
                    status, found = "transient_error", []
                    pending["error"] = str(error)[:500]
                finally:
                    await page.close()
                pending.update(status=status, attempts=pending["attempts"]+1, observed_at=now(), result_count=len(found))
                for item in found:
                    ident = item["external_id"]
                    candidate = state["candidates"].setdefault(ident, {**item,"topics":[],"query_ids":[],"first_round":state["round"],"query":pending["query"]})
                    if pending["topic"] not in candidate["topics"]:
                        candidate["topics"].append(pending["topic"])
                    if pending["id"] not in candidate["query_ids"]:
                        candidate["query_ids"].append(pending["id"])
                if status == "limited":
                    children = split_query(pending)
                    if children:
                        pending["status"] = "subdivided"
                        state["queries"].extend(children)
                if status == "blocked":
                    state["status"] = "blocked"
                save(state_path, state)
                print(json.dumps({"query":pending["id"],"status":status,"results":len(found)},ensure_ascii=False),flush=True)
                await asyncio.sleep(3 * pending["attempts"])
                if state["status"] in {"blocked", "paused"}:
                    break
                await collect_pending()
                save(state_path,state)
                export(rows,state)
                if state["status"] in {"blocked", "paused"}:
                    break
                count += 1
                if args.max_queries and count >= args.max_queries:
                    state["status"] = "checkpoint_budget"
                    break
        finally:
            if state["status"] == "running":
                state["status"] = "interrupted"
            save(state_path, state)
            export(rows, state)
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-only", action="store_true")
    parser.add_argument("--max-queries", type=int, default=0, help="Optional session budget; zero runs until saturation or external block")
    parser.add_argument("--resume-after-block", action="store_true")
    parser.add_argument("--review-only", action="store_true")
    parser.add_argument("--diagnose-topic", choices=list(TOPICS))
    args = parser.parse_args()
    with CampaignLock():
        asyncio.run(run(args))
