"""Greedy multi-start itinerary planner with explicit feasibility checks."""
from dataclasses import dataclass
import math

from where2go.catalog import haversine
from where2go.config import SNAP_LIMIT_METERS
from where2go.routing import RoutingUnavailable
from . import MODEL_VERSION
from .durations import choose_duration
from .hours import intervals_on_date
from .ranking import confidence, rank, valid_rating
from .taxonomy import FOOD_CATEGORIES


PACE_LIMITS = {"quick": 5, "balanced": 4, "relaxed": 3}
OBJECTIVE_VERSION = "planner-objective-v2.0"
SEARCH_SEED_LIMIT = 3
OBJECTIVE = {
    "diversity_bonus": 0.12,
    "preferred_theme_bonus": 0.15,
    "drive_hour_penalty": 0.05,
    "waiting_hour_penalty": 0.03,
    "uncertainty_penalty": 0.05,
}
MEAL_SPECS = (
    {"role": "meal", "name": "Bữa trưa", "start": 11 * 60 + 30, "end": 14 * 60, "duration": 60, "categories": {"restaurant", "food_street"}},
    {"role": "meal", "name": "Bữa tối", "start": 18 * 60, "end": 20 * 60, "duration": 60, "categories": {"restaurant", "food_street"}},
)


def clock(seconds):
    minute = math.ceil(seconds / 60)
    return f"{minute // 60:02d}:{minute % 60:02d}"


def start_seconds(request):
    return (request.start_time.hour * 60 + request.start_time.minute) * 60


def end_seconds(request):
    return (request.end_time.hour * 60 + request.end_time.minute) * 60


def access_point(poi):
    points = sorted(poi.get("access_points", []), key=lambda point: (not point.get("verified"), point.get("access_id", "")))
    return points[0] if points else None


def active_time_blocks(request):
    start, end = start_seconds(request) // 60, end_seconds(request) // 60
    result = []
    if request.include_meals:
        for spec in MEAL_SPECS:
            if min(end, spec["end"]) - max(start, spec["start"]) >= spec["duration"]:
                result.append(dict(spec))
    if request.include_coffee_break and end - start >= 180:
        midpoint = (start + end) // 2
        result.append({"role": "break", "name": "Nghỉ/cà phê", "start": max(start, midpoint - 60),
                       "end": min(end, midpoint + 90), "duration": 30, "categories": {"cafe"}})
    return sorted(result, key=lambda spec: (spec["start"], spec["role"]))


def filter_candidates(pois, request):
    accepted, food, excluded = [], [], []
    by_id = {poi["poi_id"]: poi for poi in pois}
    for poi in pois:
        reason = None
        if poi.get("data_status") != "usable" or not poi.get("entity_confirmed"):
            reason = "entity_unconfirmed"
        elif request.location and poi.get("location") != request.location:
            reason = "wrong_location"
        elif poi.get("business_status") in ("temporarily_closed", "permanently_closed"):
            reason = "business_closed"
        elif not poi.get("serving_quality", {}).get("eligible", True):
            reason = poi["serving_quality"]["reasons"][0]
        elif poi.get("category") in request.excluded_categories:
            reason = "excluded_category"
        elif not poi.get("access_points"):
            reason = "missing_access_point"
        else:
            point = access_point(poi)
            distance = haversine((request.start.latitude, request.start.longitude), (point["latitude"], point["longitude"]))
            if distance > request.radius_km:
                reason = "outside_radius"
            else:
                item = dict(poi, straight_distance_km=distance, chosen_access=point)
                if poi.get("category") in FOOD_CATEGORIES:
                    food.append(item)
                elif request.category_mode == "only" and poi.get("category") not in request.preferred_categories:
                    reason = "thematic_filter"
                else:
                    accepted.append(item)
        if reason and (poi["poi_id"] in request.required_poi_ids or poi.get("location") == request.location):
            excluded.append({"poi_id": poi["poi_id"], "reason": reason})
    missing_required = [ident for ident in request.required_poi_ids if ident not in by_id]
    excluded.extend({"poi_id": ident, "reason": "entity_unconfirmed"} for ident in missing_required)
    return accepted, food, excluded


