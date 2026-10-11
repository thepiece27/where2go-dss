from copy import deepcopy
import math

import pytest
from fastapi.testclient import TestClient

from where2go.api import create_app
from where2go.v2.ranking import RankingContext
from where2go.v2.recommendations import (
    RecommendationRequest,
    prepare_candidates,
    recommendation_response,
    score_candidates,
)
from where2go.v2.recommendation_evaluation import judged_metrics
from where2go.v2.quality import recommendation_eligible
from test_trip_suggestions import poi, Router, MANIFEST, request


def req(**updates):
    base = request([]).model_dump(mode="json")
    return RecommendationRequest.model_validate(
        {
            k: base[k]
            for k in (
                "start",
                "date",
                "location",
                "interests",
                "preferred_categories",
                "selected_poi_ids",
            )
        }
        | updates
    )


def test_retrieval_includes_relevant_poi_beyond_nearest_thirty():
    rows = [poi(i) for i in range(70)] + [
        poi(90, category="beach", description="biển thư giãn")
    ]
    r = req(interests=["biển"], preferred_categories=["beach"], radius_km=80)
    prepared = prepare_candidates(
        rows, MANIFEST, r, Router(unavailable=True), RankingContext(rows)
    )
    assert "90" in {p["poi"]["poi_id"] for p in prepared["rows"]}
    detail = next(p for p in prepared["rows"] if p["poi"]["poi_id"] == "90")
    assert detail["content"]["category_match"] and detail["values"][0] >= 0.7


def test_preference_and_preset_change_controlled_ranking():
    rows = [poi(1), poi(2, category="beach", description="biển thiên nhiên")]
    ctx = RankingContext(rows)
    r = req(preferred_categories=["museum"])
    p = prepare_candidates(rows, MANIFEST, r, Router(), ctx)
    assert recommendation_response(p, r)["items"][0]["poi_id"] == "1"
    r2 = req(preferred_categories=["beach"])
    assert (
        recommendation_response(
            prepare_candidates(rows, MANIFEST, r2, Router(), ctx), r2
        )["items"][0]["poi_id"]
        == "2"
    )
    mixed = prepare_candidates(
        rows, MANIFEST, req(allow_non_matching=True), Router(), ctx
    )
    mixed["rows"][0]["values"] = [0.95, 0.5, 600]
    mixed["rows"][1]["values"] = [0.2, 0.5, 60]
    assert score_candidates(mixed, req(preset="interests"))[0][0][0]["poi"]["poi_id"] == "1"
    assert score_candidates(mixed, req(preset="nearby"))[0][0][0]["poi"]["poi_id"] == "2"


@pytest.mark.parametrize(
    "preferences",
    [
        {"interests": ["tâm linh"]},
        {"interests": ["TAM LINH"]},
        {"preferred_categories": ["temple"]},
        {"preferred_categories": ["cafe"]},
    ],
)
def test_explicit_preference_overrides_default_tourism_category_filter(preferences):
    rows = [
        poi(1, name="Bãi biển", category="beach", description="biển thư giãn"),
        poi(2, name="Chùa Linh Ứng", category="temple", description="tâm linh"),
        poi(3, name="Quán cà phê", category="cafe", google_category_raw="Cafe"),
        poi(4, name="Nhà hàng", category="restaurant", google_category_raw="Restaurant"),
    ]
    context = RankingContext(rows)
    base = req(scope="danang_hoian", tourism_only=True)
    default = prepare_candidates(rows, MANIFEST, base, Router(), context)
    assert [r["poi"]["poi_id"] for r in default["rows"]] == ["1"]
    changed = base.model_copy(update=preferences)
    prepared = prepare_candidates(rows, MANIFEST, changed, Router(), context)
    expected = "cafe" if preferences.get("preferred_categories") == ["cafe"] else "temple"
    assert {r["poi"]["category"] for r in prepared["rows"]} == {expected}
    result = recommendation_response(prepared, changed)
    assert result["items"][0]["category"] == expected
    assert result["items"][0]["criteria"]["preference_match"] >= 0.7
    # Removing the preference must restore the default pool on the same context.
    assert prepare_candidates(rows, MANIFEST, base, Router(), context) == default


