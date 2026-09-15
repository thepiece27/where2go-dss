# POI Recommendation System

This document explains the current implementation in `poi_recommendation_system.ipynb`.

## Main Files

- Input workbook: `data/vietnam_destinations_google_maps_browser_hotosm.xlsx`
- Notebook: `poi_recommendation_system.ipynb`
- Cleaned recommendation dataset: `data/poi_recommendation_cleaned.xlsx`
- Sample recommendation result: `data/poi_sample_recommendations.xlsx`
- Evaluation metrics: `data/poi_evaluation_metrics.xlsx`
- Method reference: `docs/fuzzy_ahp.md`

## Current Modeling Decision

The final ranking model is **Fuzzy AHP only**.

The notebook still uses TF-IDF, fuzzy string matching, distance, ratings, reviews, image availability, and opening-hour availability. These are not separate final models. They are input criteria for Fuzzy AHP.

Final score:

```text
final_score = fuzzy_ahp_norm
```

If raw defuzzified scores are used directly in another experiment, the equivalent non-normalized form is:

```text
final_score = fuzzy_ahp_score
```

In the current notebook, `fuzzy_ahp_score` is normalized first, so `fuzzy_ahp_norm` is used.

## Data Fields Used

The notebook reads these important fields from the workbook:

- `Tên địa điểm`: POI name
- `Vị trí`: location text
- `Mô tả`: description
- `Đánh giá `: rating text
- `Ảnh`: image URL
- `Từ Khóa`: keywords
- `maps_latitude`, `maps_longitude`: coordinates
- `maps_destination_type`: Google Maps destination type
- `maps_review_count`, `maps_review_label`: popularity signals
- `maps_first_open_hours`, `maps_open_hours`: opening hours
- `maps_url`: Google Maps URL

## Phase 1: Data Inspection

The notebook inspects:

- row count
- column names and data types
- missing values
- duplicate names
- coordinate validity
- top destination types

Vietnam coordinate sanity check:

```text
7.0 <= latitude <= 24.5
102.0 <= longitude <= 110.5
```

Rows outside this box are treated as invalid for this Vietnam POI dataset.

## Phase 2: Cleaning

Rows are removed when:

- POI name is missing
- coordinate is missing or invalid
- coordinate is outside Vietnam bounds

Duplicates are removed by:

```text
duplicate_key = normalized_name + rounded_latitude + rounded_longitude
```

This prevents keeping the same POI multiple times after HOTOSM/Google Maps enrichment.

## Phase 3: Missing Data Handling

The notebook fills fields needed for recommendation:

- missing type -> `Unknown`
- missing location -> `Việt Nam`
- missing description -> `Điểm đến tại Việt Nam.`
- missing opening hours -> `Không rõ`

Ratings are parsed, clipped to `[0, 5]`, then filled by:

```text
destination-type median -> global median -> 3.5
```

Reviews are parsed from:

```text
maps_review_count -> maps_review_label -> 0
```

Keywords are cleaned into the project style:

```text
"biển" , "vui chơi" , "chụp ảnh"
```

When keywords are missing, the notebook infers simple keywords from type, description, and name.

## Phase 4: Normalization And Utility Functions

### Min-Max Normalization

```text
minmax(x_i) = (x_i - min(x)) / (max(x) - min(x))
```

If all values are equal or invalid:

```text
minmax(x_i) = 0
```

### Ramp Down

```text
ramp_down(x, low, high) = 1, if x <= low
ramp_down(x, low, high) = 0, if x >= high
ramp_down(x, low, high) = (high - x) / (high - low), otherwise
```

## Phase 5: Criteria Features

The Fuzzy AHP model uses five criteria:

```text
content, type, location, distance, quality
```

Content is separated from type and location to avoid double-counting.

Content text contains:

- POI name
- Google result name
- description
- keywords

Content text does not contain:

- destination type
- location text

## Phase 6: Criteria Score Functions

### Content Score

The notebook builds TF-IDF vectors and computes cosine similarity:

```text
content_score_i = cosine(tfidf(user_query), tfidf(content_text_i))
```

```text
cosine(x, y) = (x . y) / (||x|| * ||y||)
```

### Type Score

```text
type_score_i = max_t fuzzy_text_score(t, poi_type_i)
```

Where `t` is one preferred type from the user profile.

### Location Score

```text
location_score_i = max_l fuzzy_text_score(l, location_i)
```

Where `l` is one preferred location from the user profile.

### Fuzzy Text Score

```text
fuzzy_text_score(q, text) =
  max(ratio(q,text), partial_ratio(q,text), token_set_ratio(q,text)) / 100
```

The notebook uses `rapidfuzz` when installed and falls back to `difflib` otherwise.

### Distance Score

Distance is calculated with Haversine:

```text
a = sin(dphi/2)^2 + cos(phi1) * cos(phi2) * sin(dlambda/2)^2
d = 2 * R * atan2(sqrt(a), sqrt(1-a))
```

Then converted to score:

```text
distance_score_i = ramp_down(distance_i, 0, max_distance_km)
```

If no user coordinate is provided:

```text
distance_score_i = 1
```

### Quality Score

```text
rating_norm_i = rating_i / 5
review_log_i = log(1 + review_count_i)
review_norm_i = minmax(review_log_i)
```

```text
quality_score_i =
    0.55 * rating_norm_i
  + 0.35 * review_norm_i
  + 0.05 * has_image_i
  + 0.05 * has_hours_i
```

## Phase 7: Fuzzy AHP Ranking

Full mathematical details are in `docs/fuzzy_ahp.md`.

Short pipeline:

```text
expert/user pairwise matrix
  -> crisp AHP weights
  -> CR consistency check
  -> triangular fuzzy pairwise matrix
  -> fuzzy criteria weights
  -> fuzzy evaluation matrix
  -> H = A x W aggregation
  -> centroid defuzzification
  -> min-max normalization
  -> final ranking
```

Pairwise input:

```python
EXPERT_PAIRWISE_MATRIX = np.array([
    [1,   2,   3,   2,   1],
    [1/2, 1,   2,   1,   1/2],
    [1/3, 1/2, 1,   1/2, 1/3],
    [1/2, 1,   2,   1,   1/2],
    [1,   2,   3,   2,   1],
])
```

Criteria order:

```text
content, type, location, distance, quality
```

Consistency:

```text
CR = 0.002964 <= 0.10
```

Final score:

```text
final_score_i = fuzzy_ahp_norm_i
```

## User Profile Format

Example:

```python
user_profile = {
    "query": "di tich van hoa chup anh ngam canh",
    "keywords": ["van hoa", "di tich", "chup anh", "ngam canh"],
    "preferred_types": ["Tourist attraction", "Historical landmark", "Museum"],
    "preferred_locations": ["Khanh Hoa", "Nha Trang"],
    "current_lat": 12.2388,
    "current_lng": 109.1967,
    "max_distance_km": 120,
}
```

Run:

```python
recommend_pois(user_profile, top_k=15)
```

## Evaluation And Metrics

The workbook does not contain real user-click or user-rating labels. Evaluation therefore uses pseudo relevance labels generated from held-out user profiles.

The pseudo-relevance oracle is only for evaluation:

```text
oracle_i =
    0.25 * content_score_i
  + 0.15 * type_score_i
  + 0.15 * location_score_i
  + 0.20 * distance_score_i
  + 0.25 * quality_score_i
```

A POI is relevant if it is in the top 5% of oracle scores for that profile. If fewer than `K` items are relevant, the top `K` oracle items are marked relevant.

### Baselines

Baseline models compared with the main model:

- `popularity_baseline`: quality only
- `distance_baseline`: distance only
- `content_baseline`: content TF-IDF only
- `type_location_baseline`: type + location matching
- `equal_weight_baseline`: equal average of all criteria
- `crisp_ahp_weighted_baseline`: crisp AHP weighted score without fuzzy evaluation
- `fuzzy_ahp`: main model

### Metrics

Precision@K:

```text
Precision@K = relevant_items_in_top_K / K
```

Recall@K:

```text
Recall@K = relevant_items_in_top_K / total_relevant_items
```

Average Precision@K:

```text
AP@K = average of Precision@rank over ranks where a relevant item appears
```

Mean Average Precision@K:

```text
MAP@K = mean(AP@K over evaluation profiles)
```

Reciprocal Rank@K:

```text
RR@K = 1 / rank_of_first_relevant_item
```

If no relevant item appears in top `K`:

```text
RR@K = 0
```

Mean Reciprocal Rank@K:

```text
MRR@K = mean(RR@K over evaluation profiles)
```

Discounted Cumulative Gain@K:

```text
DCG@K = sum_i gain_i / log2(i + 1), i = 1..K
```

Normalized DCG@K:

```text
NDCG@K = DCG@K / IDCG@K
```

Type diversity@K:

```text
type_diversity@K = unique_destination_types_in_top_K / K
```

Catalog coverage@K:

```text
catalog_coverage@K = unique_recommended_items_across_profiles / total_items
```

## Outputs

`data/poi_recommendation_cleaned.xlsx` contains cleaned recommendation data.

`data/poi_sample_recommendations.xlsx` contains top recommendations from the example profile.

`data/poi_evaluation_metrics.xlsx` contains:

- `summary`: averaged metrics by model
- `by_profile`: metrics per evaluation profile
- `fuzzy_ahp_weights`: crisp AHP and fuzzy weights from the expert pairwise matrix

## Limitations

- Evaluation uses pseudo relevance, not real user feedback.
- The pairwise matrix should be reviewed by domain experts or real users.
- Google Maps scraped fields can contain wrong matches.
- Missing destination types reduce type matching quality.
- TF-IDF is simple and may miss semantic similarity.

## Possible Improvements

- Collect real clicks, saves, ratings, or itinerary choices.
- Let multiple experts provide pairwise matrices, then aggregate judgments.
- Add itinerary constraints such as time, budget, and travel route.
- Add diversity constraints so top results are not too similar.
- Replace TF-IDF with sentence embeddings for semantic content matching.
