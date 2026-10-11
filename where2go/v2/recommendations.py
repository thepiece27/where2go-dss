"""Content/context POI recommendations shared by the web API and experiments.

Scores are relative to the complete retrieved pool, never to the displayed top K.
No behavioral labels are inferred from these scores.
"""

from typing import Literal

import numpy as np
from pydantic import Field

from where2go.catalog import haversine
from where2go.config import SNAP_LIMIT_METERS
from where2go.ranking import topsis
from where2go.routing import RoutingUnavailable
from .hours import intervals_on_date
from .intent import interpret_request, poi_concepts
from .quality import recommendation_eligible
from .ranking import confidence
from .trip_models import TripContext
from .discovery import EXCLUDED, matches_scope
from .taxonomy import CATEGORIES

POLICY_VERSION = "poi-recommendation-3.0"
CRITERIA = ("preference_match", "place_quality", "travel_cost")
PRESETS = {
    "balanced": (4 / 9, 3 / 9, 2 / 9),
    "interests": (11 / 18, 2 / 9, 1 / 6),
    "nearby": (1 / 3, 2 / 9, 4 / 9),
    "quality": (5 / 18, 1 / 2, 2 / 9),
}
METHODS = (
    "nearby",
    "quality",
    "taxonomy",
    "text",
    "weighted_sum",
    "topsis_no_quality",
    "topsis",
)


class RecommendationRequest(TripContext):
    scope: Literal["", "danang_hoian"] = ""
    tourism_only: bool = False
    preset: Literal["balanced", "interests", "nearby", "quality"] = "balanced"
    radius_km: float = Field(default=30, ge=1, le=80)
    top_k: int = Field(default=10, ge=1, le=20, strict=True)


