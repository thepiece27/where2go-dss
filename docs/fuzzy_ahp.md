# Fuzzy AHP Knowledge Used In This Project

This document records the Fuzzy AHP method used by `poi_recommendation_system.ipynb`.

The current project uses Fuzzy AHP to weight a contextual hybrid decision matrix, then uses TOPSIS for the final ranking.

## 1. Decision Hierarchy

The recommendation problem is modeled as a multi-criteria decision problem.

```text
Goal
  Recommend the best point of interest (POI)

Criteria
  C1 = behavior
  C2 = content
  C3 = distance
  C4 = quality
  C5 = context

Alternatives
  A1, A2, ..., Am = cleaned POIs
```

The criteria are intentionally separated:

- `behavior`: popularity, association-rule, and item-CF score for known users; neutral for cold-start users
- `content`: TF-IDF + cosine score used for candidate generation and semantic preference matching
- `distance`: distance from the user's current coordinates
- `quality`: rating, reviews, image availability, opening-hour availability
- `context`: type, location, and content matching combined into `type_context_score`

This avoids double-counting type/location inside the content criterion.

## 2. AHP Pairwise Comparison Input

Let there be `n` criteria. The expert/user provides a pairwise comparison matrix:

```text
A = [a_ij], i,j = 1..n
```

Rules:

```text
a_ii = 1
a_ij > 0
a_ji = 1 / a_ij
```

The values follow Saaty's pairwise comparison idea:

```text
1 = equally important
2 = weakly/moderately more important in this implementation
3 = moderately more important
5 = strongly more important
7 = very strongly more important
9 = extremely more important
```

Intermediate values may be used when the expert's judgment is between two levels.

In the notebook, the pairwise matrix is an input:

```python
EXPERT_PAIRWISE_MATRIX = np.array([
    [1,   2,   3,   2,   1],
    [1/2, 1,   2,   1,   1/2],
    [1/3, 1/2, 1,   1/2, 1/3],
    [1/2, 1,   2,   1,   1/2],
    [1,   2,   3,   2,   1],
], dtype=float)
```

Criteria order:

```text
behavior, content, distance, quality, context
```

Important: the notebook does **not** create the pairwise matrix from preset weights. The pairwise matrix is the expert/user input, then AHP computes the weights.

## 3. Crisp AHP Weight Calculation

Given the pairwise matrix `A`, first compute the column sum:

```text
s_j = sum_i a_ij
```

Normalize each column:

```text
n_ij = a_ij / s_j
```

Compute the row mean as the crisp AHP weight:

```text
w_i = (1 / n) * sum_j n_ij
```

Normalize the weight vector:

```text
w_i = w_i / sum_k w_k
```

So the crisp AHP weight vector is:

```text
W = [w_1, w_2, ..., w_n]
```

## 4. AHP Consistency Check

AHP checks whether the pairwise judgments are consistent enough.

Weighted sum vector:

```text
v = A * W
```

Consistency vector:

```text
c_i = v_i / w_i
```

Largest eigenvalue approximation:

```text
lambda_max = (1 / n) * sum_i c_i
```

Consistency Index:

```text
CI = (lambda_max - n) / (n - 1)
```

Consistency Ratio:

```text
CR = CI / RI
```

`RI` is the random index table used in the notebook:

```text
n:  1    2    3     4     5     6     7     8     9     10
RI: 0.00 0.00 0.58  0.90  1.12  1.24  1.32  1.41  1.45  1.49
```

Decision rule:

```text
CR <= 0.10  accepted
CR >  0.10  revise expert judgments
```

The current matrix has:

```text
CR = 0.002964
```

So the judgments are accepted.

## 5. Triangular Fuzzy Numbers

The implementation represents a fuzzy number as a triangular fuzzy number:

```text
M = (l, m, u)
```

Where:

- `l` = lower bound
- `m` = modal / most likely value
- `u` = upper bound
- `l <= m <= u`

This encodes uncertainty around a crisp judgment.

## 6. Fuzzy Number Operations

For two positive triangular fuzzy numbers:

```text
M1 = (l1, m1, u1)
M2 = (l2, m2, u2)
```

