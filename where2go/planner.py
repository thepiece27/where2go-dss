import math
from . import MODEL_VERSION
from .catalog import candidates
from .config import CANDIDATE_LIMIT, SNAP_LIMIT_METERS
from .hours import intervals_on
from .ranking import rank_pois
from .routing import RoutingUnavailable


def clock_text(seconds):
    value = math.ceil(seconds / 60)
    return f"{value // 60:02d}:{value % 60:02d}"


def simulate(order, by_id, matrix, request):
    now = (request.start_time.hour*60 + request.start_time.minute)*60
    end = (request.end_time.hour*60 + request.end_time.minute)*60
    start_time = now
    previous, stops, legs = 0, [], []
    total_drive = total_wait = 0
    provisional = False
    for ident in order:
        poi = by_id[ident]
        index = poi["matrix_index"]
        travel = matrix["durations"][previous][index]
        if travel is None:
            return None
        arrive = now + travel
        begin = arrive
        duration = poi["visit_duration_minutes"] * 60
        windows = intervals_on(poi["hours_raw"], request.date)
        if windows is not None:
            feasible = [max(arrive, a*60) for a, b in windows if max(arrive, a*60) + duration <= b*60]
            if not feasible:
                return None
            begin = min(feasible)
        else:
            provisional = True
        now = begin + duration
        if now > end:
            return None
        total_drive += travel
        total_wait += begin-arrive
        legs.append({"from": "start" if previous == 0 else order[len(stops)-1], "to": ident,
                     "duration_seconds": travel, "distance_meters": matrix["distances"][previous][index]})
        stops.append(dict(poi, arrival_time=clock_text(arrive), visit_start_time=clock_text(begin),
                          departure_time=clock_text(now), wait_minutes=(begin-arrive)/60,
                          hours_status="known" if windows is not None else "unknown"))
        previous = index
    home = matrix["durations"][previous][0]
    if home is None or now + home > end:
        return None
    legs.append({"from": order[-1] if order else "start", "to": "start", "duration_seconds": home,
                 "distance_meters": matrix["distances"][previous][0]})
    return {"stops": stops, "legs": legs, "return_time": clock_text(now+home),
            "return_seconds": now+home, "drive_seconds": total_drive+home,
            "wait_seconds": total_wait, "total_seconds": now+home-start_time,
            "status": "provisional" if provisional else "ready"}


