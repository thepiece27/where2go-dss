"""Four-criterion Fuzzy AHP and TOPSIS shared by API and evaluator."""
from datetime import date
import math
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from where2go.ranking import normalize, topsis
from .hours import intervals_on_date
from .models import CRITERIA
from .taxonomy import CATEGORY_TAGS


PAIR_ORDER = tuple((i, j) for i in range(4) for j in range(i + 1, 4))


def ahp_matrix(comparisons):
    matrix = np.ones((4, 4), dtype=float)
    for (i, j), value in zip(PAIR_ORDER, comparisons, strict=True):
        matrix[i, j] = value
        matrix[j, i] = 1 / value
    return matrix


def fuzzy_matrix(comparisons, uncertainty):
    crisp = ahp_matrix(comparisons)
    gamma = np.ones((4, 4), dtype=float)
    for (i, j), value in zip(PAIR_ORDER, uncertainty, strict=True):
        gamma[i, j] = gamma[j, i] = value
    lower, upper = crisp / gamma, crisp * gamma
    np.fill_diagonal(lower, 1)
    np.fill_diagonal(upper, 1)
    return lower, crisp, upper


def ahp_weights(comparisons, uncertainty=None):
    comparisons = np.asarray(comparisons, dtype=float)
    uncertainty = np.ones(6) if uncertainty is None else np.asarray(uncertainty, dtype=float)
    if comparisons.shape != (6,) or uncertainty.shape != (6,):
        raise ValueError("AHP v2 cần đúng sáu cặp phán đoán")
    if not np.isfinite(comparisons).all() or (comparisons <= 0).any():
        raise ValueError("Phán đoán AHP phải hữu hạn và dương")
    if not np.isfinite(uncertainty).all() or (uncertainty < 1).any():
        raise ValueError("Bất định fuzzy phải hữu hạn và >= 1")
    lower, crisp, upper = fuzzy_matrix(comparisons, uncertainty)
    eigenvalue = float(np.linalg.eigvals(crisp).real.max())
    cr = max(0.0, (eigenvalue - 4) / 3 / 0.90)
    if cr > 0.1 + 1e-10:
        raise ValueError(f"Phán đoán chưa nhất quán: CR={cr:.3f} > 0,1")
    geometric = np.stack((lower, crisp, upper), axis=2)
    row_means = np.exp(np.log(geometric).mean(axis=1))
    fuzzy_weights = row_means / row_means.sum(axis=0)[::-1]
    result = fuzzy_weights.mean(axis=1)
    result /= result.sum()
    return result, cr


def valid_rating(poi):
    rows = [row for row in poi.get("ratings", [])
            if row.get("same_observation")
            and isinstance(row.get("rating"), (int, float)) and math.isfinite(row["rating"])
            and 1 <= row["rating"] <= 5
            and isinstance(row.get("review_count"), int) and row["review_count"] >= 0]
    return max(rows, key=lambda row: row.get("observed_at") or "") if rows else None


