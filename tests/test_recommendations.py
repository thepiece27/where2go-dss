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
    p["rows"][0]["values"] = [0.95, 0.5, 600, 0.5]
    p["rows"][1]["values"] = [0.2, 0.5, 60, 0.5]
    assert score_candidates(p, req(preset="interests"))[0][0][0]["poi"]["poi_id"] == "1"
    assert score_candidates(p, req(preset="nearby"))[0][0][0]["poi"]["poi_id"] == "2"


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


def test_empty_ties_and_uniform_fuzzy():
    rows = [poi(1), poi(2)]
    r = req()
    p = prepare_candidates(rows, MANIFEST, r, Router(), RankingContext(rows))
    a, b = recommendation_response(p, r), recommendation_response(p, r, "fuzzy")
    assert [x["poi_id"] for x in a["items"]] == [x["poi_id"] for x in b["items"]]
    assert all(math.isfinite(x["score"]) for x in a["items"])
    empty = prepare_candidates(
        rows, MANIFEST, req(selected_poi_ids=["1", "2"]), Router(), RankingContext(rows)
    )
    assert recommendation_response(empty, r)["items"] == []


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
