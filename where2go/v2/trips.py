"""Bounded, selection-first trip suggestions. Never invent a road leg or opening time."""
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from time import perf_counter

from where2go.catalog import haversine
from where2go.config import SNAP_LIMIT_METERS
from where2go.routing import RoutingUnavailable
from .dataset import curated_focus_ids
from .durations import choose_duration, fallback_profile
from .hours import intervals_on_date
from .planner import access_point, clock, overlap
from .quality import manual_trip_quality

POLICY_VERSION = "trip-choice-1.0"
TripContextFields = ("start", "date", "location", "selected_poi_ids", "interests", "preferred_categories")
BEAM_WIDTH = 64
MAX_ROUTE_CHECKS = 18
SEARCH_BUDGET_SECONDS = 12
PROFILES = (("convenient", "Thuận đường", "balanced"), ("more", "Ghé nhiều hơn", "quick"),
            ("relaxed", "Thư thả", "relaxed"))
REASONS = {
    "not_found": "Địa điểm không còn trong catalog; hãy tìm và chọn lại.",
    "identity_or_coordinates_unconfirmed": "Danh tính hoặc tọa độ chưa đủ tin cậy.",
    "business_closed": "Nguồn dữ liệu báo địa điểm đã đóng hoặc tạm đóng cửa.",
    "wrong_location": "Địa điểm nằm ngoài địa phương của chuyến đi.",
    "closed_on_date": "Giờ nguồn cho biết địa điểm đóng cửa vào ngày đã chọn.",
    "snap_too_far": "Chưa xác định được điểm tiếp cận đủ gần đường ô tô.",
    "related_access": "Có quan hệ khu lớn–điểm con; chưa có bằng chứng về hai điểm tiếp cận ô tô độc lập.",
    "no_route": "Chưa có đủ đường đi và quay về trong ma trận OSRM.",
    "time_or_search_limit": "Chưa xếp được trong khung giờ, giờ mở cửa và thứ tự này; tìm kiếm có giới hạn.",
}