def prepare_candidates(
    pois, manifest, request, router, context, *, pool_size=40, geographic_only=False
):
    """Compute one fixed decision matrix for all methods in an experiment."""
    if pool_size is not None and pool_size < 1:
        raise ValueError("pool_size must be positive")
    intent = interpret_request(request)
    origin = (request.start.latitude, request.start.longitude)
    selected = set(request.selected_poi_ids)
    # A default tourism group must not silently defeat an explicit category.
    included_categories = set(intent.preferred_categories) & EXCLUDED
    if not request.tourism_only:
        included_categories.clear()
    eligible, distances = [], {}
    filtered = {
        "scope": 0,
        "quality_or_location": 0,
        "selected": 0,
        "excluded_category_or_topic": 0,
        "required_category": 0,
        "closed_on_date": 0,
        "unknown_hours": 0,
        "outside_radius": 0,
    }
    for poi in pois:
        if not matches_scope(poi, request.scope, request.tourism_only,
                             include_categories=included_categories):
            filtered["scope"] += 1
            continue
        if poi["poi_id"] in selected:
            filtered["selected"] += 1
            continue
        if not recommendation_eligible(poi, request.location):
            filtered["quality_or_location"] += 1
            continue
        concepts = poi_concepts(poi)
        if poi["category"] in intent.excluded_categories or concepts & set(intent.negative_concepts):
            filtered["excluded_category_or_topic"] += 1
            continue
        if (intent.category_mode == "only"
                and poi["category"] not in intent.preferred_categories):
            filtered["required_category"] += 1
            continue
        intervals = intervals_on_date(
            poi.get("hours_weekly"), poi.get("hours_exceptions"), request.date
        )
        if intervals == []:
            filtered["closed_on_date"] += 1
            continue
        if request.require_known_hours and intervals is None:
            filtered["unknown_hours"] += 1
            continue
        distance = haversine(origin, (poi["latitude"], poi["longitude"]))
        if distance <= request.radius_km:
            eligible.append(poi)
            distances[poi["poi_id"]] = distance
        else:
            filtered["outside_radius"] += 1
    preference = context.preference_components(eligible, request, intent)
    matching = [
        poi for poi in eligible
        if not intent.has_positive_intent
        or request.allow_non_matching
        or preference[poi["poi_id"]]["has_evidence"]
    ]
    quality = {p["poi_id"]: context.adjusted_quality(p) for p in matching}
    groups = (
        sorted(
            matching, key=lambda p: (-preference[p["poi_id"]]["score"], p["poi_id"])
        ),
        sorted(matching, key=lambda p: (distances[p["poi_id"]], p["poi_id"])),
        sorted(matching, key=lambda p: (-quality[p["poi_id"]][0], p["poi_id"])),
    )
    union = {
        p["poi_id"]: p
        for group in groups
        for p in (group if pool_size is None else group[:pool_size])
    }
    pool = [union[i] for i in sorted(union)]
    costs = [distances[p["poi_id"]] for p in pool]
    mode, routing_reason = (
        "geographic_distance",
        "Không có dữ liệu đường đi đầy đủ; dùng khoảng cách đường chim bay.",
    )
    expected = manifest.get("osm", {}).get("sha256")
    if (
        pool
        and not geographic_only
        and expected
        and router.manifest.get("pbf_sha256") == expected
    ):
        from .trips import position

        road_costs = []
        try:
            for offset in range(0, len(pool), 30):
                batch = pool[offset : offset + 30]
                points = [position(p) for p in batch]
                matrix = router.table(
                    [origin] + [(p["latitude"], p["longitude"]) for p in points]
                )
                if not matrix or any(
                    s["distance"] > SNAP_LIMIT_METERS for s in matrix["sources"]
                ):
                    raise RoutingUnavailable("Điểm tiếp cận chưa đủ gần đường ô tô.")
                for i in range(1, len(batch) + 1):
                    value = matrix["durations"][0][i]
                    back = matrix["durations"][i][0]
                    if (
                        value is None
                        or back is None
                        or not np.isfinite(value)
                        or value < 0
                    ):
                        raise RoutingUnavailable(
                            "Thiếu tuyến đi hoặc quay về cho ít nhất một ứng viên."
                        )
                    road_costs.append(float(value))
            costs, mode, routing_reason = (
                road_costs,
                "road_time",
                "Thời gian lái xe OSRM; không có giao thông trực tiếp.",
            )
        except RoutingUnavailable:
            # Discard every partial road batch. A single matrix has one cost unit.
            pass
    rows = []
    for poi, cost in zip(pool, costs, strict=True):
        ident = poi["poi_id"]
        _, evidence = confidence(poi, request.date)
        rows.append(
            {
                "poi": poi,
                "values": [
                    preference[ident]["score"],
                    quality[ident][0],
                    cost,
                ],
                "content": preference[ident],
                "rating": quality[ident][1],
                "confidence_evidence": evidence,
                "distance_km": distances[ident],
                "hours_known": intervals_on_date(
                    poi.get("hours_weekly"), poi.get("hours_exceptions"), request.date
                )
                is not None,
            }
        )
    return {
        "rows": rows,
        "travel_metric": mode,
        "travel_unit": "seconds" if mode == "road_time" else "km",
        "routing_message": routing_reason,
        "eligible_count": len(eligible),
        "matching_count": len(matching),
        "excluded_non_matching_count": len(eligible) - len(matching),
        "candidate_count": len(rows),
        "pool_size_per_source": pool_size,
        "dataset_version": manifest["version"],
        "interpreted_request": intent.as_dict(),
        "filter_counts": filtered,
        "included_categories": sorted(included_categories),
        "filter_message": (
            "Đã áp dụng điều kiện: "
            + "; ".join(
                part
                for part in (
                    "chỉ " + ", ".join(CATEGORIES[c] for c in intent.preferred_categories)
                    if intent.category_mode == "only" else "",
                    "loại " + ", ".join(CATEGORIES[c] for c in intent.excluded_categories)
                    if intent.excluded_categories else "",
                    "phải có giờ mở cửa" if request.require_known_hours else "",
                    "cho phép kết quả ít khớp" if request.allow_non_matching else "",
                )
                if part
            )
            + "."
            if any((intent.category_mode == "only", intent.excluded_categories,
                    request.require_known_hours, request.allow_non_matching))
            else ""
        ),
    }