class RankingContext:
    def __init__(self, pois):
        self.pois = pois
        self.index = {poi["poi_id"]: index for index, poi in enumerate(pois)}
        corpus = [normalize(" ".join([poi["name"], *poi.get("aliases", []), poi.get("description", "")])) or "unknown"
                  for poi in pois]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=20000)
        self.matrix = self.vectorizer.fit_transform(corpus)
        self.rated = [(poi, valid_rating(poi)) for poi in pois if valid_rating(poi)]

    def adjusted_quality(self, poi, m=50):
        current = valid_rating(poi)
        provider = current["provider"] if current else "Google Maps"
        rows = [(candidate, rating) for candidate, rating in self.rated if rating["provider"] == provider]
        local = [rating["rating"] for candidate, rating in rows
                 if candidate["category"] == poi["category"] and candidate["location"] == poi["location"]]
        category = [rating["rating"] for candidate, rating in rows if candidate["category"] == poi["category"]]
        values = local if len(local) >= 10 else category if len(category) >= 10 else [rating["rating"] for _, rating in rows]
        if not values:
            return 0.5, {"method": "neutral_no_rating_data", "observation": None}
        prior = float(np.mean(values))
        if current:
            score = (current["review_count"] * current["rating"] + m * prior) / (current["review_count"] + m)
            method = "bayesian_adjusted"
        else:
            # Missing data is not evidence that a place has average quality.
            # Keep the criterion neutral while retaining the provider prior in
            # the explanation for audit/debugging.
            score, method = 2.5, "neutral_missing_rating"
        return score / 5, {"method": method, "prior": prior, "m": m, "observation": current}

    def preference_scores(self, pool, request):
        wanted = set(normalize(" ".join(request.interests)).split())
        if not wanted and not request.preferred_categories:
            return {poi["poi_id"]: 1.0 for poi in pool}
        query_parts = list(request.interests)
        for category in request.preferred_categories:
            query_parts.extend(CATEGORY_TAGS[category])
        vector = self.vectorizer.transform([normalize(" ".join(query_parts)) or "unknown"])
        result = {}
        for poi in pool:
            tags = set(normalize(" ".join(poi.get("tags", []) + list(CATEGORY_TAGS.get(poi["category"], ())))).split())
            taxonomy = len(tags & wanted) / len(wanted) if wanted else 0.0
            if poi["category"] in request.preferred_categories:
                taxonomy = 1.0
            similarity = float((self.matrix[self.index[poi["poi_id"]]] @ vector.T).toarray()[0, 0])
            result[poi["poi_id"]] = 0.7 * taxonomy + 0.3 * similarity
        return result


def confidence(poi, request_date):
    access_verified = any(point.get("verified") for point in poi.get("access_points", []))
    hours_known = intervals_on_date(poi.get("hours_weekly"), poi.get("hours_exceptions"), request_date) is not None
    checked = poi.get("activity_checked_at")
    try:
        recent = bool(checked) and 0 <= (request_date - date.fromisoformat(checked[:10])).days <= 180
    except (TypeError, ValueError):
        recent = False
    evidence = {
        "identity": bool(poi.get("entity_confirmed")), "access": access_verified,
        "hours": hours_known, "recent_activity": recent,
    }
    return sum(evidence.values()) / len(evidence), evidence


def rank(pool, drive_times, request, context, method="fuzzy"):
    if len(pool) != len(drive_times):
        raise ValueError("Mỗi POI phải có một thời gian lái xe")
    uncertainty = [1.0] * 6 if method == "crisp" else request.ahp.uncertainty
    weights, cr = ahp_weights(request.ahp.comparisons, uncertainty)
    if method == "equal":
        weights = np.full(4, 0.25)
    preference = context.preference_scores(pool, request)
    values, explanations = [], []
    for poi, drive_time in zip(pool, drive_times, strict=True):
        if not isinstance(drive_time, (int, float)) or not math.isfinite(drive_time) or drive_time < 0:
            raise ValueError("Thời gian OSRM không hợp lệ")
        quality, rating_detail = context.adjusted_quality(poi)
        data_confidence, evidence = confidence(poi, request.date)
        criteria = [preference[poi["poi_id"]], quality, float(drive_time), data_confidence]
        values.append(criteria)
        explanations.append({"rating": rating_detail, "confidence_evidence": evidence})
    if method == "nearby":
        drive = np.asarray(drive_times, dtype=float)
        spread = float(drive.max() - drive.min()) if len(drive) else 0.0
        scores = np.ones(len(drive)) if spread <= 1e-12 else 1 - (drive - drive.min()) / spread
    else:
        scores = topsis(values, weights, (True, True, False, True))
    ranked = [dict(poi, score=float(score), criteria=dict(zip(CRITERIA, criteria)), explanation=explanation)
              for poi, score, criteria, explanation in zip(pool, scores, values, explanations, strict=True)]
    ranked.sort(key=lambda poi: (-poi["score"], poi["poi_id"]))
    return ranked, {"method": method, "criteria_order": list(CRITERIA),
                    "weights": dict(zip(CRITERIA, map(float, weights))), "cr": cr}
