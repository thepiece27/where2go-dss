"""Metrics use independent judgments over the complete judged candidate set."""
import math


def metrics(ranked_ids, relevance, k=10):
    if k < 1:
        raise ValueError("k must be positive")
    if len(ranked_ids) != len(set(ranked_ids)):
        raise ValueError("Duplicate recommendation IDs")
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 3 for v in relevance.values()):
        raise ValueError("Invalid relevance labels")
    top = ranked_ids[:k]
    relevant = sum(v > 0 for v in relevance.values())
    hits = 0
    ap = rr = dcg = 0.0
    for rank, ident in enumerate(top, 1):
        grade = relevance.get(ident, 0)
        if grade > 0:
            hits += 1
            ap += hits/rank
            if not rr:
                rr = 1/rank
        dcg += (2**grade - 1) / math.log2(rank+1)
    ideal = sum((2**grade-1)/math.log2(rank+1) for rank, grade in enumerate(sorted(relevance.values(), reverse=True)[:k], 1))
    return {"ap": ap/min(k, relevant) if relevant else 0, "ndcg": dcg/ideal if ideal else 0,
            "recall": hits/relevant if relevant else 0, "mrr": rr, "hit_rate": float(hits > 0)}


def global_time_split(events, cutoff):
    return [e for e in events if e["timestamp"] < cutoff], [e for e in events if e["timestamp"] >= cutoff]