def score_candidates(prepared, request, method="topsis"):
    """Pure scoring; API and evaluator call exactly this function."""
    if method not in METHODS:
        raise ValueError("Unknown recommendation method")
    weights = np.asarray(PRESETS[request.preset], dtype=float)
    rows = prepared["rows"]
    values = np.asarray([r["values"] for r in rows], dtype=float).reshape((-1, 3))
    active_criteria = CRITERIA
    if method == "nearby":
        cost = values[:, 2]
        spread = float(np.ptp(cost)) if len(cost) else 0
        scores = (
            1 - (cost - cost.min()) / spread
            if spread > 1e-12
            else np.full(len(cost), 0.5)
        )
    elif method == "quality":
        scores = values[:, 1]
    elif method in ("taxonomy", "text"):
        key = "taxonomy" if method == "taxonomy" else "cosine"
        scores = np.asarray([row["content"][key] for row in rows], dtype=float)
    elif method == "weighted_sum":
        # Same vector normalization and weights as TOPSIS isolate aggregation.
        norms = np.linalg.norm(values, axis=0)
        normalized = np.divide(values, norms, out=np.zeros_like(values), where=norms > 0)
        scores = normalized @ (weights * np.array([1, 1, -1]))
    elif method == "topsis_no_quality":
        active_criteria = (CRITERIA[0], CRITERIA[2])
        reduced = values[:, (0, 2)]
        reduced_weights = weights[[0, 2]]
        reduced_weights = reduced_weights / reduced_weights.sum()
        scores = topsis(reduced, reduced_weights, (True, False))
        weights = reduced_weights
    else:
        scores = topsis(values, weights, (True, True, False))
    ranked = sorted(
        zip(rows, scores, strict=True),
        key=lambda pair: (-float(pair[1]), pair[0]["poi"]["poi_id"]),
    )
    return ranked, {
        "method": method,
        "weights": dict(zip(active_criteria, map(float, weights))),
        "weight_source": "preset",
        "preset": request.preset,
        "criteria_order": list(active_criteria),
        "data_evidence_role": "eligibility_warning_only",
    }


def recommendation_response(prepared, request, method="topsis"):
    from .trips import card

    ranked, ranking = score_candidates(prepared, request, method)
    items = []
    for index, (row, score) in enumerate(ranked[: request.top_k], 1):
        poi, reasons = row["poi"], []
        content = row["content"]
        if content["category_match"]:
            reasons.append("Thuộc loại hình bạn ưu tiên.")
        elif content["matched_concepts"]:
            reasons.append("Khớp chủ đề: " + ", ".join(content["matched_concepts"]) + ".")
        elif content["cosine"] > 0:
            reasons.append("Nội dung địa điểm có từ ngữ tương đồng với nhu cầu.")
        if prepared["travel_metric"] == "road_time":
            reasons.append(
                f"Khoảng {row['values'][2] / 60:.0f} phút lái xe từ điểm xuất phát theo OSRM."
            )
        else:
            reasons.append(
                f"Cách điểm xuất phát {row['distance_km']:.1f} km theo vị trí (đường chim bay)."
            )
        observation = row["rating"].get("observation")
        if observation:
            reasons.append(
                f"Nguồn ghi {observation['rating']}/5 từ {observation['review_count']} đánh giá."
            )
        elif row["hours_known"]:
            reasons.append("Có thông tin giờ mở cửa theo ngày đã chọn.")
        warnings = []
        if not observation:
            warnings.append(
                "Chưa có cặp điểm và số lượt đánh giá; chất lượng dùng prior của nhóm và vẫn được ghi là thiếu quan sát."
            )
        if not row["hours_known"]:
            warnings.append(
                "Chưa có giờ mở cửa cho ngày đã chọn; cần kiểm tra trước khi đi."
            )
        if not row["confidence_evidence"]["access"]:
            warnings.append("Điểm tiếp cận ô tô chưa được xác minh.")
        items.append(
            card(poi)
            | {
                "rank": index,
                "score": float(score),
                "criteria": dict(zip(CRITERIA, row["values"])),
                "evidence_completeness": row["confidence_evidence"],
                "reasons": reasons[:3],
                "warnings": warnings,
                "source_url": poi.get("source_url"),
                "explanation": {
                    k: row[k]
                    for k in (
                        "content",
                        "rating",
                        "confidence_evidence",
                        "distance_km",
                        "hours_known",
                    )
                },
                "provenance": poi.get("provenance", {}),
            }
        )
    return {
        "items": items,
        "ranking": ranking,
        "policy_version": POLICY_VERSION,
        **{k: v for k, v in prepared.items() if k != "rows"},
        "personalized": bool(
            request.interests
            or request.experience_topics
            or request.preferred_categories
            or request.excluded_categories
        ),
        "message": ""
        if items
        else "Chưa có POI có bằng chứng đáp ứng nhu cầu và điều kiện đã chọn. Hệ thống không tự nới điều kiện; hãy sửa bộ lọc hoặc bật cho phép kết quả ít khớp.",
    }


def recommend_pois(pois, manifest, request, router, context, **options):
    return recommendation_response(
        prepare_candidates(pois, manifest, request, router, context, **options), request
    )