def shortlist(attractions, food, request, attraction_limit=40, food_limit=20):
    def evidence(poi):
        return (3 * bool(valid_rating(poi)) + 2 * (poi.get("hours_weekly") is not None)
                + bool(poi.get("website")) + bool(poi["chosen_access"].get("verified")))
    required = set(request.required_poi_ids)
    attraction_sorted = sorted(attractions, key=lambda poi: (
        poi["poi_id"] not in required,
        poi["category"] not in request.preferred_categories,
        -evidence(poi), poi["straight_distance_km"], poi["poi_id"],
    ))
    near = sorted(attractions, key=lambda poi: (poi["straight_distance_km"], poi["poi_id"]))
    chosen = {}
    for relevant, nearby in zip(attraction_sorted, near):
        for poi in (relevant, nearby):
            if len(chosen) < attraction_limit or poi["poi_id"] in required:
                chosen.setdefault(poi["poi_id"], poi)
    food_sorted = sorted(food, key=lambda poi: (-evidence(poi), poi["straight_distance_km"], poi["poi_id"]))
    return list(chosen.values()), food_sorted[:food_limit]


def opening_start(poi, day, earliest, duration):
    windows = intervals_on_date(poi.get("hours_weekly"), poi.get("hours_exceptions"), day)
    if windows is None:
        return earliest, "unknown"
    feasible = [max(earliest, start * 60) for start, end in windows if max(earliest, start * 60) + duration <= end * 60]
    return (min(feasible), "known") if feasible else (None, "closed")


@dataclass
class SimulationEnvironment:
    request: object
    by_id: dict
    matrix: dict
    food: list
    fixed_food: dict | None = None


def choose_break(spec, previous, following, now, environment):
    request, matrix = environment.request, environment.matrix
    candidates = []
    fixed_id = (environment.fixed_food or {}).get(spec["name"])
    for poi in environment.food:
        if fixed_id and poi["poi_id"] != fixed_id:
            continue
        if poi["category"] not in spec["categories"] or poi.get("hours_weekly") is None:
            continue
        index = poi["matrix_index"]
        outward = matrix["durations"][previous][index]
        onward = matrix["durations"][index][following]
        if outward is None or onward is None:
            continue
        arrive = now + outward
        begin, hours_status = opening_start(poi, request.date, max(arrive, spec["start"] * 60), spec["duration"] * 60)
        if begin is None or begin + spec["duration"] * 60 > spec["end"] * 60:
            continue
        candidates.append((outward + onward, begin, poi["poi_id"], poi, outward, onward, hours_status))
    if candidates:
        _, begin, _, poi, outward, _, hours_status = min(candidates, key=lambda row: row[:3])
        arrive = now + outward
        finish = begin + spec["duration"] * 60
        return {
            "block": {"role": spec["role"], "name": poi["name"], "poi_id": poi["poi_id"],
                      "arrival_time": clock(arrive), "start_time": clock(begin), "end_time": clock(finish),
                      "duration_minutes": spec["duration"], "duration_source": "meal_design_default",
                      "wait_minutes": (begin - arrive) / 60, "hours_status": hours_status,
                      "access_status": "verified" if poi["chosen_access"].get("verified") else "estimated",
                      "category": poi["category"]},
            "leg": {"from_index": previous, "to_index": poi["matrix_index"], "duration_seconds": outward,
                    "distance_meters": matrix["distances"][previous][poi["matrix_index"]]},
            "now": finish, "previous": poi["matrix_index"], "specific": True,
        }
    begin = max(now, spec["start"] * 60)
    finish = begin + spec["duration"] * 60
    if finish > spec["end"] * 60:
        return None
    return {
        "block": {"role": spec["role"], "name": spec["name"] + " tự túc", "poi_id": None,
                  "arrival_time": clock(begin), "start_time": clock(begin), "end_time": clock(finish),
                  "duration_minutes": spec["duration"], "duration_source": "meal_design_default",
                  "wait_minutes": 0, "hours_status": "not_applicable", "access_status": "not_applicable",
                  "category": None},
        "leg": None, "now": finish, "previous": previous, "specific": False,
    }


