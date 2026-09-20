"""Run discovery, then validate images and publish an audited campaign snapshot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from where2go.config import ROOT
from scripts.crawl_danang import CAMPAIGN, CampaignLock, Reviewer, read, save, export
from scripts.validate_images_v2 import check_image


def command(script, *args):
    subprocess.run([sys.executable,"-X","utf8",str(ROOT / "scripts" / script),*map(str,args)],cwd=ROOT,check=True)


def finalize(analysis=True):
    state = read(CAMPAIGN / "checkpoint.json", {})
    if state.get("status") == "running":
        raise RuntimeError("Crawler still running; pause it before publishing a consistent snapshot")
    rows = read(CAMPAIGN / "observations.json", [])
    reviewer = Reviewer()
    latest = {r["record_id"]:r for r in rows}
    reviewed = [reviewer.review(dict(r)) for r in latest.values()]
    rows.extend(reviewed); save(CAMPAIGN / "observations.json", rows)
    export(rows,state)
    accepted = [r for r in reviewed if r["accepted"]]
    if not accepted:
        raise RuntimeError("No accepted observations to publish")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = ROOT / "artifacts/danang-snapshots" / stamp
    archive.mkdir(parents=True)
    for path in [CAMPAIGN / "checkpoint.json", CAMPAIGN / "observations.json", ROOT / "data/enrichment/accepted-danang-hoian.json"]:
        shutil.copy2(path,archive / path.name)
    cache_path = ROOT / "data/cache/image_checks_v2.json"
    cache = read(cache_path,{})
    urls = {u for r in accepted for u in [r["place"].get("image_url"),*r["place"].get("image_urls",[])] if u}
    pending = sorted(u for u in urls if u not in cache or cache[u]["status"] != "valid")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(check_image,pending):
            cache[result["url"]] = result
    save(cache_path,cache)
    print(json.dumps({"campaign_images":len(urls),"checked":len(pending),"valid":sum(cache[u]["status"]=="valid" for u in urls)}),flush=True)
    command("rebuild_dataset_v2.py","--publish")
    command("report_danang_campaign.py")
    report = read(ROOT / "data/reports/v2/danang_campaign/report.json",{})
    version = report["dataset_version"]
    # Keep all prior evaluations/labels before creating artifacts for the new snapshot.
    if analysis:
        for relative in ("data/reports/recommendations", "data/reports/analysis"):
            source = ROOT / relative
            if source.exists():
                shutil.copytree(source,archive / source.name)
        for relative in ("data/reports/v2/evaluation.json", "data/reports/v2/trip_choices_evaluation.json", "data/manual/v2_owner_grading.xlsx"):
            source = ROOT / relative
            if source.exists():
                shutil.copy2(source,archive / source.name)
        command("evaluate_v2.py")
        command("evaluate_trip_choices.py")
        command("evaluate_recommendations.py")
        import nbformat
        path = ROOT / "notebooks/phan_tich_du_lieu_poi.ipynb"
        notebook = nbformat.read(path,as_version=4)
        today = datetime.now(timezone.utc).date()
        for cell in notebook.cells:
            if cell.cell_type == "code":
                import re
                cell.source = re.sub(r"REFERENCE_DATE = date\(\d+, \d+, \d+\)",f"REFERENCE_DATE = date({today.year}, {today.month}, {today.day})",cell.source)
        if not any("CAMPAIGN_COVERAGE" in c.source for c in notebook.cells):
            notebook.cells.append(nbformat.v4.new_markdown_cell("## Tăng cường Đà Nẵng – Hội An\n\nPhân bố trước/sau trong phạm vi crawl; kết quả chưa đạt bão hòa không được coi là danh mục đầy đủ."))
            notebook.cells.append(nbformat.v4.new_code_cell('''# CAMPAIGN_COVERAGE
campaign = json.loads((ROOT / "data/reports/v2/danang_campaign/report.json").read_text(encoding="utf-8"))
assert campaign["dataset_version"] == summary["dataset_version"]
campaign_coverage = pd.DataFrame(campaign["coverage"])
display(Markdown(f"Trạng thái crawl: **{campaign['collection_status']}**; bão hòa: **{campaign['saturated']}**."))
display(campaign_coverage)
ax = campaign_coverage.set_index("category")[["before", "after"]].plot.bar(figsize=(14, 5), logy=True)
ax.set_title("Đà Nẵng – Hội An: phân bố trước và sau (trục log)")
ax.set_ylabel("Số POI")
plt.tight_layout()
plt.savefig(ROOT / "docs/assets/poi/danang_campaign_coverage.png", dpi=160)
plt.show()
'''))
        nbformat.write(notebook,path)
        command("run_analysis.py")
    banner = (f"> Dữ liệu đang phục vụ: `{version}`. Đợt Đà Nẵng–Hội An có trạng thái **{report['collection_status']}**, "
              f"{report['after_total']} POI trong phạm vi (bao gồm dữ liệu cũ). "
              "Các số liệu baseline bên dưới vẫn là kết quả lịch sử của snapshot được ghi kèm; "
              "xem báo cáo chiến dịch và notebook đã cập nhật để đối chiếu snapshot mới.\n\n")
    for relative, link in [("README.md","data/reports/v2/danang_campaign/report.md"),
                           ("docs/bao_cao_du_an_poi.md","../data/reports/v2/danang_campaign/report.md"),
                           ("docs/kich_ban_bao_ve.md","../data/reports/v2/danang_campaign/report.md")]:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        start,end = "<!-- DANANG_CURRENT_START -->", "<!-- DANANG_CURRENT_END -->"
        block = f"{start}\n{banner}[Báo cáo chiến dịch hiện tại]({link})\n{end}\n\n"
        if start in text:
            a,b = text.index(start),text.index(end)+len(end)
            text = text[:a]+text[b:].lstrip("\n")
        path.write_text(block+text,encoding="utf-8")
    save(ROOT / "data/reports/v2/danang_campaign/pipeline.json",{"status":"published","dataset_version":version,
         "collection_status":state.get("status"),"analysis":"PASS" if analysis else "NOT_RUN","archive":str(archive)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize-only",action="store_true")
    parser.add_argument("--skip-analysis",action="store_true")
    parser.add_argument("--max-queries",type=int,default=0)
    parser.add_argument("--background",action="store_true",help="Launch a detached worker and save its PID/log in artifacts")
    args = parser.parse_args()
    if args.background:
        # Verify that no collector/publisher currently owns this campaign.
        with CampaignLock():
            pass
        log_path = ROOT / "artifacts/danang_campaign.log"
        log_path.parent.mkdir(parents=True,exist_ok=True)
        child_args = [sys.executable,"-X","utf8",str(Path(__file__).resolve()),"--max-queries",str(args.max_queries)]
        if args.finalize_only:
            child_args.append("--finalize-only")
        if args.skip_analysis:
            child_args.append("--skip-analysis")
        options = {"creationflags":subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session":True}
        with log_path.open("a",encoding="utf-8") as log:
            worker = subprocess.Popen(child_args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,**options)
        info = {"pid":worker.pid,"log":str(log_path),"started_at":datetime.now(timezone.utc).isoformat()}
        save(ROOT / "artifacts/danang_campaign_worker.json",info)
        print(json.dumps(info),flush=True)
        return
    if not args.finalize_only:
        command("crawl_danang.py","--max-queries",args.max_queries)
    try:
        with CampaignLock():
            finalize(not args.skip_analysis)
    except Exception as error:
        save(ROOT / "data/reports/v2/danang_campaign/pipeline_error.json",{"error":str(error),"at":datetime.now(timezone.utc).isoformat()})
        raise


if __name__ == "__main__":
    main()