Addition:

```text
M1 + M2 = (l1 + l2, m1 + m2, u1 + u2)
```

Multiplication:

```text
M1 * M2 = (l1 * l2, m1 * m2, u1 * u2)
```

Multiplication by a positive scalar `k`:

```text
k * M1 = (k*l1, k*m1, k*u1)
```

Reciprocal:

```text
1 / M1 = (1/u1, 1/m1, 1/l1)
```

Centroid defuzzification:

```text
defuzz(M1) = (l1 + m1 + u1) / 3
```

## 7. Convert Crisp Pairwise Values To Fuzzy Values

For a crisp pairwise value `a_ij`, the notebook creates a triangular fuzzy number using an uncertainty band `delta`.

Default:

```text
delta = 0.20
```

Formula:

```text
fuzzy(a_ij) = (a_ij * (1 - delta), a_ij, a_ij * (1 + delta))
```

For diagonal values:

```text
fuzzy(a_ii) = (1, 1, 1)
```

For reciprocal positions:

```text
fuzzy(a_ji) = (1/u_ij, 1/m_ij, 1/l_ij)
```

This creates a fuzzy pairwise matrix:

```text
F = [M_ij]
M_ij = (l_ij, m_ij, u_ij)
```

## 8. Fuzzy Criteria Weights

The notebook uses a Buckley-style fuzzy geometric mean.

For criterion `i`, compute the geometric mean of its fuzzy pairwise row:

```text
G_i = (M_i1 * M_i2 * ... * M_in)^(1/n)
```

Component-wise:

```text
G_i = (
  (product_j l_ij)^(1/n),
  (product_j m_ij)^(1/n),
  (product_j u_ij)^(1/n)
)
```

Let:

```text
sum_l = sum_i G_i.l
sum_m = sum_i G_i.m
sum_u = sum_i G_i.u
```

Normalize fuzzy weights:

```text
FW_i = (
  G_i.l / sum_u,
  G_i.m / sum_m,
  G_i.u / sum_l
)
```

The notebook also defuzzifies these fuzzy weights for reporting:

```text
dw_i = (FW_i.l + FW_i.m + FW_i.u) / 3
dw_i = dw_i / sum_k dw_k
```

The final ranking aggregation uses the fuzzy weights `FW_i`.

## 9. Criterion Scores Before Fuzzification

Every POI receives a crisp score in `[0, 1]` for each criterion.

### Content Criterion

The notebook builds TF-IDF vectors from content-only text:

```text
content_text = name + result_name + description + keywords
```

Content does not include type or location.

For a user query/profile:

```text
content_score_i = cosine(tfidf(query), tfidf(content_text_i))
```

Cosine similarity:

```text
cosine(x, y) = (x . y) / (||x|| * ||y||)
```

### Type Criterion

The type criterion uses fuzzy string matching between preferred types and POI type:

```text
type_score_i = max_t fuzzy_text_score(t, poi_type_i)
```

The fuzzy text score is:

```text
fuzzy_text_score(q, text) =
  max(ratio(q,text), partial_ratio(q,text), token_set_ratio(q,text)) / 100
```

If no preferred type is provided:

```text
type_score_i = 0
```

### Location Criterion

The location criterion is the same fuzzy matching idea, but against location text:

```text
location_score_i = max_l fuzzy_text_score(l, location_i)
```

If no preferred location is provided:

```text
location_score_i = 0
```

### Distance Criterion

Distance uses the Haversine formula.

Let:

```text
phi = latitude in radians
lambda = longitude in radians
R = 6371.0088 km
```

For user coordinate `(lat1, lon1)` and POI coordinate `(lat2, lon2)`:

```text
dphi = phi2 - phi1
dlambda = lambda2 - lambda1

a = sin(dphi/2)^2 + cos(phi1) * cos(phi2) * sin(dlambda/2)^2
c = 2 * atan2(sqrt(a), sqrt(1-a))
d = R * c
```

The distance score uses a decreasing ramp:

```text
distance_score_i = 1, if d_i <= 0
distance_score_i = 0, if d_i >= max_distance_km
distance_score_i = (max_distance_km - d_i) / max_distance_km, otherwise
```