def test_spiritual_interest_preserves_scope_radius_hours_and_selection():
    rows = [
        poi(1, name="Chùa mở cửa", category="temple"),
        poi(2, name="Chùa đóng cửa", category="temple", business_status="permanently_closed"),
        poi(3, name="Chùa nghỉ hôm nay", category="temple", hours_weekly=[[]] * 7),
        poi(4, name="Chùa đã chọn", category="temple"),
        poi(5, name="Chùa xa", category="temple", latitude=15.99),
        poi(6, name="Chùa ngoài phạm vi", category="temple", latitude=16.30, longitude=107.8),
    ]
    context = RankingContext(rows)
    r = req(interests=["tâm linh"], tourism_only=True, scope="danang_hoian",
            radius_km=5, selected_poi_ids=["4"])
    result = prepare_candidates(rows, MANIFEST, r, Router(), context)
    assert [row["poi"]["poi_id"] for row in result["rows"]] == ["1"]
    wider = prepare_candidates(rows, MANIFEST, r.model_copy(update={"radius_km": 80}), Router(), context)
    assert {row["poi"]["poi_id"] for row in wider["rows"]} == {"1", "5"}


def test_partial_route_batches_use_geographic_cost_for_every_poi():
    class Partial(Router):
        def table(self, coords):
            data = super().table(coords)
            if self.tables == 2:
                data["durations"][0][1] = None
            return data

    rows = [poi(i) for i in range(50)]
    p = prepare_candidates(rows, MANIFEST, req(), Partial(), RankingContext(rows))
    assert p["travel_metric"] == "geographic_distance" and p["candidate_count"] > 30
    assert all(row["values"][2] == row["distance_km"] for row in p["rows"])


def test_topk_parity_missing_data_closed_selection_and_no_mutation():
    rows = [poi(i, hours_weekly=None) for i in range(25)] + [
        poi(99, business_status="permanently_closed")
    ]
    before = deepcopy(rows)
    r = req(selected_poi_ids=["0"])
    p = prepare_candidates(rows, MANIFEST, r, Router(), RankingContext(rows))
    a = recommendation_response(p, r)
    b = recommendation_response(p, r.model_copy(update={"top_k": 20}))
    assert a["items"] == b["items"][:10] and a["travel_metric"] == "road_time"
    assert all(x["poi_id"] not in {"0", "99"} for x in b["items"])
    assert all(
        x["criteria"]["place_quality"] == 0.5 and x["warnings"] for x in a["items"]
    )
    with TestClient(create_app(router=Router(), v2_data=(rows, MANIFEST))) as client:
        assert (
            client.post(
                "/api/v2/recommendations", json=r.model_dump(mode="json")
            ).json()
            == a
        )
        for route in ("/", "/explore", "/itinerary", "/common.js"):
            assert client.get(route).status_code == 200
    assert before == rows


def test_empty_ties_and_direct_preset_weights():
    rows = [poi(1), poi(2)]
    r = req()
    p = prepare_candidates(rows, MANIFEST, r, Router(), RankingContext(rows))
    a = recommendation_response(p, r)
    assert a["ranking"]["method"] == "topsis"
    assert a["ranking"]["weight_source"] == "preset"
    assert list(a["ranking"]["weights"].values()) == pytest.approx([4 / 9, 3 / 9, 2 / 9])
    assert "cr" not in a["ranking"]
    assert a["ranking"]["data_evidence_role"] == "eligibility_warning_only"
    assert "data_confidence" not in a["items"][0]["criteria"]
    assert all(math.isfinite(x["score"]) for x in a["items"])
    empty = prepare_candidates(
        rows, MANIFEST, req(selected_poi_ids=["1", "2"]), Router(), RankingContext(rows)
    )
    assert recommendation_response(empty, r)["items"] == []


def test_weighted_sum_baseline_respects_cost_and_handles_empty_pool():
    rows = [poi(1), poi(2)]
    r = req()
    prepared = prepare_candidates(rows, MANIFEST, r, Router(), RankingContext(rows))
    prepared["rows"][0]["values"] = [0.8, 0.5, 60]
    prepared["rows"][1]["values"] = [0.8, 0.5, 600]
    result = recommendation_response(prepared, r, "weighted_sum")
    assert [p["poi_id"] for p in result["items"]] == ["1", "2"]
    assert result["items"][0]["score"] > result["items"][1]["score"]
    prepared["rows"] = []
    assert recommendation_response(prepared, r, "weighted_sum")["items"] == []


