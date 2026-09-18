import numpy as np
import pytest

from where2go.v2.models import AHPPreferences, ItineraryRequestV2, DEFAULT_COMPARISONS
from where2go.v2.ranking import PAIR_ORDER, RankingContext, ahp_matrix, ahp_weights, rank


def poi(ident, category="museum", rating=None, count=None):
    ratings = [] if rating is None else [{
        "provider": "Google Maps", "rating": rating, "review_count": count,
        "observed_at": "2026-09-16T00:00:00+00:00", "same_observation": count is not None,
    }]
    return {
        "poi_id": ident, "name": f"Địa điểm {ident}", "aliases": [], "description": "lịch sử văn hóa",
        "location": "Hà Nội", "category": category, "tags": ["lịch sử", "văn hóa"],
        "data_status": "usable", "entity_confirmed": True, "business_status": "open",
        "access_points": [{"verified": True}], "hours_weekly": [[(480, 1020)]] * 7,
        "hours_exceptions": {}, "ratings": ratings, "activity_checked_at": "2026-09-01",
    }


def request(**changes):
    payload = {
        "start": {"latitude": 21.03, "longitude": 105.85}, "date": "2026-09-17",
        "interests": ["lịch sử"], "preferred_categories": ["museum"],
    }
    payload.update(changes)
    return ItineraryRequestV2.model_validate(payload)


def upper_values(matrix):
    return [float(matrix[i, j]) for i, j in PAIR_ORDER]


def test_default_ahp_is_consistent_and_permutation_invariant():
    base, cr = ahp_weights(DEFAULT_COMPARISONS, [1.2] * 6)
    assert cr < 1e-9
    permutation = [2, 0, 3, 1]
    crisp = ahp_matrix(DEFAULT_COMPARISONS)
    permuted = crisp[np.ix_(permutation, permutation)]
    weights, permuted_cr = ahp_weights(upper_values(permuted), [1.2] * 6)
    assert permuted_cr < 1e-9
    assert np.allclose(weights, base[permutation])


def test_uniform_fuzzy_uncertainty_has_same_weights_as_crisp_ahp():
    crisp, _ = ahp_weights(DEFAULT_COMPARISONS, [1.0] * 6)
    fuzzy, _ = ahp_weights(DEFAULT_COMPARISONS, [1.2] * 6)
    assert np.allclose(fuzzy, crisp)


def test_inconsistent_ahp_is_rejected_by_request_validation():
    with pytest.raises(ValueError, match="CR="):
        AHPPreferences(comparisons=[9, 9, 1 / 9, 9, 1 / 9, 9])


def test_bayesian_rating_shrinks_small_sample_more():
    rows = [poi("prior-a", rating=4.0, count=100), poi("prior-b", rating=4.0, count=100),
            poi("few", rating=5.0, count=1), poi("many", rating=5.0, count=1000)]
    context = RankingContext(rows)
    few, _ = context.adjusted_quality(rows[2])
    many, _ = context.adjusted_quality(rows[3])
    assert 0.8 < few < many < 1.0


def test_rank_handles_constant_columns_and_drive_is_cost():
    rows = [poi("near"), poi("far")]
    context = RankingContext(rows)
    ranked, info = rank(rows, [60, 600], request(interests=[], preferred_categories=[]), context, method="equal")
    assert ranked[0]["poi_id"] == "near"
    assert all(np.isfinite(item["score"]) for item in ranked)
    assert tuple(info["criteria_order"]) == ("preference_match", "place_quality", "drive_time", "data_confidence")


def test_missing_rating_is_neutral_and_not_displayed_as_invented_observation():
    rows = [poi("rated", rating=4.5, count=100), poi("missing")]
    context = RankingContext(rows)
    score, detail = context.adjusted_quality(rows[1])
    assert score == 0.5
    assert detail["method"] == "neutral_missing_rating"
    assert detail["prior"] == 4.5
    assert detail["observation"] is None
