"""Content criteria and ordinary AHP weights for the research planner."""
from datetime import date
import math
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from where2go.ranking import normalize, topsis
from .hours import intervals_on_date
from .intent import interpret_request, poi_concepts
from .models import CRITERIA


PAIR_ORDER = tuple((i, j) for i in range(4) for j in range(i + 1, 4))


def ahp_matrix(comparisons):
    matrix = np.ones((4, 4), dtype=float)
    for (i, j), value in zip(PAIR_ORDER, comparisons, strict=True):
        matrix[i, j] = value
        matrix[j, i] = 1 / value
    return matrix


def ahp_weights(comparisons):
    comparisons = np.asarray(comparisons, dtype=float)
    if comparisons.shape != (6,):
        raise ValueError("AHP v2 cần đúng sáu cặp phán đoán")
    if not np.isfinite(comparisons).all() or (comparisons <= 0).any():
        raise ValueError("Phán đoán AHP phải hữu hạn và dương")
    matrix = ahp_matrix(comparisons)
    eigenvalue = float(np.linalg.eigvals(matrix).real.max())
    cr = max(0.0, (eigenvalue - 4) / 3 / 0.90)
    if cr > 0.1 + 1e-10:
        raise ValueError(f"Phán đoán chưa nhất quán: CR={cr:.3f} > 0,1")
    geometric = np.exp(np.log(matrix).mean(axis=1))
    return geometric / geometric.sum(), cr


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
        # TF-IDF uses source-backed text. Category-derived tags are handled once
        # by the taxonomy component instead of being duplicated in this corpus.
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
        prior_basis = "location_category" if len(local) >= 10 else "category" if len(category) >= 10 else "provider"
        if not values:
            return 0.5, {"method": "neutral_no_rating_data", "observation": None,
                         "observed": False, "prior_basis": "none"}
        prior = float(np.mean(values))
        if current:
            score = (current["review_count"] * current["rating"] + m * prior) / (current["review_count"] + m)
            method = "bayesian_adjusted"
        else:
            # This is an explicit estimate, never presented as an observation.
            score, method = prior, "group_prior_missing_rating"
        return score / 5, {"method": method, "prior": prior, "prior_basis": prior_basis,
                           "m": m, "observation": current, "observed": current is not None}

    def preference_scores(self, pool, request):
        return {ident: detail["score"] for ident, detail in self.preference_components(pool, request).items()}

    def preference_components(self, pool, request, intent=None):
        intent = intent or interpret_request(request)
        wanted_concepts = set(intent.positive_concepts)
        preferred = set(intent.preferred_categories)
        if not intent.has_positive_intent:
            return {poi["poi_id"]: {"score": 1.0, "taxonomy": 0.0, "cosine": 0.0,
                    "category_match": False, "matched_concepts": [], "matched_tokens": [],
                    "has_evidence": True, "unspecified": True} for poi in pool}
        query_parts = [*intent.query_texts, *intent.positive_concepts]
        vector = self.vectorizer.transform([normalize(" ".join(query_parts)) or "unknown"])
        result = {}
        for poi in pool:
            concepts = poi_concepts(poi)
            matched = concepts & wanted_concepts
            category_match = poi["category"] in preferred
            concept_score = len(matched) / len(wanted_concepts) if wanted_concepts else 0.0
            taxonomy = max(concept_score, float(category_match))
            similarity = float((self.matrix[self.index[poi["poi_id"]]] @ vector.T).toarray()[0, 0])
            structured = bool(wanted_concepts or preferred)
            has_evidence = bool(matched or category_match or (intent.unmapped_texts and similarity > 1e-12))
            score = ((0.75 * taxonomy + 0.25 * similarity) if structured
                     else similarity)
            result[poi["poi_id"]] = {"score": score,
                    "taxonomy": taxonomy, "cosine": similarity,
                    "category_match": category_match,
                    "matched_concepts": sorted(matched),
                    "matched_tokens": sorted(matched),
                    "has_evidence": has_evidence, "unspecified": False}
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


def rank(pool, drive_times, request, context, method="ahp"):
    if method not in ("ahp", "nearby", "equal"):
        raise ValueError("Unknown planner ranking method")
    if len(pool) != len(drive_times):
        raise ValueError("Mỗi POI phải có một thời gian lái xe")
    weights, cr = ahp_weights(request.ahp.comparisons)
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