def plan_itinerary(pois, manifest, request, router, method="fuzzy"):
    result = {"status": "insufficient_data", "reason": "Không đủ địa điểm trong điều kiện yêu cầu",
              "dataset_version": manifest["version"], "model_version": MODEL_VERSION,
              "routing_version": router.version, "stops": [], "legs": [], "warnings": [], "excluded": []}
    pool, counts = candidates(pois, request, CANDIDATE_LIMIT)
    result["candidate_counts"] = counts
    if len(pool) < 2:
        return result
    if router.manifest.get("pbf_sha256") != manifest["osm"]["sha256"]:
        return dict(result, status="routing_unavailable", reason="Catalog và OSRM không cùng snapshot OSM")
    coords = [(request.start.latitude, request.start.longitude)] + [(p["latitude"], p["longitude"]) for p in pool]
    try:
        matrix = router.table(coords)
        if matrix is None:
            return dict(result, reason="Không có tuyến đường tới các điểm được chọn")
        result["routing_issues"] = matrix.get("invalid_edges", [])
        if matrix["sources"][0]["distance"] > SNAP_LIMIT_METERS:
            return dict(result, reason="Điểm xuất phát quá xa đường ô tô. Hãy chọn một điểm trên đường.")
        valid = []
        for i, p in enumerate(pool, 1):
            if matrix["durations"][0][i] is None or matrix["durations"][i][0] is None:
                result["excluded"].append({"poi_id": p["poi_id"], "reason": "no_round_trip_route"})
            elif matrix["sources"][i]["distance"] > SNAP_LIMIT_METERS:
                result["excluded"].append({"poi_id": p["poi_id"], "reason": "snap_too_far"})
            else:
                valid.append(dict(p, matrix_index=i, snap_distance_meters=matrix["sources"][i]["distance"]))
        counts["routable"] = len(valid)
        if len(valid) < 2:
            return dict(result, reason="Không đủ 2 POI có đường đi và quay về, với điểm tiếp cận phù hợp")
        ranked, info = rank_pois(valid, [matrix["durations"][0][p["matrix_index"]] for p in valid], request, method)
        result["ranking"] = info
        result["ranked_candidates"] = [{"poi_id": p["poi_id"], "score": p["score"], "criteria": p["criteria"]} for p in ranked]
        by_id = {p["poi_id"]: p for p in ranked}
        order = []
        current = simulate(order, by_id, matrix, request)
        while len(order) < 5:
            inserted = False
            for p in ranked:
                if p["poi_id"] in order:
                    continue
                choices = []
                for pos in range(len(order)+1):
                    trial = order[:pos] + [p["poi_id"]] + order[pos:]
                    schedule = simulate(trial, by_id, matrix, request)
                    if schedule:
                        choices.append((schedule["drive_seconds"]-current["drive_seconds"], schedule["return_seconds"], pos, trial, schedule))
                if choices:
                    _, _, _, order, current = min(choices, key=lambda c: c[:3])
                    inserted = True
                    break  # restart descending rank after each insertion
            if not inserted:
                break
        if len(order) < 2:
            return dict(result, reason="Không đủ thời gian/giờ mở cửa để ghé ít nhất 2 POI và quay về")
        for p in ranked:
            if p["poi_id"] not in order:
                result["excluded"].append({"poi_id": p["poi_id"], "reason": "stop_limit" if len(order) == 5 else "time_window_or_route_infeasible"})
        route_coords = [coords[0]] + [coords[by_id[i]["matrix_index"]] for i in order] + [coords[0]]
        route = router.route(route_coords, use_cache=False)
        # A via-point Route can differ from pairwise Table because of turn handling.
        # Revalidate the displayed route's actual legs before returning its schedule.
        if "legs" in route:
            indexes = [0] + [by_id[i]["matrix_index"] for i in order] + [0]
            if len(route["legs"]) != len(indexes)-1:
                raise RoutingUnavailable("Số chặng Route không khớp lịch trình")
            for (a, b), leg in zip(zip(indexes, indexes[1:]), route["legs"], strict=True):
                if not all(isinstance(leg.get(k), (int, float)) and math.isfinite(leg[k]) and leg[k] >= 0 for k in ("duration", "distance")):
                    raise RoutingUnavailable("OSRM trả chặng không hợp lệ")
                matrix["durations"][a][b] = leg["duration"]
                matrix["distances"][a][b] = leg["distance"]
            current = simulate(order, by_id, matrix, request)
            if current is None:
                return dict(result, reason="Tuyến hiển thị vượt khung giờ; hãy tăng thời gian hoặc thu hẹp bán kính")
        result.update(current)
        result.update(reason="Lịch trình gợi ý theo dữ liệu hiện có", geometry=route["geometry"])
        result["warnings"] = ["Thời lượng tham quan là ước lượng theo loại hình.",
                              "Thời gian đường bộ không bao gồm giao thông thời gian thực, tìm chỗ đỗ xe hoặc đi bộ từ đường tới điểm tham quan."]
        if current["status"] == "provisional":
            result["warnings"].append("Tạm tính — cần kiểm tra giờ mở cửa/ngoại lệ ngày lễ của các điểm chưa xác minh.")
        if any(p["coordinate_status"] != "osm_point" for p in current["stops"]):
            result["warnings"].append("Có điểm dùng tọa độ đại diện khu tham quan; cần kiểm tra lối vào thực tế.")
        return result
    except RoutingUnavailable as error:
        return dict(result, status="routing_unavailable", reason=str(error), stops=[], legs=[])
