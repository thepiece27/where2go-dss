"""Freeze the campaign boundary from the local ward snapshot and record baseline."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from collections import Counter
from shapely.geometry import mapping, shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.v2.catalog import load_catalog
from where2go.v2.discovery import SCOPE_PATH, matches_scope, regions


def main():
    source = ROOT / "data/vietnam_provinces_wards_geojson.zip"
    codes = {"20194", "20197", "20200", "20209", "20242", "20257", "20260", "20263", "20275", "20285", "20305", "20308", "20314", "20320", "20332", "20401", "20410", "20413", "20434"}
    features = []
    with zipfile.ZipFile(source) as archive:
        for name in archive.namelist():
            code = Path(name).name[:5]
            if "/48_da_nang/wards/" not in name or code not in codes:
                continue
            data = json.loads(archive.read(name))
            for feature in data["features"]:
                props = feature.setdefault("properties", {})
                props.update(ward_code=code, source_member=name, requires_boat=code == "20434",
                             region="cu_lao_cham" if code == "20434" else "hoi_an" if code.startswith("204") else "danang",
                             search_name="Hội An" if code.startswith("204") else "Đà Nẵng",
                             grid_km=5 if code in {"20308", "20320", "20332", "20194"} else 2)
                # Small coastal tolerance for entity markers placed on the sand/water edge.
                # Inland borders and Hai Van are not expanded.
                if code in {"20263", "20275", "20285", "20410", "20413", "20434"}:
                    props["coastal_precision_tolerance_m"] = 25
                    feature["geometry"] = mapping(shape(feature["geometry"]).buffer(25 / 111320))
                features.append(feature)
    assert {f["properties"]["ward_code"] for f in features} == codes
    scope = {"type": "FeatureCollection", "scope_id": "danang_hoian", "version": 2,
             "source": str(source.relative_to(ROOT)), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
             "boundary_method": "Union of 19 local snapshot wards covering old mainland Da Nang, Hoi An and Tan Hiep; excludes Hoang Sa and other former Quang Nam wards. Upstream origin of inherited snapshot not independently verified.",
             "features": features}
    SCOPE_PATH.write_text(json.dumps(scope, ensure_ascii=False), encoding="utf-8")
    regions.cache_clear()
    from where2go.v2.discovery import region_for
    region_for.cache_clear()
    pois, manifest = load_catalog()
    selected = [p for p in pois if matches_scope(p, "danang_hoian")]
    baseline = {"dataset_version": manifest["version"], "scope_sha256": hashlib.sha256(SCOPE_PATH.read_bytes()).hexdigest(),
                "total": len(selected), "categories": dict(Counter(p["category"] for p in selected)),
                "tourism_total": sum(matches_scope(p, "danang_hoian", True) for p in selected),
                "with_image": sum(bool(p.get("image")) for p in selected),
                "eligible": sum(p["itinerary_eligible"] for p in selected), "poi_ids": [p["poi_id"] for p in selected]}
    out = ROOT / "data/reports/v2/danang_campaign"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "baseline.json"
    if not path.exists():
        path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        prior = json.loads(path.read_text(encoding="utf-8"))
        if prior["dataset_version"] == baseline["dataset_version"] and prior["scope_sha256"] != baseline["scope_sha256"]:
            (out / "baseline_initial_boundary.json").write_text(json.dumps(prior, ensure_ascii=False, indent=2), encoding="utf-8")
            path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in baseline.items() if k != "poi_ids"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
