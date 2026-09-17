"""Run fixed, independently written scenarios through the same pipeline as the API."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.catalog import load_catalog
from where2go.models import ItineraryRequest
from where2go.planner import plan_itinerary
from where2go.routing import OSRM
from where2go.evaluation import metrics


SCENARIOS = [
    ("hanoi_hoan_kiem", "Hà Nội", 21.0285, 105.8542, ["văn hóa", "lịch sử"]),
    ("hanoi_west_lake", "Hà Nội", 21.0437, 105.8364, ["thiên nhiên", "văn hóa"]),
    ("danang_center", "Đà Nẵng", 16.0612, 108.2227, ["văn hóa", "ngắm cảnh"]),
    ("quangnam_hoi_an", "Đà Nẵng", 15.8794, 108.3278, ["văn hóa", "lịch sử"]),
]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judgments", type=Path, help="Independent JSON: scenario -> POI ID -> relevance 0..3")
    parser.add_argument("--output", type=Path, default=Path("data/reports/evaluation.json"))
    args=parser.parse_args()
    pois,manifest=load_catalog()
    router=OSRM()
    judgments=json.loads(args.judgments.read_text(encoding="utf-8")) if args.judgments else {}
    results=[]
    for name,city,lat,lon,interests in SCENARIOS:
        request=ItineraryRequest(start={"latitude":lat,"longitude":lon},date="2026-09-20",location=city,interests=interests)
        for method in ("nearby","equal_sum","crisp","fuzzy"):
            result=plan_itinerary(pois,manifest,request,router,method)
            ids=[p["poi_id"] for p in result.get("ranked_candidates",[])]
            if name in judgments and not set(ids).issubset(judgments[name]):
                raise ValueError(f"{name}: cần nhãn độc lập cho toàn bộ pool ứng viên; không coi điểm chưa chấm là không liên quan")
            evaluation=metrics(ids,judgments[name]) if name in judgments else None
            results.append({"scenario":name,"request":request.model_dump(mode="json"),"method":method,
                            "metrics":evaluation,"result":result})
            print(name,method,result["status"],len(result["stops"]),flush=True)
    report={"type":"case_study_without_user_labels" if not judgments else "independent_judgments",
            "dataset_version":manifest["version"],"results":results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if any(r["result"]["status"] not in ("ready","provisional") for r in results):
        raise SystemExit("One or more live scenarios did not pass; inspect report")


if __name__=="__main__": main()
