"""Pooled, owner-graded case-study metrics. Missing labels never mean irrelevant."""

import math


def judged_metrics(ids, grades, judged_pool, k):
    """Binary relevance >=2; graded NDCG denominator is the complete judged pool.

    Short lists keep denominator K for precision. NDCG is undefined with zero
    ideal gain, and both metrics are withheld while any pooled label is missing.
    """
    if not judged_pool or any(grades.get(i) is None for i in judged_pool):
        return {"precision": None, "ndcg": None, "status": "NOT GRADED"}
    if any(type(grades[i]) is not int or not 0 <= grades[i] <= 3 for i in judged_pool):
        raise ValueError("Relevance must be an integer from 0 to 3")
    if len(set(ids)) != len(ids) or not set(ids) <= set(judged_pool):
        raise ValueError("Ranking must contain unique IDs from the judged pool")
    values = [grades[i] for i in ids[:k]]
    dcg = sum((2**g - 1) / math.log2(j + 2) for j, g in enumerate(values))
    ideal = sorted((grades[i] for i in judged_pool), reverse=True)[:k]
    idcg = sum((2**g - 1) / math.log2(j + 2) for j, g in enumerate(ideal))
    return {
        "precision": sum(g >= 2 for g in values) / k,
        "ndcg": dcg / idcg if idcg else None,
        "status": "GRADED" if idcg else "NO RELEVANT ITEMS",
    }