def simulate(order, environment):
    request, matrix, by_id = environment.request, environment.matrix, environment.by_id
    now, end = start_seconds(request), end_seconds(request)
    previous, blocks, legs = 0, [], []
    pending = active_time_blocks(request)
    fixed_food, provisional = {}, False
    total_drive = total_wait = 0.0

    def add_break(spec, following):
        nonlocal now, previous, total_drive, provisional
        selected = choose_break(spec, previous, following, now, environment)
        if selected is None:
            return False
        blocks.append(selected["block"])
        if selected["leg"]:
            legs.append(selected["leg"])
            total_drive += selected["leg"]["duration_seconds"]
        if selected["block"]["poi_id"]:
            fixed_food[spec["name"]] = selected["block"]["poi_id"]
            if selected["block"]["access_status"] != "verified":
                provisional = True
        else:
            provisional = True
        now, previous = selected["now"], selected["previous"]
        return True

    for ident in order:
        poi = by_id[ident]
        index = poi["matrix_index"]
        travel = matrix["durations"][previous][index]
        if travel is None:
            return None
        duration, duration_source = choose_duration(poi["duration_profile"], request.pace,
                                                    request.duration_overrides.get(ident))
        access_seconds = poi["chosen_access"].get("access_minutes", 0) * 60
        direct_earliest = now + travel + access_seconds
        direct_begin, _ = opening_start(poi, request.date, direct_earliest, duration * 60)
        direct_finish = direct_begin + duration * 60 if direct_begin is not None else math.inf
        while pending and (now >= pending[0]["start"] * 60 or direct_finish > pending[0]["end"] * 60):
            if not add_break(pending.pop(0), index):
                return None
            travel = matrix["durations"][previous][index]
            if travel is None:
                return None
        arrive = now + travel
        earliest = arrive + access_seconds
        begin, hours_status = opening_start(poi, request.date, earliest, duration * 60)
        if begin is None:
            return None
        finish = begin + duration * 60
        if finish > end:
            return None
        leg = {"from_index": previous, "to_index": index, "duration_seconds": travel,
               "distance_meters": matrix["distances"][previous][index]}
        legs.append(leg); total_drive += travel; total_wait += begin - earliest
        blocks.append({
            "role": "attraction", "name": poi["name"], "poi_id": ident, "category": poi["category"],
            "arrival_time": clock(arrive), "start_time": clock(begin), "end_time": clock(finish),
            "duration_minutes": duration, "duration_source": duration_source,
            "access_minutes": poi["chosen_access"].get("access_minutes", 0),
            "access_status": "verified" if poi["chosen_access"].get("verified") else "estimated",
            "wait_minutes": (begin - earliest) / 60, "hours_status": hours_status,
            "score": poi["score"], "criteria": poi["criteria"], "explanation": poi["explanation"],
        })
        if hours_status == "unknown" or duration_source == "category_default" or not poi["chosen_access"].get("verified"):
            provisional = True
        previous, now = index, finish

    while pending:
        if not add_break(pending.pop(0), 0):
            return None
    home = matrix["durations"][previous][0]
    if home is None:
        return None
    legs.append({"from_index": previous, "to_index": 0, "duration_seconds": home,
                 "distance_meters": matrix["distances"][previous][0]})
    total_drive += home
    return_seconds = now + home
    reserve = min(45 * 60, max(15 * 60, total_drive * 0.10))
    if return_seconds + reserve > end:
        return None
    return {
        "blocks": blocks, "legs": legs, "return_time": clock(return_seconds),
        "return_seconds": return_seconds, "drive_seconds": total_drive,
        "wait_seconds": total_wait, "reserve_minutes": math.ceil(reserve / 60),
        "status": "provisional" if provisional else "ready", "fixed_food": fixed_food,
    }


def overlap(a, b):
    return (a.get("parent_poi_id") and a["parent_poi_id"] == b["poi_id"]) or (
        b.get("parent_poi_id") and b["parent_poi_id"] == a["poi_id"]) or (
        a.get("parent_poi_id") and a.get("parent_poi_id") == b.get("parent_poi_id"))


def valid_addition(order, candidate, by_id, request):
    if any(overlap(candidate, by_id[ident]) for ident in order):
        return False, "duplicate_or_child_overlap"
    if request.pace == "balanced" and request.category_mode != "only":
        if sum(by_id[ident]["category"] == candidate["category"] for ident in order) >= 2:
            return False, "same_category_limit"
    return True, None


def utility(order, schedule, by_id, request):
    categories = {by_id[ident]["category"] for ident in order}
    theme = int(bool(categories & set(request.preferred_categories)))
    confidence_penalty = sum(1 - by_id[ident]["criteria"]["data_confidence"] for ident in order)
    return (sum(by_id[ident]["score"] for ident in order)
            + OBJECTIVE["diversity_bonus"] * max(0, len(categories) - 1)
            + OBJECTIVE["preferred_theme_bonus"] * theme
            - OBJECTIVE["drive_hour_penalty"] * schedule["drive_seconds"] / 3600
            - OBJECTIVE["waiting_hour_penalty"] * schedule["wait_seconds"] / 3600
            - OBJECTIVE["uncertainty_penalty"] * confidence_penalty)