If the profile has no current coordinate, every POI receives:

```text
distance_score_i = 1
```

### Quality Criterion

Rating is normalized:

```text
rating_norm_i = rating_i / 5
```

Review count is log-normalized:

```text
review_log_i = log(1 + review_count_i)
review_norm_i = minmax(review_log_i)
```

The quality score is:

```text
quality_score_i =
    0.55 * rating_norm_i
  + 0.35 * review_norm_i
  + 0.05 * has_image_i
  + 0.05 * has_hours_i
```

Where:

```text
has_image_i = 1 if image URL exists, else 0
has_hours_i = 1 if opening hours exist, else 0
```

## 10. Fuzzy Evaluation Matrix

Each crisp criterion score `x_ij` in `[0, 1]` is converted to a triangular fuzzy evaluation.

Default evaluation spread:

```text
s = 0.08
```

Formula:

```text
X_ij = (
  max(0, x_ij - s),
  x_ij,
  min(1, x_ij + s)
)
```

This produces the fuzzy evaluation matrix:

```text
X = [X_ij]
```

Where:

- row `i` = POI alternative
- column `j` = criterion
- value `X_ij` = triangular fuzzy score

## 11. Fuzzy AHP Aggregation

Let:

```text
X_ij = fuzzy evaluation of POI i on criterion j
FW_j = fuzzy weight of criterion j
```

The fuzzy aggregate score for POI `i` is:

```text
H_i = sum_j (X_ij * FW_j)
```

Component-wise:

```text
H_i.l = sum_j X_ij.l * FW_j.l
H_i.m = sum_j X_ij.m * FW_j.m
H_i.u = sum_j X_ij.u * FW_j.u
```

This is the `H = A x W` aggregation step from the Fuzzy AHP pipeline.

## 12. Defuzzification

The fuzzy aggregate score is converted into one crisp score using centroid defuzzification:

```text
fuzzy_ahp_score_i = (H_i.l + H_i.m + H_i.u) / 3
```

This raw score is retained as the defuzzified weighted matrix input to TOPSIS.

```text
TOPSIS computes the ideal best and ideal worst vectors:

```text
D_i+ = distance from the ideal best
D_i- = distance from the ideal worst
```

The final closeness coefficient is:

```text
topsis_score_i = D_i- / (D_i+ + D_i-)
```
```

If all scores are equal or invalid, the notebook returns `0.0` for the TOPSIS score.

## 13. Final Ranking Formula

The final score is:

```text
final_score_i = topsis_score_i
```

POIs are ranked by:

```text
final_score descending
contextual_score descending as tie-breaker
```

The final implementation ranks a behavior/content candidate pool after contextual scoring, rather than ranking the entire catalog with Fuzzy AHP alone.

## 14. Why This Is Fuzzy AHP

The implementation has the required structure:

```text
Hierarchy
  -> expert/user pairwise comparison matrix
  -> AHP criteria weights
  -> consistency check with CR
  -> fuzzy pairwise matrix
  -> fuzzy criteria weights
  -> fuzzy evaluation matrix
  -> aggregation H = A x W
  -> defuzzification
  -> TOPSIS ideal distances
  -> Top-K ranking
```

It is not just a manually weighted sum. The weights are computed from the pairwise comparison matrix, and the ranking uses fuzzy weights plus fuzzy evaluation scores before defuzzification.

## 15. Implementation Checklist

Use this checklist to verify the notebook:

```text
[x] Has goal, criteria, alternatives
[x] Has explicit pairwise comparison matrix input
[x] Computes AHP weights from the pairwise matrix
[x] Checks lambda_max, CI, CR
[x] Converts pairwise judgments to triangular fuzzy numbers
[x] Computes fuzzy criteria weights
[x] Builds fuzzy evaluation matrix
[x] Aggregates with H = A x W
[x] Defuzzifies fuzzy aggregate scores
[x] Computes TOPSIS ideal best/worst distances
[x] Sets final_score = topsis_score
[x] Ranks POIs by final_score
```