def test_unknown_recommendation_method_is_rejected():
    with pytest.raises(ValueError, match="Unknown recommendation method"):
        score_candidates({"rows": []}, req(), "unsupported")


def test_negative_only_and_unknown_negation_are_not_silently_positive():
    rows = [
        poi(1, category="temple", name="Chùa", description="điểm tâm linh"),
        poi(2, category="park", name="Công viên", description="cây xanh"),
    ]
    context = RankingContext(rows)
    negative = req(interests=["không thích tâm linh"])
    prepared = prepare_candidates(rows, MANIFEST, negative, Router(), context)
    assert [row["poi"]["poi_id"] for row in prepared["rows"]] == ["2"]
    assert prepared["interpreted_request"]["excluded_categories"] == ["temple"]
    with pytest.raises(ValueError, match="Chưa hiểu điều kiện phủ định"):
        req(interests=["không thích đông đúc"])


def test_natural_only_category_and_explicit_conflict_are_enforced():
    rows = [poi(1, category="museum"), poi(2, category="park")]
    context = RankingContext(rows)
    only = req(interests=["chỉ bảo tàng"])
    prepared = prepare_candidates(rows, MANIFEST, only, Router(), context)
    assert [row["poi"]["category"] for row in prepared["rows"]] == ["museum"]
    assert prepared["interpreted_request"]["category_mode"] == "only"
    with pytest.raises(ValueError, match="vừa được chọn vừa bị loại trừ"):
        req(preferred_categories=["museum"], excluded_categories=["museum"])


def test_sea_concept_requires_sea_evidence_and_no_result_is_honest():
    rows = [
        poi(1, category="beach", name="Bãi biển", description="bờ biển yên tĩnh"),
        poi(2, category="bridge", name="Cầu thành phố", description="ngắm cảnh chụp ảnh"),
    ]
    context = RankingContext(rows)
    sea = req(interests=["ngắm cảnh biển"])
    prepared = prepare_candidates(rows, MANIFEST, sea, Router(), context)
    assert [row["poi"]["poi_id"] for row in prepared["rows"]] == ["1"]
    no_match = req(interests=["tâm linh"])
    result = recommendation_response(
        prepare_candidates(rows, MANIFEST, no_match, Router(), context), no_match
    )
    assert result["items"] == [] and "không tự nới" in result["message"]


def test_known_hours_filter_is_hard_and_relaxation_is_explicit():
    rows = [poi(1, hours_weekly=None), poi(2)]
    context = RankingContext(rows)
    strict = req(require_known_hours=True)
    prepared = prepare_candidates(rows, MANIFEST, strict, Router(), context)
    assert [row["poi"]["poi_id"] for row in prepared["rows"]] == ["2"]
    assert prepared["filter_counts"]["unknown_hours"] == 1


def test_recommendation_gate_does_not_treat_website_as_attractiveness():
    website_only = poi(
        1,
        description="",
        hours_weekly=None,
        duration_profile=None,
        website="https://example.org",
    )
    outdoor = poi(
        2,
        category="viewpoint",
        description="Điểm ngắm cảnh có mô tả nguồn",
        hours_weekly=None,
        duration_profile=None,
        website=None,
        access_points=[{"verified": True}],
    )
    assert not recommendation_eligible(website_only, "Đà Nẵng")
    assert recommendation_eligible(outdoor, "Đà Nẵng")


@pytest.mark.parametrize(
    "change", [{"radius_km": 0}, {"top_k": 21}, {"preset": "arbitrary"}, {"top_k": 2.5}]
)
def test_contract_rejects_invalid_inputs(change):
    with pytest.raises(ValueError):
        req(**change)


def test_metrics_do_not_treat_missing_grades_as_irrelevance():
    assert judged_metrics(["a"], {"a": 3}, ["a", "b"], 5)["precision"] is None
    result = judged_metrics(["a", "b"], {"a": 3, "b": 0}, ["a", "b"], 5)
    assert result["precision"] == 0.2 and result["ndcg"] == 1
    assert judged_metrics(["b", "a"], {"a": 3, "b": 0}, ["a", "b"], 5)["ndcg"] < 1
    assert judged_metrics(["a"], {"a": 0}, ["a"], 5)["ndcg"] is None