def improve(seed, ranked, environment, max_stops, cache):
    by_id = environment.by_id
    order = list(seed)
    def scheduled(candidate_order):
        key = tuple(candidate_order)
        if key not in cache:
            cache[key] = simulate(candidate_order, environment)
        return cache[key]

    schedule = scheduled(order)
    if schedule is None:
        return None
    while len(order) < max_stops:
        choices = []
        for candidate in ranked[:20]:
            if candidate["poi_id"] in order:
                continue
            allowed, _ = valid_addition(order, candidate, by_id, environment.request)
            if not allowed:
                continue
            for position in range(len(order) + 1):
                trial = order[:position] + [candidate["poi_id"]] + order[position:]
                result = scheduled(trial)
                if result:
                    choices.append((utility(trial, result, by_id, environment.request), trial, result))
        if not choices:
            break
        best = max(choices, key=lambda item: (item[0], tuple(item[1])))
        if best[0] <= utility(order, schedule, by_id, environment.request) + 1e-12:
            break
        _, order, schedule = best

    for _ in range(3):
        current = utility(order, schedule, by_id, environment.request)
        choices = []
        for position in range(len(order)):
            for candidate in ranked[:10]:
                if candidate["poi_id"] in order or order[position] in environment.request.required_poi_ids:
                    continue
                trial = order[:position] + [candidate["poi_id"]] + order[position + 1:]
                if not all(valid_addition(trial[:i] + trial[i + 1:], by_id[ident], by_id, environment.request)[0]
                           for i, ident in enumerate(trial)):
                    continue
                result = scheduled(trial)
                if result:
                    choices.append((utility(trial, result, by_id, environment.request), trial, result))
        if not choices:
            break
        best = max(choices, key=lambda item: (item[0], tuple(item[1])))
        if best[0] <= current + 1e-12:
            break
        _, order, schedule = best
    return order, schedule, utility(order, schedule, by_id, environment.request)


