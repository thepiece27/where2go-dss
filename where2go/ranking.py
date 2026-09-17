"""Three-criterion fuzzy AHP weights and crisp TOPSIS, shared by API/evaluation."""
import math
import re
import unicodedata
import numpy as np
from .config import CRITERIA, GAMMA, CATEGORY_TEXT


def normalize(text):
    value = str(text).lower().replace("đ", "d")
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFD", value).encode("ascii", "ignore").decode()))


def pairwise_matrix(p):
    a, b, c = (p.preference_over_drive_time, p.preference_over_data_confidence, p.drive_time_over_data_confidence)
    return np.array([[1, a, b], [1/a, 1, c], [1/b, 1/c, 1]], dtype=float)


def matrix_weights(matrix, gamma=GAMMA):
    a = np.asarray(matrix, dtype=float)
    if a.shape != (3, 3) or not np.isfinite(a).all() or (a <= 0).any():
        raise ValueError("Ma trận AHP phải là 3×3, hữu hạn và dương")
    if not np.allclose(np.diag(a), 1) or not np.allclose(a * a.T, 1):
        raise ValueError("Ma trận AHP phải có đường chéo 1 và reciprocal")
    if not math.isfinite(gamma) or gamma < 1:
        raise ValueError("gamma phải >= 1; gamma=1 là baseline crisp")
    eigenvalue = float(np.max(np.linalg.eigvals(a).real))
    cr = max(0.0, (eigenvalue - 3) / 2 / 0.58)
    if cr > 0.1 + 1e-10:
        raise ValueError(f"Phán đoán chưa nhất quán: CR={cr:.3f} > 0.1. Hãy sửa ưu tiên.")
    lower, upper = a / gamma, a * gamma
    np.fill_diagonal(lower, 1)
    np.fill_diagonal(upper, 1)
    gm = np.exp(np.log(np.stack([lower, a, upper], axis=2)).mean(axis=1))
    fuzzy = gm / gm.sum(axis=0)[::-1]
    crisp = fuzzy.mean(axis=1)
    return crisp / crisp.sum(), cr


def weights(pairwise, gamma=GAMMA):
    return matrix_weights(pairwise_matrix(pairwise), gamma)


def topsis(values, weight, benefits=(True, False, True)):
    a = np.asarray(values, dtype=float)
    w = np.asarray(weight, dtype=float)
    if a.ndim != 2 or a.shape[1] != len(w) or len(benefits) != len(w):
        raise ValueError("Invalid decision matrix dimensions")
    if not np.isfinite(a).all() or not np.isfinite(w).all() or (a < 0).any() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("Non-finite/negative decision values")
    if not len(a):
        return np.array([])
    norms = np.linalg.norm(a, axis=0)
    v = np.divide(a, norms, out=np.zeros_like(a), where=norms > 0) * (w / w.sum())
    best = np.where(benefits, v.max(axis=0), v.min(axis=0))
    worst = np.where(benefits, v.min(axis=0), v.max(axis=0))
    dp, dm = np.linalg.norm(v-best, axis=1), np.linalg.norm(v-worst, axis=1)
    return np.divide(dm, dp+dm, out=np.full(len(a), .5), where=(dp+dm) > 1e-12)


def preference(poi, interests):
    # Documented token recall, no synthetic behavior or template/source coordinates.
    wanted = set(normalize(" ".join(interests)).split())
    if not wanted:
        return 1.0
    tokens = set(normalize(" ".join([poi["name"], poi.get("description", ""),
                                   CATEGORY_TEXT.get(poi["category"], "")])).split())
    return len(wanted & tokens) / len(wanted)


def rank_pois(pois, durations_from_start, request, method="fuzzy"):
    w, cr = weights(request.pairwise_preferences, gamma=1 if method == "crisp" else GAMMA)
    values = [[preference(p, request.interests), float(t), p["data_confidence"]]
              for p, t in zip(pois, durations_from_start, strict=True)]
    if method == "nearby":
        scores = [-v[1] for v in values]
    elif method == "equal_sum":
        a = np.asarray(values, dtype=float)
        norms = np.linalg.norm(a, axis=0) if len(a) else np.ones(3)
        normalized = np.divide(a, norms, out=np.zeros_like(a), where=norms > 0)
        scores = normalized @ np.array([1, -1, 1]) / 3 if len(a) else []
    else:
        scores = topsis(values, w)
    ranked = [dict(p, score=float(score), criteria=dict(zip(CRITERIA, value)))
              for p, score, value in zip(pois, scores, values, strict=True)]
    return sorted(ranked, key=lambda p: (-p["score"], p["poi_id"])), {"weights": dict(zip(CRITERIA, map(float, w))), "cr": cr, "method": method}