def position(poi):
    point = access_point(poi)
    if point is not None:
        lat, lon = point.get("latitude"), point.get("longitude")
        if (isinstance(lat, (float, int)) and isinstance(lon, (float, int))
                and math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            return point
    # A trusted entity position is usable but is NOT a verified vehicle entrance.
    return {"latitude": poi["latitude"], "longitude": poi["longitude"], "access_minutes": 0,
            "verified": False, "method": "entity_position_not_verified_entrance"}


def card(poi):
    profile = poi.get("duration_profile") or fallback_profile(poi["category"])
    return {key: poi.get(key) for key in ("poi_id", "name", "location", "category", "latitude", "longitude", "image")} | {
        "duration_profile": profile, "manual_trip_quality": manual_trip_quality(poi),
        "warnings": (["Chưa có giờ mở cửa; cần kiểm tra trước khi đi."] if poi.get("hours_weekly") is None else []),
    }


def recommendations(pois, manifest, request, router, context):
    """Editorial highlights stay available when road-based ranking is unavailable."""
    selected = set(request.selected_poi_ids)
    by_id = {p["poi_id"]: p for p in pois}
    featured = [by_id[i] for i in curated_focus_ids().get(request.location, [])
                if i in by_id and i not in selected and manual_trip_quality(by_id[i], request.location)["eligible"]
                and intervals_on_date(by_id[i].get("hours_weekly"), by_id[i].get("hours_exceptions"), request.date) != []]
    from .recommendations import RecommendationRequest, recommend_pois
    # Preserve the old editorial/contextual wire shape; the homepage uses items.
    payload = {k: getattr(request, k) for k in TripContextFields}
    payload["top_k"] = 20
    data = recommend_pois(pois, manifest, RecommendationRequest.model_validate(payload), router, context)
    featured_ids = {p["poi_id"] for p in featured}
    contextual = [p for p in data["items"] if p["poi_id"] not in featured_ids][:8]
    routing_status = "ready" if data["travel_metric"] == "road_time" else "unavailable"
    return {"dataset_version": manifest["version"], "policy_version": POLICY_VERSION,
            "routing_status": routing_status, "ranking": data["ranking"] if routing_status == "ready" else None,
            "featured": [card(p) | {"reasons": [f"Điểm nổi bật tại {request.location}"]} for p in featured[:12]],
            "contextual": contextual}


@dataclass(frozen=True)
class SearchState:
    order: tuple
    now: float
    drive: float = 0
    wait: float = 0


class Scheduler:
    def __init__(self, request, items, matrix, pace):
        self.request, self.items, self.matrix = request, items, matrix
        self.durations = {i: choose_duration(p.get("duration_profile") or fallback_profile(p["category"]),
                                            pace, request.duration_overrides.get(i)) for i, p in items.items()}
        self.windows = {i: intervals_on_date(p.get("hours_weekly"), p.get("hours_exceptions"), request.date)
                        for i, p in items.items()}

    def compatible(self, order, ident):
        p = self.items[ident]
        for other in order:
            q = self.items[other]
            if overlap(p, q):
                a, b = p["access"], q["access"]
                if not (a.get("verified") and b.get("verified") and
                        haversine((a["latitude"], a["longitude"]), (b["latitude"], b["longitude"])) >= .1):
                    return False
        return True

    def advance(self, state, ident, leg=None):
        p = self.items[ident]
        previous = self.items[state.order[-1]]["index"] if state.order else 0
        drive = self.matrix["durations"][previous][p["index"]] if leg is None else leg["duration"]
        if drive is None or not self.compatible(state.order, ident):
            return None
        access = max(0, p["access"].get("access_minutes") or 0) * 60
        arrival, duration = state.now + drive, self.durations[ident][0] * 60
        earliest = arrival + access
        windows = self.windows[ident]
        possible = [max(earliest, a * 60) for a, b in windows or [] if max(earliest, a * 60) + duration <= b * 60]
        begin = earliest if windows is None else min(possible) if possible else None
        if begin is None:
            return None
        # Access time is charged in both directions; zero means unknown rather than verified zero.
        finish = begin + duration + access
        return SearchState(state.order + (ident,), finish, state.drive + drive, state.wait + begin - earliest), {
            "arrival": arrival, "begin": begin, "finish_visit": begin + duration, "finish": finish,
            "access": access, "drive": drive, "wait": begin - earliest,
        }

    def search(self, start, end):
        beam, candidates = [SearchState((), start)], []
        must = set(self.request.must_visit_poi_ids)
        manual = self.request.manual_order
        positions = {ident: idx for idx, ident in enumerate(manual or [])}
        for _ in range(len(self.items)):
            expanded = []
            for current in beam:
                for ident in self.items:
                    if ident in current.order or (manual and current.order and positions[ident] <= positions[current.order[-1]]):
                        continue
                    result = self.advance(current, ident)
                    if result is None or result[0].now > end:
                        continue
                    state = result[0]
                    expanded.append(state)
                    home = self.matrix["durations"][self.items[ident]["index"]][0]
                    if home is not None and state.now + home <= end:
                        candidates.append((state, home))
            if not expanded:
                break
            expanded.sort(key=lambda s: (-len(must.intersection(s.order)), -len(s.order), s.now, s.drive, s.order))
            # Keep separate visited sets / last stops and earliest states; never force ranked order.
            unique = {}
            for s in expanded:
                key = (frozenset(s.order), s.order[-1])
                unique.setdefault(key, s)
            beam = list(unique.values())[:BEAM_WIDTH]
        candidates.sort(key=lambda pair: (-len(must.intersection(pair[0].order)), -len(pair[0].order),
                                          pair[0].drive + pair[1] + pair[0].wait * .5, pair[0].now + pair[1], pair[0].order))
        return candidates[:8]

    def simulate(self, order, route, start, end, breaks=None):
        """Simulate one concrete Route; no shared-matrix mutation between options."""
        current, timeline = SearchState((), start), []
        def block(role, name, a, b, **extra):
            timeline.append({"role": role, "name": name, "start_time": clock(a), "end_time": clock(b),
                             "start_seconds": a, "end_seconds": b, "duration_minutes": (b - a) / 60, **extra})
        for idx in range(len(order) + 1):
            for spec in (breaks or {}).get(idx, []):
                begin = max(current.now, spec["start"])
                if begin + spec["duration"] > spec["end"]:
                    return None
                if begin > current.now:
                    block("wait", "Chờ giờ nghỉ", current.now, begin)
                block(spec["role"], spec["name"], begin, begin + spec["duration"], poi_id=None)
                current = SearchState(current.order, begin + spec["duration"], current.drive, current.wait + begin - current.now)
            if idx == len(order):
                home = route["legs"][idx]
                block("return", "Quay về điểm xuất phát", current.now, current.now + home["duration"],
                      distance_meters=home["distance"])
                finish = current.now + home["duration"]
                if finish > end:
                    return None
                return {"timeline": timeline, "return_seconds": finish, "return_time": clock(finish),
                        "drive_seconds": current.drive + home["duration"], "wait_seconds": current.wait,
                        "total_minutes": (finish - start) / 60}
            ident, leg = order[idx], route["legs"][idx]
            result = self.advance(current, ident, leg)
            if result is None:
                return None
            updated, timing = result
            p = self.items[ident]
            block("travel", "Di chuyển đến " + p["name"], current.now, timing["arrival"],
                  to_poi_id=ident, distance_meters=leg["distance"])
            if timing["access"]:
                block("access", "Tiếp cận địa điểm", timing["arrival"], timing["arrival"] + timing["access"], poi_id=ident)
            if timing["wait"]:
                block("wait", "Chờ mở cửa", timing["arrival"] + timing["access"], timing["begin"], poi_id=ident)
            warnings = []
            if self.windows[ident] is None:
                warnings.append("Cần kiểm tra giờ trước khi đi.")
            if not p["access"].get("verified"):
                warnings.append("Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung.")
            if self.durations[ident][1] != "user_override":
                warnings.append("Thời lượng tham khảo, có thể điều chỉnh.")
            block("visit", p["name"], timing["begin"], timing["finish_visit"], poi_id=ident,
                  category=p["category"], hours_status="unknown" if self.windows[ident] is None else "known",
                  duration_source=self.durations[ident][1], warnings=warnings)
            if timing["access"]:
                block("access", "Trở lại điểm đón ô tô", timing["finish_visit"], timing["finish"], poi_id=ident)
            current = updated

    def with_breaks(self, order, route, start, end):
        result = self.simulate(order, route, start, end)
        if result is None:
            return None
        specs, notes, breaks = [], [], {}
        if self.request.include_meals:
            for name, a, b in (("Bữa trưa tự túc tại điểm dừng", 690, 840), ("Bữa tối tự túc tại điểm dừng", 1080, 1200)):
                if min(result["return_seconds"], b * 60) - max(start, a * 60) >= 1800:
                    covered = any(t["role"] == "visit" and t.get("category") in ("restaurant", "food_street")
                                  and min(t["end_seconds"], b * 60) - max(t["start_seconds"], a * 60) >= 1200
                                  for t in result["timeline"])
                    if not covered:
                        specs.append({"name": name, "role": "meal", "start": a * 60, "end": b * 60, "duration": 2700})
        if self.request.include_coffee_break and result["return_seconds"] - start >= 10800:
            if not any(self.items[i]["category"] == "cafe" for i in order):
                specs.append({"name": "Nghỉ tự túc tại điểm dừng", "role": "break", "start": start + 3600,
                              "end": end, "duration": 1200})
        for spec in specs:
            choices = []
            for idx in range(1, len(order) + 1):
                trial = {i: list(rows) for i, rows in breaks.items()}
                trial.setdefault(idx, []).append(spec)
                scheduled = self.simulate(order, route, start, end, trial)
                if scheduled:
                    choices.append((scheduled["return_seconds"], scheduled["wait_seconds"], idx, trial, scheduled))
            if choices:
                _, _, _, breaks, result = min(choices, key=lambda x: x[:3])
                notes.append(spec["name"] + ": chưa chọn nhà hàng; cần kiểm tra dịch vụ tại chỗ.")
            else:
                notes.append("Chưa xếp khối " + spec["name"].lower() + "; bạn có thể bớt điểm hoặc kéo dài chuyến đi.")
        return result | {"break_notes": notes}


def suggest_trips(pois, manifest, request, router, context):
    started = perf_counter()
    by_id = {p["poi_id"]: p for p in pois}
    selected = list(request.selected_poi_ids)
    base = {"status": "adjustment_needed", "message": "Chưa xếp được với lựa chọn này.",
            "dataset_version": manifest["version"], "routing_version": router.version,
            "policy_version": POLICY_VERSION, "options": [], "actions": [], "issues": [],
            "selected_poi_ids": selected.copy(), "auto_added_poi_ids": [],
            "search": {"beam_width": BEAM_WIDTH, "globally_optimal": False, "max_route_checks": MAX_ROUTE_CHECKS, "budget_reached": False}}
    def action(code, label, **extra):
        if not any(a["code"] == code for a in base["actions"]):
            base["actions"].append({"code": code, "label": label, **extra})
    def finish():
        base["elapsed_ms"] = round((perf_counter() - started) * 1000, 1)
        return base
    if not selected:
        base.update(status="choose_places", message="Chọn những nơi bạn muốn ghé để bắt đầu.")
        action("choose_places", "Xem các địa điểm nổi bật")
        return finish()
    if request.auto_add and len(selected) < 12:
        reco = recommendations(pois, manifest, request, router, context)
        extra = [p["poi_id"] for p in reco["contextual"][:min(3, 12 - len(selected))]]
        selected.extend(extra)
        base["auto_added_poi_ids"] = extra
    rejected, items = {}, {}
    for ident in selected:
        p = by_id.get(ident)
        reasons = manual_trip_quality(p, request.location)["reasons"] if p else ["not_found"]
        if not reasons and intervals_on_date(p.get("hours_weekly"), p.get("hours_exceptions"), request.date) == []:
            reasons = ["closed_on_date"]
        if reasons:
            rejected[ident] = reasons[0]
        else:
            items[ident] = dict(p, access=position(p), index=len(items) + 1)
    base["issues"] = [{"poi_id": i, "name": by_id.get(i, {}).get("name", i), "code": r, "message": REASONS[r]}
                      for i, r in rejected.items()]
    if rejected:
        action("replace_places", "Thay hoặc bỏ các điểm chưa thể xếp", poi_ids=list(rejected))
    if not items:
        action("change_date", "Chọn ngày khác hoặc tìm địa điểm thay thế")
        return finish()
    expected_hash = manifest.get("osm", {}).get("sha256")
    if not expected_hash or router.manifest.get("pbf_sha256") != expected_hash:
        base.update(status="routing_unavailable", message="Dữ liệu đường đi chưa khớp với dữ liệu địa điểm.")
        action("retry_routing", "Thử lại khi dữ liệu đường đi sẵn sàng")
        return finish()
    coords = [(request.start.latitude, request.start.longitude)] + [(p["access"]["latitude"], p["access"]["longitude"]) for p in items.values()]
    try:
        matrix = router.table(coords)
        if matrix is None:
            raise RoutingUnavailable("Chưa có ma trận đường đi cho các điểm đã chọn.")
    except RoutingUnavailable as error:
        base.update(status="routing_unavailable", message=str(error))
        action("retry_routing", "Thử lại đường đi")
        action("change_start", "Chọn lại điểm xuất phát gần đường ô tô")
        return finish()
    if matrix["sources"][0]["distance"] > SNAP_LIMIT_METERS:
        base["message"] = "Điểm xuất phát đang quá xa đường ô tô."
        action("change_start", "Chọn lại điểm xuất phát trên bản đồ")
        return finish()
    for ident, p in list(items.items()):
        if matrix["sources"][p["index"]]["distance"] > SNAP_LIMIT_METERS:
            rejected[ident] = "snap_too_far"
            del items[ident]
    vertices = {0, *(p["index"] for p in items.values())}
    def reachable(reverse=False):
        found, pending = {0}, [0]
        while pending:
            a = pending.pop()
            for b in vertices - found:
                edge = matrix["durations"][b][a] if reverse else matrix["durations"][a][b]
                if edge is not None:
                    found.add(b); pending.append(b)
        return found
    round_trip = reachable() & reachable(True)
    for ident, p in list(items.items()):
        if p["index"] not in round_trip:
            rejected[ident] = "no_route"
            del items[ident]
    base["issues"] = [{"poi_id": i, "name": by_id.get(i, {}).get("name", i), "code": r, "message": REASONS[r]}
                      for i, r in rejected.items()]
    if not items:
        base.update(status="routing_unavailable", message="Chưa có đường ô tô phù hợp để đi và quay về từ các điểm đã chọn.")
        action("change_start", "Chọn lại điểm xuất phát hoặc điểm tiếp cận")
        action("replace_places", "Chọn địa điểm thay thế", poi_ids=list(rejected))
        action("retry_routing", "Thử lại đường đi")
        return finish()
    start = (request.start_time.hour * 60 + request.start_time.minute) * 60
    end = (request.end_time.hour * 60 + request.end_time.minute) * 60
    route_cache, verified, route_errors = {}, [], []
    def verify(profile, window_start, window_end):
        if perf_counter() - started > SEARCH_BUDGET_SECONDS:
            base["search"]["budget_reached"] = True
            return
        key, label, pace = profile
        scheduler = Scheduler(request, items, matrix, pace)
        candidates = scheduler.search(window_start, window_end)
        checked = set()
        # Try alternate orders/subsets when Route disagrees with Table.
        queue = [c[0].order for c in candidates[:4]]
        attempts = 0
        while queue and attempts < 8:
            order = queue.pop(0)
            if not order or order in checked:
                continue
            checked.add(order)
            attempts += 1
            if order not in route_cache:
                if len(route_cache) >= MAX_ROUTE_CHECKS or perf_counter() - started > SEARCH_BUDGET_SECONDS:
                    base["search"]["budget_reached"] = True
                    break
                try:
                    route_cache[order] = router.route([coords[0]] + [coords[items[i]["index"]] for i in order] + [coords[0]], use_cache=False)
                except RoutingUnavailable as error:
                    route_errors.append(str(error)); route_cache[order] = None
            route = route_cache[order]
            if route is None:
                continue
            result = scheduler.with_breaks(order, route, window_start, window_end)
            if result is None:
                # Preserve the manual order in every repair; no fabricated or shortened user duration.
                removable = sorted(range(len(order)), key=lambda j: (order[j] in request.must_visit_poi_ids, -j))
                queue.extend(order[:j] + order[j + 1:] for j in removable[:3])
                continue
            missing = [i for i in request.selected_poi_ids if i not in order]
            missing_must = [i for i in request.must_visit_poi_ids if i not in order]
            changed_time = window_start != start or result["return_seconds"] > end
            changes = []
            if changed_time:
                changes.append({"code": "time_changed", "message": f"Đề xuất đi lúc {clock(window_start)}, về lúc {result['return_time']} (yêu cầu {clock(start)}–{clock(end)})."})
            if missing_must:
                changes.append({"code": "missing_must_visit", "poi_ids": missing_must,
                                "message": "Chưa ghé được điểm bắt buộc: " + ", ".join(by_id.get(i, {}).get("name", i) for i in missing_must)})
            unscheduled = []
            for i in missing:
                reason = rejected.get(i, "time_or_search_limit")
                if i in items and not scheduler.compatible(order, i):
                    reason = "related_access"
                elif i in items and (all(matrix["durations"][j][items[i]["index"]] is None for j in range(len(coords)) if j != items[i]["index"])
                                     or all(matrix["durations"][items[i]["index"]][j] is None for j in range(len(coords)) if j != items[i]["index"])):
                    reason = "no_route"
                unscheduled.append({"poi_id": i, "name": by_id.get(i, {}).get("name", i), "code": reason, "message": REASONS[reason]})
            effective_end = max(end, math.ceil(result["return_seconds"] / 60) * 60)
            reserve = max(0, effective_end - result["return_seconds"]) / 60
            recommended = min(45, max(15, result["drive_seconds"] / 600))
            warnings = ["Thời gian lái xe chưa bao gồm giao thông trực tiếp.", *result.pop("break_notes")]
            if reserve < recommended:
                warnings.append("Lịch khá sát: thời gian đệm thấp hơn mức khuyến nghị.")
            visits = [t for t in result["timeline"] if t["role"] == "visit"]
            option = {**result, "profile": key, "label": label, "start_time": clock(window_start),
                      "date": request.date.isoformat(), "location": request.location, "start": request.start.model_dump(),
                      "window": {"start_time": clock(window_start), "end_time": clock(effective_end)},
                      "scheduled_poi_ids": list(order), "unscheduled": unscheduled,
                      "auto_added": [{"poi_id": i, "name": items[i]["name"]} for i in order if i not in request.selected_poi_ids],
                      "missing_must_visit_poi_ids": missing_must, "all_must_visits": not missing_must,
                      "coverage": {"selected": len(request.selected_poi_ids) - len(missing), "selected_total": len(request.selected_poi_ids),
                                   "must": len(request.must_visit_poi_ids) - len(missing_must), "must_total": len(request.must_visit_poi_ids)},
                      "changes": changes, "requires_confirmation": bool(changes), "warnings": warnings,
                      "reserve_minutes": round(reserve, 1), "recommended_reserve_minutes": round(recommended, 1),
                      "geometry": route["geometry"], "legs": route["legs"],
                      "stops": [{"poi_id": i, "name": items[i]["name"], "latitude": items[i]["access"]["latitude"],
                                 "longitude": items[i]["access"]["longitude"]} for i in order],
                      "status": "provisional" if any(t["hours_status"] == "unknown" or not items[t["poi_id"]]["access"].get("verified")
                                                       for t in visits) else "ready"}
            signature = json.dumps([manifest["version"], router.version, request.date.isoformat(), coords[0], list(order),
                                    [(t["start_seconds"], t["end_seconds"]) for t in visits], window_start,
                                    result["return_seconds"], request.selected_poi_ids, request.must_visit_poi_ids,
                                    route["geometry"], route["legs"], missing_must, changes], sort_keys=True)
            option["option_id"] = sha256(signature.encode()).hexdigest()[:16]
            verified.append(option)
            break
    for profile in PROFILES:
        verify(profile, start, end)
    full = any(o["coverage"]["selected"] == len(request.selected_poi_ids) for o in verified)
    if not full or request.try_other_windows:
        windows = [(8 * 3600, 12 * 3600), (13 * 3600, 18 * 3600), (8 * 3600, 18 * 3600),
                   (start, min(86340, end + 4 * 3600)), (max(0, start - 3 * 3600), min(86340, end + 4 * 3600)), (6 * 3600, 86340)]
        seen = {(start, end)}
        for a, b in windows:
            if (a, b) in seen:
                continue
            seen.add((a, b))
            verify(PROFILES[0], a, b)
            if not full:
                verify(PROFILES[1], a, b)
    # Reserve a slot for a meaningful time-changing option when it preserves more chosen places.
    originals = [o for o in verified if not any(c["code"] == "time_changed" for c in o["changes"])]
    alternatives = [o for o in verified if any(c["code"] == "time_changed" for c in o["changes"])]
    def quality(o):
        return (-o["coverage"]["must"], -o["coverage"]["selected"],
                abs(int(o["start_time"][:2]) * 3600 + int(o["start_time"][3:]) * 60 - start) + max(0, o["return_seconds"] - end),
                o["drive_seconds"], next(i for i, p in enumerate(PROFILES) if p[0] == o["profile"]), o["option_id"])
    originals.sort(key=quality); alternatives.sort(key=quality)
    ordered = []
    if originals:
        ordered.append(originals[0])
    if alternatives and (request.try_other_windows or not originals or
                         alternatives[0]["coverage"]["selected"] > originals[0]["coverage"]["selected"] or
                         alternatives[0]["coverage"]["must"] > originals[0]["coverage"]["must"]):
        ordered.append(alternatives[0])
    # Prefer distinct duration profiles after reserving the primary and adjustment slots.
    ordered.extend(originals)
    if not originals:
        ordered.extend(alternatives)
    seen = set()
    for option in ordered:
        if option["option_id"] not in seen:
            base["options"].append(option); seen.add(option["option_id"])
        if len(base["options"]) == 3:
            break
    if base["options"]:
        base.update(status="suggestions", message="So sánh các lịch và chọn phương án phù hợp với bạn.")
    elif route_errors:
        base.update(status="routing_unavailable", message="Chưa xác nhận được tuyến đường cho lựa chọn này.")
        action("retry_routing", "Thử lại đường đi")
    else:
        base["issues"].extend({"poi_id": i, "name": p["name"], "code": rejected.get(i, "time_or_search_limit"),
                               "message": REASONS[rejected.get(i, "time_or_search_limit")]} for i, p in by_id.items() if i in selected and i not in rejected)
    action("try_other_windows", "Thử khung giờ khác trong ngày")
    action("edit_selection", "Sửa danh sách và thời lượng")
    if not any(o["coverage"]["selected"] == len(request.selected_poi_ids) for o in base["options"]):
        action("split_trip", "Giữ các điểm chưa xếp để đi chuyến khác")
        action("change_date", "Thử ngày khác nếu giờ mở cửa xung đột")
    if not base["options"]:
        action("change_start", "Kiểm tra điểm xuất phát và đường tiếp cận")
    return finish()