def plan_itinerary(pois, manifest, request, router, context, method="fuzzy"):
    base = {
        "status": "insufficient_data", "reason": "Không tạo được lịch khả thi theo dữ liệu và ràng buộc đã chọn",
        "dataset_version": manifest["version"], "model_version": MODEL_VERSION,
        "routing_version": router.version, "objective_version": OBJECTIVE_VERSION,
        "blocks": [], "legs": [], "warnings": [], "excluded_candidates": [],
    }
    attractions, food, excluded = filter_candidates(pois, request)
    base["excluded_candidates"] = excluded
    attractions, food = shortlist(attractions, food, request)
    base["candidate_counts"] = {"attractions": len(attractions), "food_rest": len(food)}
    required = set(request.required_poi_ids)
    available = {poi["poi_id"] for poi in attractions}
    if not required <= available:
        return dict(base, reason="Có điểm bắt buộc không thỏa điều kiện dữ liệu, category, khoảng cách hoặc hoạt động")
    if len(required) > PACE_LIMITS[request.pace]:
        return dict(base, reason="Số điểm bắt buộc vượt giới hạn của nhịp đi", excluded_candidates=excluded + [
            {"poi_id": ident, "reason": "required_poi_conflict"} for ident in sorted(required)])
    if not attractions:
        return dict(base, reason="Không có điểm tham quan nào qua được bộ lọc dữ liệu, địa phương, category và bán kính")
    if router.manifest.get("pbf_sha256") != manifest["osm"]["sha256"]:
        return dict(base, status="routing_unavailable", reason="Catalog v2 và OSRM không cùng snapshot OSM")
    all_candidates = attractions + food
    coordinates = [(request.start.latitude, request.start.longitude)] + [
        (poi["chosen_access"]["latitude"], poi["chosen_access"]["longitude"]) for poi in all_candidates]
    try:
        matrix = router.table(coordinates)
        if matrix is None:
            return dict(base, reason="OSRM không tìm được ma trận đường đi")
        if matrix["sources"][0]["distance"] > SNAP_LIMIT_METERS:
            return dict(base, reason="Điểm xuất phát quá xa đường ô tô", excluded_candidates=excluded + [
                {"poi_id": "start", "reason": "snap_too_far"}])
        routable_attractions, routable_food = [], []
        for index, poi in enumerate(all_candidates, 1):
            reason = None
            if matrix["durations"][0][index] is None:
                reason = "no_outbound_route"
            elif matrix["durations"][index][0] is None:
                reason = "no_return_route"
            elif matrix["sources"][index]["distance"] > SNAP_LIMIT_METERS:
                reason = "snap_too_far"
            if reason:
                base["excluded_candidates"].append({"poi_id": poi["poi_id"], "reason": reason})
                continue
            item = dict(poi, matrix_index=index, snap_distance_meters=matrix["sources"][index]["distance"])
            (routable_food if poi["is_food"] else routable_attractions).append(item)
        if not required <= {poi["poi_id"] for poi in routable_attractions}:
            return dict(base, reason="Điểm bắt buộc không có đủ đường đi và quay về")
        if not routable_attractions:
            return dict(base, reason="Không có điểm tham quan định tuyến được")
        ranked, ranking_info = rank(
            routable_attractions,
            [matrix["durations"][0][poi["matrix_index"]] for poi in routable_attractions],
            request, context, method,
        )
        by_id = {poi["poi_id"]: poi for poi in ranked}
        environment = SimulationEnvironment(request, by_id, matrix, routable_food)
        max_stops = PACE_LIMITS[request.pace]
        required_order = [poi["poi_id"] for poi in ranked if poi["poi_id"] in required]
        seeds = [required_order] if required_order else [[poi["poi_id"]] for poi in ranked[:SEARCH_SEED_LIMIT]]
        simulation_cache = {}
        options = [result for seed in seeds if (result := improve(seed, ranked, environment, max_stops, simulation_cache))]
        if not options:
            return dict(base, reason="Không có seed nào thỏa giờ, dwell, ăn/nghỉ, đường về và dự phòng")
        order, schedule, objective = max(options, key=lambda item: (item[2], tuple(item[0])))
        typical_major = len(order) == 1 and by_id[order[0]]["duration_profile"]["typical_minutes"] >= 180
        if len(order) < 2 and not typical_major:
            return dict(base, reason="Không đủ điều kiện ghé ít nhất hai điểm; điểm đơn lẻ không phải điểm lớn từ ba giờ")

        route_indices = [0]
        for block in schedule["blocks"]:
            if block["poi_id"]:
                poi = by_id.get(block["poi_id"])
                if poi is None:
                    poi = next(item for item in routable_food if item["poi_id"] == block["poi_id"])
                route_indices.append(poi["matrix_index"])
        route_indices.append(0)
        route_coords = [coordinates[index] for index in route_indices]
        route = router.route(route_coords, use_cache=False)
        if len(route["legs"]) != len(route_indices) - 1:
            raise RoutingUnavailable("Số chặng Route không khớp lịch v2")
        for (source, target), leg in zip(zip(route_indices, route_indices[1:]), route["legs"], strict=True):
            matrix["durations"][source][target] = leg["duration"]
            matrix["distances"][source][target] = leg["distance"]
        environment.fixed_food = schedule["fixed_food"]
        schedule = simulate(order, environment)
        if schedule is None:
            return dict(base, reason="Route thực làm lịch vượt ràng buộc; cần nới thời gian hoặc bán kính")
        objective = utility(order, schedule, by_id, request)

        used = set(order)
        for poi in ranked:
            if poi["poi_id"] not in used:
                base["excluded_candidates"].append({"poi_id": poi["poi_id"],
                                                       "reason": "stop_limit" if len(order) == max_stops else "time_window_conflict"})
        warnings = [
            "Thời gian OSRM không phải dự báo giao thông trực tiếp.",
            "Điểm tiếp cận chưa xác minh thực địa được hiển thị là ước lượng.",
        ]
        if any(block["duration_source"] == "category_default" for block in schedule["blocks"]):
            warnings.append("Một số thời lượng tham quan vẫn dùng fallback theo category.")
        if any(block["poi_id"] is None and block["role"] in ("meal", "break") for block in schedule["blocks"]):
            warnings.append("Có khối ăn/nghỉ tự túc vì chưa chọn được địa điểm đủ dữ liệu trong cửa sổ giờ.")
        return {
            **base, **schedule, "reason": "Lịch trình gợi ý theo dữ liệu v2 hiện có",
            "ranking": ranking_info, "ranked_candidates": [{"poi_id": poi["poi_id"], "score": poi["score"],
                                                               "criteria": poi["criteria"]} for poi in ranked],
            "objective": objective, "objective_parameters": OBJECTIVE,
            "geometry": route["geometry"], "warnings": warnings,
        }
    except RoutingUnavailable as error:
        return dict(base, status="routing_unavailable", reason=str(error), blocks=[], legs=[])
