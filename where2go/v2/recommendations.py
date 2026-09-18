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
from .models import AHPPreferences
from .quality import recommendation_eligible
from .ranking import ahp_weights, confidence
from .trip_models import TripContext

POLICY_VERSION = "poi-recommendation-1.0"
CRITERIA = ("preference_match", "place_quality", "travel_cost", "data_confidence")
PRESETS = {
    "balanced": (0.40, 0.30, 0.20, 0.10),
    "interests": (0.55, 0.20, 0.15, 0.10),
    "nearby": (0.30, 0.20, 0.40, 0.10),
    "quality": (0.25, 0.45, 0.20, 0.10),
}
METHODS = ("nearby", "quality", "content", "equal", "crisp", "fuzzy")


class RecommendationRequest(TripContext):
    preset: Literal["balanced", "interests", "nearby", "quality"] = "balanced"
    radius_km: float = Field(default=30, ge=1, le=80)
    top_k: int = Field(default=10, ge=1, le=20, strict=True)

    @property
    def ahp(self):
        w = PRESETS[self.preset]
        return AHPPreferences(
            comparisons=[w[i] / w[j] for i in range(4) for j in range(i + 1, 4)]
        )


def prepare_candidates(
    pois, manifest, request, router, context, *, pool_size=40, geographic_only=False
):
    """Compute one fixed decision matrix for all methods in an experiment."""
    if pool_size < 1:
        raise ValueError("pool_size must be positive")
    origin = (request.start.latitude, request.start.longitude)
    selected = set(request.selected_poi_ids)
    eligible, distances = [], {}
    for poi in pois:
        if poi["poi_id"] in selected or not recommendation_eligible(
            poi, request.location
        ):
            continue
        if (
            intervals_on_date(
                poi.get("hours_weekly"), poi.get("hours_exceptions"), request.date
            )
            == []
        ):
            continue
        distance = haversine(origin, (poi["latitude"], poi["longitude"]))
        if distance <= request.radius_km:
            eligible.append(poi)
            distances[poi["poi_id"]] = distance
    preference = context.preference_components(eligible, request)
    quality = {p["poi_id"]: context.adjusted_quality(p) for p in eligible}
    groups = (
        sorted(
            eligible, key=lambda p: (-preference[p["poi_id"]]["score"], p["poi_id"])
        ),
        sorted(eligible, key=lambda p: (distances[p["poi_id"]], p["poi_id"])),
        sorted(eligible, key=lambda p: (-quality[p["poi_id"]][0], p["poi_id"])),
    )
    union = {p["poi_id"]: p for group in groups for p in group[:pool_size]}
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
        data_confidence, evidence = confidence(poi, request.date)
        rows.append(
            {
                "poi": poi,
                "values": [
                    preference[ident]["score"],
                    quality[ident][0],
                    cost,
                    data_confidence,
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
        "candidate_count": len(rows),
        "pool_size_per_source": pool_size,
        "dataset_version": manifest["version"],
    }


def score_candidates(prepared, request, method="crisp"):
    """Pure scoring; API and evaluator call exactly this function."""
    if method not in METHODS:
        raise ValueError("Unknown recommendation method")
    weights, cr = ahp_weights(
        request.ahp.comparisons,
        request.ahp.uncertainty if method == "fuzzy" else [1.0] * 6,
    )
    if method == "equal":
        weights = np.full(4, 0.25)
    rows = prepared["rows"]
    values = np.asarray([r["values"] for r in rows], dtype=float).reshape((-1, 4))
    if method == "nearby":
        cost = values[:, 2]
        spread = float(np.ptp(cost)) if len(cost) else 0
        scores = (
            1 - (cost - cost.min()) / spread
            if spread > 1e-12
            else np.full(len(cost), 0.5)
        )
    elif method in ("content", "quality"):
        scores = values[:, 0 if method == "content" else 1]
    else:
        scores = topsis(values, weights, (True, True, False, True))
    ranked = sorted(
        zip(rows, scores, strict=True),
        key=lambda pair: (-float(pair[1]), pair[0]["poi"]["poi_id"]),
    )
    return ranked, {
        "method": method,
        "weights": dict(zip(CRITERIA, map(float, weights))),
        "cr": cr,
        "preset": request.preset,
        "criteria_order": list(CRITERIA),
    }


def recommendation_response(prepared, request, method="crisp"):
    from .trips import card

    ranked, ranking = score_candidates(prepared, request, method)
    items = []
    for index, (row, score) in enumerate(ranked[: request.top_k], 1):
        poi, reasons = row["poi"], []
        content = row["content"]
        if content["category_match"]:
            reasons.append("Thuộc loại hình bạn ưu tiên.")
        elif content["matched_tokens"]:
            from where2go.ranking import normalize

            matched = [
                text
                for text in request.interests
                if set(normalize(text).split())
                and set(normalize(text).split()) <= set(content["matched_tokens"])
            ]
            reasons.append(
                "Khớp sở thích: " + ", ".join(matched) + "."
                if matched
                else "Có từ khóa trùng với sở thích bạn nhập."
            )
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
                "Chưa có cặp điểm và số lượt đánh giá đủ bằng chứng; tiêu chí chất lượng dùng giá trị trung tính."
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
        "personalized": bool(request.interests or request.preferred_categories),
        "message": ""
        if items
        else "Chưa có POI đáp ứng điều kiện. Hãy đổi vị trí, ngày hoặc mở rộng bán kính; hệ thống không tự nới điều kiện.",
    }


def recommend_pois(pois, manifest, request, router, context, **options):
    return recommendation_response(
        prepare_candidates(pois, manifest, request, router, context, **options), request
    )
