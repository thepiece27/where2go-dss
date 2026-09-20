"""Reproducible POI ranking experiments and a blinded group-grading worksheet."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from where2go.routing import OSRM
from where2go.v2.catalog import load_catalog
from where2go.v2.ranking import RankingContext
from where2go.v2.recommendations import (
    METHODS,
    PRESETS,
    POLICY_VERSION,
    RecommendationRequest,
    prepare_candidates,
    recommendation_response,
)
from where2go.v2.recommendation_evaluation import judged_metrics


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate(output, geographic_only=False):
    scenarios_path = ROOT / "data/evaluation/v2_scenarios.json"
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))
    pois, manifest = load_catalog()
    context, router = RankingContext(pois), OSRM()
    results, grading, sensitivity, matrices = [], [], [], []
    rng = random.Random(20260919)
    for scenario in scenarios:
        req = RecommendationRequest.model_validate(
            {
                k: scenario[k]
                for k in (
                    "start",
                    "location",
                    "interests",
                    "preferred_categories",
                    "radius_km",
                )
            }
            | {"date": "2026-09-20"}
        )
        started = perf_counter()
        prepared = prepare_candidates(
            pois, manifest, req, router, context, geographic_only=geographic_only
        )
        preparation_seconds = perf_counter() - started
        common = {
            "scenario_id": scenario["scenario_id"],
            "split": scenario["split"],
            "travel_metric": prepared["travel_metric"],
            "eligible_count": prepared["eligible_count"],
            "candidate_count": prepared["candidate_count"],
            "request": req.model_dump(mode="json"),
        }
        matrices.append(
            common
            | {
                "rows": [
                    {
                        "poi_id": r["poi"]["poi_id"],
                        "category": r["poi"]["category"],
                        "values": r["values"],
                        "distance_km": r["distance_km"],
                    }
                    for r in prepared["rows"]
                ]
            }
        )
        pooled = {}
        for method in METHODS:
            started = perf_counter()
            data = recommendation_response(prepared, req, method)
            results.append(
                common
                | {
                    "method": method,
                    "items": data["items"],
                    "ranking": data["ranking"],
                    "preparation_seconds": preparation_seconds,
                    "scoring_seconds": perf_counter() - started,
                }
            )
            pooled.update({p["poi_id"]: p for p in data["items"]})
        grade_rows = [
            {
                "scenario_id": scenario["scenario_id"],
                "split": scenario["split"],
                "location": req.location,
                "date": req.date.isoformat(),
                "interests": ", ".join(req.interests),
                "categories": ", ".join(req.preferred_categories),
                "origin_latitude": req.start.latitude,
                "origin_longitude": req.start.longitude,
                "radius_km": req.radius_km,
                "poi_id": p["poi_id"],
                "name": p["name"],
                "category": p["category"],
                "description": next(
                    r["poi"].get("description", "")
                    for r in prepared["rows"]
                    if r["poi"]["poi_id"] == p["poi_id"]
                ),
                "distance_km": round(p["explanation"]["distance_km"], 3),
                "source_url": p.get("source_url") or "",
                "relevance_0_3": "",
                "notes": "",
            }
            for p in pooled.values()
        ]
        rng.shuffle(grade_rows)
        grading.extend(grade_rows)
        baseline = [
            p["poi_id"] for p in recommendation_response(prepared, req)["items"]
        ]
        for preset in PRESETS:
            changed = req.model_copy(update={"preset": preset})
            ids = [
                p["poi_id"] for p in recommendation_response(prepared, changed)["items"]
            ]
            sensitivity.append(
                common
                | {
                    "kind": "preset",
                    "value": preset,
                    "ids": ids,
                    "overlap_at_10": len(set(ids) & set(baseline))
                    / max(1, len(baseline)),
                }
            )
        # Pool-size sensitivity uses geographic costs for every compared size.
        geographic_base = prepare_candidates(
            pois, manifest, req, router, context, geographic_only=True
        )
        geo_ids = [
            p["poi_id"] for p in recommendation_response(geographic_base, req)["items"]
        ]
        sensitivity.append(
            common
            | {
                "kind": "travel_mode",
                "value": "geographic_distance",
                "ids": geo_ids,
                "overlap_at_10": len(set(geo_ids) & set(baseline))
                / max(1, len(baseline)),
            }
        )
        for size in (20, 40, 80):
            prepared_size = (
                geographic_base
                if size == 40
                else prepare_candidates(
                    pois,
                    manifest,
                    req,
                    router,
                    context,
                    pool_size=size,
                    geographic_only=True,
                )
            )
            ids = [
                p["poi_id"]
                for p in recommendation_response(prepared_size, req)["items"]
            ]
            sensitivity.append(
                common
                | {
                    "kind": "pool_size",
                    "value": size,
                    "travel_metric": "geographic_distance",
                    "candidate_count": prepared_size["candidate_count"],
                    "ids": ids,
                    "overlap_at_10": len(set(ids) & set(geo_ids))
                    / max(1, len(geo_ids)),
                }
            )
        print(
            f"{scenario['scenario_id']}: {prepared['candidate_count']} candidates, {prepared['travel_metric']}",
            flush=True,
        )
    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "dataset_version": manifest["version"],
        "policy_version": POLICY_VERSION,
        "scenario_sha256": hashlib.sha256(scenarios_path.read_bytes()).hexdigest(),
        "grading_design": "Group/owner case study, pooled top-10, relevance 0..3, binary relevance >=2; not independent users.",
        "recommendation_quality": "NOT GRADED",
        "geographic_only_requested": geographic_only,
    }
    dump(output / "evaluation.json", metadata | {"results": results})
    dump(output / "sensitivity.json", sensitivity)
    dump(output / "matrices.json", matrices)
    # A separate template is always safe to regenerate; never overwrite human grades.
    with (output / "grading_template.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(grading[0]))
        writer.writeheader()
        writer.writerows(grading)
    grade_hash = hashlib.sha256(
        (output / "grading_template.csv").read_bytes()
    ).hexdigest()
    dump(
        output / "grading_manifest.json",
        metadata
        | {
            "template_sha256": grade_hash,
            "evaluation_sha256": hashlib.sha256(
                (output / "evaluation.json").read_bytes()
            ).hexdigest(),
            "pool_ids": {
                row["scenario_id"]: sorted(
                    {
                        g["poi_id"]
                        for g in grading
                        if g["scenario_id"] == row["scenario_id"]
                    }
                )
                for row in scenarios
            },
        },
    )
    # A new pool invalidates metrics of the previous pool. Recompute explicitly
    # from the blank template; real owner labels live in a separate input file.
    grade(output, output / "grading_template.csv")
    return len(results)


def grade(output, path):
    payload = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (output / "grading_manifest.json").read_text(encoding="utf-8")
    )
    pools = manifest["pool_ids"]
    grades = {scenario: {} for scenario in pools}
    expected = {(scenario, ident) for scenario, ids in pools.items() for ident in ids}
    with (output / "grading_template.csv").open(
        encoding="utf-8-sig", newline=""
    ) as template_file:
        template = {
            (r["scenario_id"], r["poi_id"]): r for r in csv.DictReader(template_file)
        }
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = (row["scenario_id"], row["poi_id"])
            if key not in expected or key in seen:
                raise ValueError(
                    "Phiếu có ID lạ hoặc lặp; dùng template của đúng đợt đánh giá"
                )
            seen.add(key)
            if any(
                row.get(k) != v
                for k, v in template[key].items()
                if k not in ("relevance_0_3", "notes")
            ):
                raise ValueError(
                    "Ngữ cảnh/POI không khớp template; không dùng phiếu của đợt khác"
                )
            raw = row["relevance_0_3"].strip()
            if raw and raw not in {"0", "1", "2", "3"}:
                raise ValueError("Nhãn phải là số nguyên 0–3 hoặc để trống")
            grades[key[0]][key[1]] = int(raw) if raw else None
    rows = []
    for row in payload["results"]:
        ids = [p["poi_id"] for p in row["items"]]
        for k in (5, 10):
            rows.append(
                {
                    "scenario_id": row["scenario_id"],
                    "split": row["split"],
                    "method": row["method"],
                    "k": k,
                    **judged_metrics(
                        ids, grades[row["scenario_id"]], pools[row["scenario_id"]], k
                    ),
                }
            )
    dump(
        output / "quality_metrics.json",
        {
            "dataset_version": payload["dataset_version"],
            "policy_version": payload["policy_version"],
            "evaluation_sha256": hashlib.sha256(
                (output / "evaluation.json").read_bytes()
            ).hexdigest(),
            "labels_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "design": payload["grading_design"],
            "results": rows,
        },
    )


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/reports/recommendations"
    )
    parser.add_argument("--geographic-only", action="store_true")
    parser.add_argument(
        "--grades",
        type=Path,
        help="Only score an existing evaluation; do not rerun/reorder the pool",
    )
    args = parser.parse_args()
    if args.grades:
        grade(args.output, args.grades)
    else:
        print(
            f"Completed {evaluate(args.output, args.geographic_only)} runs; human grades remain blank."
        )


if __name__ == "__main__":
    main()
