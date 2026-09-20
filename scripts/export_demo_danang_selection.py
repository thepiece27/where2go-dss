"""Export compact, reviewable evidence and exact result tables for the demo guide."""

import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="artifacts/demo_selection_20260921")
    parser.add_argument("--output", default="data/reports/demo_danang_selection")
    parser.add_argument("--markdown", default="docs/demo_da_nang_2_kich_ban_chinh.md")
    args = parser.parse_args()
    source, out = Path(args.input), Path(args.output)
    screening = json.loads((source / "screening.json").read_text(encoding="utf-8"))
    browser = json.loads((source / "browser_report.json").read_text(encoding="utf-8"))
    assert browser["status"] == "PASS"
    assert screening["health_before"] == screening["health_after"], "Runtime changed during screening"
    out.mkdir(parents=True, exist_ok=True)
    cases = screening["cases"]
    versions = {c["response"]["dataset_version"] for c in cases}
    policies = {c["response"]["policy_version"] for c in cases}
    assert len(versions) == len(policies) == 1
    rows = []
    for c in cases:
        rows.append(dict(id=c["id"], request=json.dumps(c["request"], ensure_ascii=False),
                         summary=json.dumps(c["summary"], ensure_ascii=False),
                         top_ids=json.dumps([p["poi_id"] for p in c["response"]["items"]]),
                         top_names=json.dumps([p["name"] for p in c["response"]["items"]], ensure_ascii=False),
                         seconds=c["seconds"]))
    with (out / "screening.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = dict(screening_started_at=screening["started_at"],
                  screening_completed_at=screening["completed_at"],
                  browser_started_at=browser["started_at"],
                  health=screening["health_after"], policy_version=next(iter(policies)),
                  chromium=browser["chromium"], screening_count=len(cases),
                  unique_requests=len({json.dumps(c["request"], sort_keys=True) for c in cases}),
                  one_field_comparisons=len(screening["comparisons"]),
                  browser_steps=sum(len(j["steps"]) for j in browser["journeys"]),
                  browser_repeats=sum(j["repeat_same_order"] for j in browser["journeys"]),
                  status=browser["status"], journeys=[])
    appendix = ["## 9. Phụ lục: toàn bộ POI hiển thị, không lược các kết quả yếu", "",
                "Các bảng dưới được xuất từ phản hồi đã đối chiếu với UI. Tên giống hoặc gần nhau vẫn được giữ; số thay đổi ở phần chính so theo **ID**, không so chuỗi tên. Ký hiệu ‘—’ là không còn kết quả ở hạng đó.", ""]
    for i, journey in enumerate(browser["journeys"], 1):
        compact = dict(id=journey["id"], javascript_errors=journey["javascript_errors"],
                       repeat_same_order=journey["repeat_same_order"], steps=[])
        for step in journey["steps"]:
            assert step["response"]["dataset_version"] in versions
            assert step["response"]["policy_version"] in policies
            compact["steps"].append(dict(id=step["id"], request=step["request"],
                summary=step["summary"], checks=step["checks"], difference=step.get("difference"),
                ranking=step["response"]["ranking"], filter_message=step["response"].get("filter_message"),
                items=[{k: p[k] for k in ("poi_id", "name", "category", "latitude", "longitude", "rank", "score", "criteria", "reasons", "warnings", "explanation", "source_url")} for p in step["response"]["items"]]))
        result["journeys"].append(compact)
        steps = journey["steps"]
        letters = [chr(65+n) for n in range(len(steps))]
        appendix.extend([f"### K{i}: thứ tự đầy đủ", "",
                         "| Hạng | " + " | ".join(f"K{i}-{letter}" for letter in letters) + " |",
                         "| ---: | " + " | ".join("---" for _ in letters) + " |"])
        for rank in range(max(len(s["response"]["items"]) for s in steps)):
            names = [s["response"]["items"][rank]["name"].replace("|", "\\|") if rank < len(s["response"]["items"]) else "—" for s in steps]
            appendix.append(f"| {rank+1} | " + " | ".join(names) + " |")
        appendix.extend(["", "| Bước | Đủ điều kiện / ứng viên | Kết quả | POI khớp sở thích bằng 0 | Cách đo chi phí |", "| --- | ---: | ---: | ---: | --- |"])
        for letter, step in zip(letters, steps, strict=True):
            s = step["summary"]
            metric = "Thời gian OSRM" if s["travel_metric"] == "road_time" else "Khoảng cách đường chim bay"
            appendix.append(f"| K{i}-{letter} | {s['eligible']} / {s['candidates']} | {s['count']} | {s['zero_match']} | {metric} |")
        appendix.append("")
    (out / "selected_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    document = Path(args.markdown)
    original = document.read_text(encoding="utf-8")
    begin, end = "<!-- GENERATED_RESULTS_START -->", "<!-- GENERATED_RESULTS_END -->"
    prefix, rest = original.split(begin, 1)
    _, suffix = rest.split(end, 1)
    document.write_text(prefix + begin + "\n\n" + "\n".join(appendix) + "\n" + end + suffix, encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "screening_count", "unique_requests", "one_field_comparisons", "browser_steps", "browser_repeats")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
