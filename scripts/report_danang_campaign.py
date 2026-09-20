"""Export campaign evidence and before/after coverage without claiming saturation."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from where2go.v2.catalog import load_catalog, CATALOG_V2
from where2go.v2.discovery import matches_scope, region_for, exclusion_reason
from where2go.v2.google_collector import google_identity
from where2go.v2.quality import recommendation_eligible
from scripts.crawl_danang import CAMPAIGN, read, save


def report(catalog):
    output = ROOT / "data/reports/v2/danang_campaign"
    baseline = read(output / "baseline.json", {})
    pois, manifest = load_catalog(catalog)
    scoped = [p for p in pois if matches_scope(p, "danang_hoian")]
    latest = {r["record_id"]:r for r in read(CAMPAIGN / "observations.json", [])}
    checkpoint = read(CAMPAIGN / "checkpoint.json", {})
    accepted = [r for r in latest.values() if r.get("accepted")]
    before = baseline.get("categories", {})
    after = Counter(p["category"] for p in scoped)
    coverage = []
    for category in sorted(set(before) | set(after)):
        group = [p for p in scoped if p["category"] == category]
        coverage.append({"category":category,"before":before.get(category,0),"after":len(group),
                         "delta":len(group)-before.get(category,0),"valid_image":sum(bool(p.get("image")) for p in group),
                         "rating_pair":sum(any(r["same_observation"] for r in p["ratings"]) for p in group),
                         "hours":sum(p.get("hours_weekly") is not None for p in group),
                         "recommendation_eligible":sum(recommendation_eligible(p) for p in group)})
    violations = [r["record_id"] for r in accepted if not google_identity(r["place"].get("google_maps_url"))
                  or not region_for(r["place"].get("latitude"), r["place"].get("longitude"))
                  or exclusion_reason(r["place"].get("name", ""), r["place"].get("category", ""))]
    summary = {"dataset_version":manifest["version"],"baseline_version":baseline.get("dataset_version"),
               "before_total":baseline.get("total"),"after_total":len(scoped),"coverage":coverage,
               "collection_status":checkpoint.get("status"),"saturated":checkpoint.get("status")=="saturated",
               "pilot":checkpoint.get("pilot"),"pilot_history":checkpoint.get("pilot_history",[]),
               "discovered":len(checkpoint.get("candidates",{})),"collected":len(latest),
               "accepted_observations":len(accepted),"accepted_unique_google_ids":len({google_identity(r["place"].get("google_maps_url")) for r in accepted}),
               "queries":dict(Counter(q["status"] for q in checkpoint.get("queries",[]))),
               "review_reasons":dict(Counter(r.get("review_reason") for r in latest.values() if not r.get("accepted"))),
               "policy_violations":violations,"scope_policy":"19 ward polygons; 25 m precision tolerance on six coastal wards; no inland boundary expansion"}
    save(output / "report.json",summary)
    fields = list(coverage[0])
    with (output / "coverage.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(coverage)
    from openpyxl import Workbook
    workbook = Workbook(); sheet = workbook.active; sheet.title = "coverage"
    sheet.append(fields)
    for row in coverage:
        sheet.append([row[k] for k in fields])
    sheet = workbook.create_sheet("observations")
    fields = ["name","category","accepted","review_reason","latitude","longitude","image","source_url","observed_at"]
    sheet.append(fields)
    exported = []
    for row in latest.values():
        p = row.get("place") or {}
        values = [p.get("name") or row["seed_name"],p.get("category"),row.get("accepted"),row.get("review_reason"),
                  p.get("latitude"),p.get("longitude"),p.get("image_url"),p.get("google_maps_url"),row.get("scraped_at")]
        # Spreadsheet values are data, never executable formulas.
        values = ["'"+v if isinstance(v,str) and v.startswith(("=","+","-","@")) else v for v in values]
        sheet.append(values); exported.append(dict(zip(fields,values)))
    private = ROOT / "data/private/danang_hoian"; private.mkdir(parents=True,exist_ok=True)
    workbook.save(private / "campaign.xlsx")
    with (private / "observations.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(exported)
    lines = ["# Kết quả tăng cường dữ liệu Đà Nẵng – Hội An", "", f"Catalog: `{manifest['version']}`.",
             f"Trạng thái crawl: **{summary['collection_status']}**. Đạt bão hòa: **{'có' if summary['saturated'] else 'chưa'}**.",
             f"Phạm vi: Đà Nẵng cũ, Hội An, Cù Lao Chàm; {len(scoped)} POI so với {baseline.get('total')} ở baseline.",
             "", "Các tổng catalog bao gồm dữ liệu cũ. Số quan sát không phải số địa điểm mới.",
             "", "| Loại | Trước | Sau | Chênh lệch | Ảnh hợp lệ | Đủ điều kiện gợi ý |", "|---|---:|---:|---:|---:|---:|"]
    lines += [f"| {r['category']} | {r['before']} | {r['after']} | {r['delta']} | {r['valid_image']} | {r['recommendation_eligible']} |" for r in coverage]
    lines += ["", "## Tính đầy đủ", "", f"Trạng thái truy vấn: `{summary['queries']}`.",
              f"Lý do chờ duyệt/loại: `{summary['review_reasons']}`.",
              "Không quy đổi kết quả Maps thành cam kết đã thu mọi điểm ngoài thực tế. Ảnh hợp lệ nghĩa là URL đã được kiểm tra nội dung và gắn với trang thực thể, không phải xác minh thực địa.",
              "", "## Tiếp tục và tái lập", "", "Xem `docs/thu_thap_danang_hoian.md`; checkpoint trong `data/enrichment/danang_hoian/`, CSV/XLSX quan sát trong `data/private/danang_hoian/`."]
    (output / "report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k not in {"coverage","pilot_history"}},ensure_ascii=False))
    if violations:
        raise RuntimeError("Campaign policy violations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog",type=Path,default=CATALOG_V2)
    report(parser.parse_args().catalog)
