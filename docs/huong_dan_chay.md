# Hướng dẫn chạy, phân tích và bảo trì Where2Go DSS

Các lệnh dưới đây chạy từ **thư mục gốc dự án**, bằng PowerShell trên Windows. Môi trường đã kiểm tra dùng Python **3.13.15**. Không cần kích hoạt virtualenv; gọi thẳng Python trong `.venv` để tránh nhầm môi trường.

## 1. Chọn đúng nhu cầu

| Nhu cầu | Cần gì? | Bắt đầu |
|---|---|---|
| Đọc báo cáo/biểu đồ | Markdown, PNG, notebook đã có output | [Báo cáo dự án](bao_cao_du_an_poi.md) |
| Chạy lại phân tích | Python + CSV trong `data/reports/v2/dataset/` | Mục 4; không cần Docker/API/crawl |
| Khám phá POI trên web | Python + `data/catalog_v2.sqlite` | Mục 2 |
| Tạo lịch có đường ô tô | Thêm Docker/OSRM đúng snapshot | Mục 3 |
| Dựng lại catalog từ đầu | PBF, địa giới, workbook, curation, các quan sát bổ sung cần dùng | Mục 5 |
| Thu thập thêm dữ liệu | Trình duyệt Playwright và parser tùy chọn | Mục 6; không thuộc bước chạy app thông thường |

SQLite, PBF, dữ liệu riêng và cache có mục nằm trong `.gitignore`. **Clone Git mới không tự có đầy đủ runtime hoặc snapshot dữ liệu riêng.** Có thể chạy notebook từ CSV đã theo dõi trong Git; muốn web giống bản báo cáo cần bộ catalog tương ứng hoặc rebuild từ các nguồn thực sự có.

## 2. Cài môi trường và chạy API/web khi đã có catalog

```powershell
python --version
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.lock.txt
.venv\Scripts\python.exe -m pip check
Test-Path data\catalog_v2.sqlite
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Nếu `Test-Path` trả `False`, chuẩn bị catalog theo mục 5. Khi API đang chạy:

- Gợi ý POI: **http://127.0.0.1:8000/**.
- Khám phá: **http://127.0.0.1:8000/explore**.
- Lịch trình: **http://127.0.0.1:8000/itinerary**.
- Thông tin dataset: **http://127.0.0.1:8000/dataset.html**.
- OpenAPI để thử request: **http://127.0.0.1:8000/docs**.
- Health: **http://127.0.0.1:8000/api/health**.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Đọc riêng `catalog`, `routing`, `basemap`, `dataset_version`; catalog ready không đồng nghĩa routing ready. Dừng API bằng `Ctrl+C` tại terminal chạy uvicorn. Sau publish catalog mới, dừng/chạy lại API để nạp đúng thế hệ dữ liệu.

Frontend là HTML/CSS/JavaScript tĩnh, không có `npm install` hoặc `npm run dev`. Leaflet vendor đã có trong repo. Nền online/ảnh cần mạng; địa giới và nền local hỗ trợ khi chặn mạng ngoài. Khi OSRM thiếu, app vẫn gợi ý bằng nội dung/ngữ cảnh với km đường chim bay, khám phá và báo trạng thái routing; không tự dựng đường đi giả.

### Luồng sử dụng ba trang

1. Ở Gợi ý POI, chọn sở thích, ngày, địa phương và mẫu ưu tiên; mặc định vị trí ở tâm địa phương, bán kính 30 km. Mở phần vị trí để nhập tọa độ, lấy GPS hoặc chuyển sang Khám phá để ghim.
2. Bấm **Nhận gợi ý**. Mở **Vì sao được gợi ý?** để xem điểm tương đối và dữ liệu thiếu. Thêm các POI muốn ghé.
3. Trang Khám phá cho tìm POI toàn quốc; chọn đúng địa phương chuyến đi để thêm điểm. Các địa bàn ngoài Hà Nội/Đà Nẵng chỉ khám phá.
4. Sang Lịch trình để đặt giờ, thời lượng, điểm bắt buộc; xem phương án và xác nhận khi có điều chỉnh. Đổi trang hoặc tải lại vẫn giữ nháp trên cùng trình duyệt.

### Thử API theo dữ liệu thật

Ví dụ này tự lấy một POI được chọn thủ công trong Hà Nội; ID cụ thể phụ thuộc snapshot:

```powershell
$items = Invoke-RestMethod 'http://127.0.0.1:8000/api/v2/pois?view=explore&limit=20000'
$chosenPoi = $items.pois | Where-Object {
    $_.location -eq 'Hà Nội' -and $_.manual_trip_quality.eligible
} | Select-Object -First 1
if ($null -eq $chosenPoi) { throw 'Catalog chưa có POI Hà Nội đủ điều kiện chọn.' }
$tripBody = @{
    start = @{ latitude = 21.0285; longitude = 105.8542 }
    date = '2026-09-20'
    location = 'Hà Nội'
    start_time = '08:00'
    end_time = '18:00'
    selected_poi_ids = @($chosenPoi.poi_id)
    must_visit_poi_ids = @($chosenPoi.poi_id)
    include_meals = $false
    auto_add = $false
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v2/trip-suggestions' `
    -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($tripBody))
```

Ngày trên là ngày demo cố định, không phải ngày hiện tại. Không bảo đảm mọi điểm lấy đầu danh sách đều có đường hoặc mở cửa hôm đó; kiểm tra `status`, `options`, `issues`, `actions`, `coverage` và `changes`. Lỗi cấu trúc request trả 422. `/api/v2/itineraries` có hợp đồng khác, dùng `required_poi_ids` và `AHPPreferences` cho nghiên cứu.

## 3. OSRM và bản đồ local

Cần Docker Desktop với Linux containers/WSL2 và tài nguyên phù hợp. Script tiền xử lý đặt giới hạn container 6 GB RAM, 8 GB cả swap, hai CPU; service 5 GB RAM. Đây là cấu hình script, không phải đo yêu cầu tối thiểu cho mọi máy. Tiền xử lý PBF Việt Nam cần thời gian và dung lượng đáng kể.

```powershell
docker info
.venv\Scripts\python.exe scripts\setup_osrm.py --download
```

Script dùng `data/raw/vietnam-260915.osm.pbf`, image OSRM đã pin digest, volume `where2go-osrm-data`, container `where2go-osrm`, endpoint **127.0.0.1:5001**. Pipeline: `osrm-extract` với `car.lua` → `osrm-partition` → `osrm-customize` → `osrm-routed --algorithm mld`. Manifest chỉ được ghi sau health check trực tiếp thành công.

Nếu runtime đã dựng đúng snapshot, có thể khởi động lại:

```powershell
docker start where2go-osrm
Invoke-RestMethod 'http://127.0.0.1:5001/route/v1/driving/105.85,21.03;105.84,21.04?overview=false'
```

Tọa độ URL OSRM có thứ tự **longitude,latitude**. Manifest routing, catalog và bản đồ local cần cùng SHA-256 PBF. `OSRM_URL` trong môi trường có thể đổi endpoint trước khi chạy API, nhưng không thay thế manifest hợp lệ. Không sửa hash bằng tay để bỏ qua lệch snapshot.

Khi cần tạo lại bản đồ:

```powershell
.venv\Scripts\python.exe scripts\build_local_basemaps.py
.venv\Scripts\python.exe scripts\build_national_basemap.py
```

Đầu ra: `web/data/basemap-hanoi.json.gz`, `basemap-danang.json.gz`, `basemap-manifest.json`, `vietnam-boundaries.json`. Nền online tải tile theo vùng xem từ OpenStreetMap/FOSSGIS; bản đồ local là lớp dự phòng, không có live traffic. Dừng riêng service của dự án khi không dùng: `docker stop where2go-osrm`.

## 4. Chạy notebook và lấy biểu đồ cho báo cáo

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
.venv\Scripts\python.exe -X utf8 scripts\run_analysis.py
```

Lệnh chạy tất cả code cell bằng chính Python hiện tại và ghi output trở lại notebook. Không cần cài kernelspec toàn hệ thống; runner dùng kernel tạm. Thành công hiện báo `PASS: 13 code cells executed`.

Đầu ra:

| Đường dẫn | Nội dung |
|---|---|
| [`notebooks/phan_tich_du_lieu_poi.ipynb`](../notebooks/phan_tich_du_lieu_poi.ipynb) | Notebook nguồn và kết quả đã chạy |
| [`docs/assets/poi/`](assets/poi/) | 14 biểu đồ PNG dùng trực tiếp trong slide |
| [`data/reports/analysis/`](../data/reports/analysis/) | Bảng CSV phân bổ, độ phủ, rating, nguồn, crawler, evaluator; JSON tổng hợp và checksum |

Mở tương tác:

```powershell
.venv\Scripts\python.exe -m jupyterlab notebooks\phan_tich_du_lieu_poi.ipynb
```

Trong VS Code, chọn kernel `.venv\Scripts\python.exe`, rồi **Restart Kernel → Run All**. Ngày tham chiếu phân tích cố định là 18/09/2026 để tái lập snapshot; khi đổi dataset cần sửa ngày phù hợp, xuất lại CSV và chạy lại evaluator cùng phiên bản. Notebook cố ý dừng nếu `summary.json`, CSV và evaluator lệch version hoặc số dòng; không bỏ assertion để chạy tiếp số liệu lẫn thế hệ.

`requirements-analysis.txt` bổ sung Matplotlib, Jupyter, nbformat/nbclient và pypdf; API không cần chúng. Pypdf phục vụ đọc paper, không được notebook tự tải tài liệu bên ngoài.

## 5. Dựng dữ liệu và tái lập snapshot

### 5.1. Kiểm kê trước khi dựng

| Nhóm | Phải giữ/chuẩn bị |
|---|---|
| Nguồn cơ bản | PBF đúng phiên bản, zip địa giới, ba workbook Google/HOTOSM |
| Curation theo Git | `data/curation/`, gồm registry, landmark, quan hệ, duration và quyết định đối chiếu |
| Đầu vào bổ sung riêng | Workbook manual nếu có, `data/enrichment/accepted*.json` |
| Cache cần giữ để tái lập chính xác | OSM supplement, geometry và image validation; ngày quan sát trong cache ảnh hưởng snapshot |
| Catalog nền | `data/catalog.sqlite` hoặc dựng từ PBF; v2 thực sự phụ thuộc baseline này |

Fresh build với thiếu quan sát riêng có thể tạo catalog có độ phủ khác. Cài đúng dependency không bảo đảm tái tạo byte-identical dataset; hash build còn bao gồm mã pipeline. Sau dọn import, build mới có thể đổi version dù bảng ngữ nghĩa giống. Báo cáo hiện tiếp tục dùng snapshot đã phân tích, không tự publish một version mới.

### 5.2. Trình tự từ nguồn cơ bản

Tải PBF và khởi tạo OSRM ở mục 3, hoặc cung cấp thủ công PBF có checksum đã biết. Nếu URL snapshot cũ không còn, cần lấy đúng snapshot đã lưu; khi chuyển snapshot phải dựng đồng bộ catalog, routing và basemap, rồi cập nhật báo cáo.

```powershell
.venv\Scripts\python.exe scripts\build_catalog.py
.venv\Scripts\python.exe scripts\extract_osm_supplement_v2.py
.venv\Scripts\python.exe scripts\extract_poi_geometry_v2.py
.venv\Scripts\python.exe scripts\build_local_basemaps.py
.venv\Scripts\python.exe scripts\build_national_basemap.py
```

Nếu có workbook manual hiện hành, kiểm tra trước build:

```powershell
if (Test-Path data\manual\poi_enrichment_v2.xlsx) {
    .venv\Scripts\python.exe scripts\validate_manual_data_v2.py
}
```

Muốn bắt đầu kiểm duyệt từ template mới, chạy riêng `scripts/create_manual_template_v2.py` sau khi có catalog nền. Script mặc định không ghi đè workbook hiện có; không dùng `--force` khi còn quan sát cần giữ. Template trống không thay thế workbook đã dùng trong báo cáo.

Build staging và audit:

```powershell
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py
```

Đầu ra trong `artifacts/dataset-build/`, chưa thay catalog đang phục vụ. Xem `dataset/audit.json`, `dataset/summary.json`, `catalog/review_queue.json`. PASS audit vẫn có thể có cảnh báo giờ/rating/access; cần đọc nội dung.

Khi đã kiểm tra staging, publish local:

```powershell
# Dừng uvicorn trước khi publish để tránh giữ catalog cũ trong bộ nhớ.
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py --publish
.venv\Scripts\python.exe scripts\export_quality_queue_v2.py
.venv\Scripts\python.exe scripts\export_priority_set_v2.py
.venv\Scripts\python.exe scripts\inventory_sources_v2.py
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Publish sao lưu catalog và báo cáo cũ vào `artifacts/dataset-backups/<timestamp>/`. SQLite được thay sau export/audit. API từ chối export khi có marker `.publishing` hoặc version export lệch catalog đang nạp.

Muốn kiểm tra semantic parity giữa hai build:

```powershell
.venv\Scripts\python.exe scripts\report_merge_v2.py --catalog artifacts\dataset-build\catalog_v2.sqlite --dataset artifacts\dataset-build\dataset --output artifacts\staged-report.json
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py --compare-report artifacts\staged-report.json
```

Chỉ thêm `--publish` nếu muốn thay dữ liệu active sau so sánh. Phép so bảng ngữ nghĩa loại thời điểm build; không dùng riêng checksum file SQLite làm bằng chứng toàn bộ nội dung thay đổi.

### 5.3. Hoàn tác

Dừng API. Chọn **một** snapshot backup cụ thể, kiểm tra chứa `catalog_v2.sqlite`, `dataset/`, `catalog/`; sao chép về `data/catalog_v2.sqlite`, `data/reports/v2/dataset/`, `data/reports/v2/catalog/`. Không trộn ba phần từ ba backup khác nhau. Khởi động lại API và kiểm tra version/health/export. Backup publish hiện không chứa toàn bộ raw/cache/manual hoặc private export; cần lưu riêng các đầu vào đó nếu mục tiêu là tái dựng đầy đủ lịch sử.

## 6. Thu thập bổ sung có kiểm soát

Không cần crawl lại để chạy app hoặc notebook. Khi bổ sung dữ liệu mới:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-enrichment.txt
.venv\Scripts\python.exe -m playwright install firefox chromium
.venv\Scripts\python.exe scripts\prepare_enrichment_v2.py
.venv\Scripts\python.exe scripts\collect_enrichment_v2.py --seeds data\enrichment\seeds.json --output data\enrichment\pilot.json --limit 20
.venv\Scripts\python.exe scripts\review_enrichment_v2.py --input data\enrichment\pilot.json --output data\enrichment\accepted-pilot.json --report data\reports\v2\collection_pilot.json
```

Parser cần Git để cài dependency theo commit. `requirements-scraper-v2.txt` dành cho pilot cũ trong môi trường tách riêng; luồng hiện hành dùng `requirements-enrichment.txt`. Giữ các script pilot/focus cũ vì còn phục vụ truy nguyên/kiểm duyệt, không phải phần app gọi khi khởi động.

Collector checkpoint từng lượt; chạy lại mặc định bỏ record đã có. `--retry` chỉ thử lại `transient_error,unresolved`; chỉ mở rộng nhóm retry khi đã xử lý nguyên nhân. Lô >20 yêu cầu cổng pilot 19/20 và tối đa 200. Gặp challenge thì dừng để xử lý truy cập theo luồng thông thường. Review phải có bằng chứng, không đổi `needs_review` thành accepted chỉ để tăng tỷ lệ.

Kiểm tra ảnh cập nhật cache:

```powershell
.venv\Scripts\python.exe scripts\validate_images_v2.py --catalog data\catalog_v2.sqlite --refresh
```

Sau thu thập/review/kiểm tra ảnh, rebuild staging rồi audit trước publish. Chỉ những file `accepted*.json` có hàng được chấp nhận mới vào catalog. Quan sát Google giữ `restricted_internal`; không phát hành toàn bộ export như dataset mở. OSM giữ attribution và ODbL. Không sửa trực tiếp CSV dẫn xuất để chữa dữ liệu; sửa nguồn kiểm duyệt/curation tương ứng.

## 7. Kiểm tra kỹ thuật và thực nghiệm

### 7.1. Code và dữ liệu

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m ruff check where2go scripts tests
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
node --check web\app.js
node --check web\map.js
node --check web\dataset.js
.venv\Scripts\python.exe scripts\audit_dataset_v2.py --output artifacts\report-validation\audit.json
```

Node cần cho ba lệnh kiểm tra cú pháp, không cần cho API. Pytest chứa cả test đọc các dữ liệu local; clone mới thiếu catalog/PBF có thể không chạy đủ bộ. Không gọi lỗi thiếu fixture là chứng minh thuật toán sai.

### 7.2. Evaluator có OSRM thật

```powershell
.venv\Scripts\python.exe scripts\evaluate_v2.py --output artifacts\report-validation\evaluation.json --method-key artifacts\report-validation\method_key.json --grading artifacts\report-validation\grading_unfilled.xlsx
.venv\Scripts\python.exe scripts\evaluate_trip_choices.py --output artifacts\report-validation\trip_choices_evaluation.json
```

Evaluator thứ nhất chạy 64 lượt; thứ hai bảy kịch bản cũ/mới. Xuất riêng để giữ phiếu chấm đã có: mặc định `evaluate_v2.py` ghi `data/manual/v2_owner_grading.xlsx`, có thể ghi đè kết quả chấm nếu dùng không chú ý. Không chạy hai evaluator cùng lúc nếu muốn đo latency so sánh.

Notebook đọc báo cáo chuẩn trong `data/reports/v2/`, không tự thay bằng một lượt thực nghiệm trong artifacts. Khi đổi snapshot và chấp nhận kết quả mới, cập nhật bộ báo cáo chuẩn nhất quán rồi chạy notebook lại. Phiếu chưa chấm nghĩa là đánh giá người dùng **NOT RUN**.

### 7.3. Smoke trình duyệt

API và OSRM phải chạy, sau đó:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe -X utf8 scripts\smoke_web.py --url http://127.0.0.1:8000
```

Smoke hiện tại kiểm tra gợi ý, nháp qua ba trang, nháp riêng theo địa phương, lịch với OSRM thật, xác nhận/hủy, phản hồi cũ, ảnh lỗi và mobile với bản đồ offline. Đầu ra tại `artifacts/recommendations/`. Network/tile bên ngoài có thể thất bại độc lập với API. Hai tên script cũ được giữ làm entrypoint tương thích đến cùng bộ smoke mới.

## 8. Xử lý sự cố

| Hiện tượng | Kiểm tra và cách xử lý |
|---|---|
| Không thấy `catalog_v2.sqlite` | Clone thiếu runtime; cung cấp snapshot hoặc dựng theo mục 5 |
| `ModuleNotFoundError` | Dùng đúng `.venv\Scripts\python.exe`; cài đúng requirements cho app/analysis/enrichment |
| Browser executable missing | Chạy `python -m playwright install chromium` hoặc `firefox` đúng collector |
| Docker daemon không truy cập được | Mở Docker Desktop, kiểm tra Linux engine/WSL2; notebook không phụ thuộc Docker |
| Container đã có nhưng manifest khác | Kiểm tra PBF/hash và container của dự án; không sửa hash hoặc xóa volume hàng loạt |
| Routing unavailable | Kiểm tra 5001, manifest và snapshot; gợi ý được fallback km có nhãn, lịch trình không được giả thời gian đường bộ |
| Export 503 sau publish | Khởi động lại API; kiểm tra marker và version; tránh phục vụ catalog cũ với CSV mới |
| “Không đủ lịch” | Đọc reasons: giờ, thiếu đường, địa phương, parent-child, giới hạn tìm kiếm; thử sửa khung/điểm |
| Notebook assertion version | CSV/summary/evaluator không cùng snapshot; dựng/xuất/đánh giá nhất quán |
| Chữ tiếng Việt sai trong console | Dùng `-X utf8`; đọc file bằng `Get-Content -Encoding UTF8`; không đổi nội dung nguồn chỉ vì console render sai |
| Cổng 8000 đang dùng | Dùng API đang chạy hoặc chọn `--port 8001`; smoke hỗ trợ `--url` nếu cần |

## 9. Tổ chức tài liệu sau làm sạch

`docs/` giữ ba tài liệu có vai trò riêng cùng mục lục: báo cáo tổng hợp, hướng dẫn chạy và kịch bản bảo vệ. Sáu bài cũ về công thức/triển khai/kết quả/kế hoạch/hợp nhất/trải nghiệm được gộp vào ba tài liệu này rồi xóa để tránh trùng và mâu thuẫn. Lịch sử vẫn ở Git. `data/reports/v2/dataset/README.md` là mô tả export được sinh bằng code, được giữ vì không trùng vai trò tài liệu dự án.

Không xóa workbook backup, PDF paper, dữ liệu curation, cache nguồn cần tái lập hoặc module v1 còn phụ thuộc. `.venv`, cache Python, `.ruff_cache`, notebook checkpoint và `artifacts` được Git bỏ qua; các PNG báo cáo và notebook đã thực thi được giữ để đọc ngay.

## 9. Thực nghiệm gợi ý POI và phiếu nhóm chấm

Chạy khi đã có catalog, độc lập với server web. OSRM là tùy chọn; metadata ghi rõ mỗi bối cảnh dùng mode nào.

```powershell
.venv\Scripts\python.exe -X utf8 scripts\evaluate_recommendations.py
# Nếu chủ động đánh giá chỉ với khoảng cách địa lý, lưu thành một đợt riêng:
.venv\Scripts\python.exe -X utf8 scripts\evaluate_recommendations.py --geographic-only --output artifacts\recommendation-geographic
```

Đợt mặc định xuất `data/reports/recommendations/`: `evaluation.json` (96 lượt), `matrices.json`, `sensitivity.json`, `grading_template.csv`, `grading_manifest.json`. Sáu phương pháp dùng cùng ma trận trong một bối cảnh. Template được tái tạo nhưng script không ghi đè phiếu đã chấm mang tên khác.

**Trình tự chấm:** giữ nguyên đợt đánh giá; sao chép template thành `data/manual/recommendation_grades.csv`. Nhóm chấm đồng thuận `relevance_0_3`: 0 không phù hợp, 1 ít phù hợp, 2 phù hợp, 3 rất phù hợp; bổ sung `notes`. Giữ nguyên các cột ngữ cảnh/POI và không xem `evaluation.json` để tránh biết phương pháp trước khi chấm. Không điền nhãn dựa vào score tự động.

```powershell
if (-not (Test-Path data\manual\recommendation_grades.csv)) {
    Copy-Item data\reports\recommendations\grading_template.csv data\manual\recommendation_grades.csv
}
.venv\Scripts\python.exe -X utf8 scripts\evaluate_recommendations.py --grades data\manual\recommendation_grades.csv
.venv\Scripts\python.exe -X utf8 scripts\run_analysis.py
```

Khi chưa chấm, có thể kiểm tra giao thức bằng `--grades data/reports/recommendations/grading_template.csv`: tất cả Precision/NDCG giữ null/NOT GRADED. Chỉ số được lưu ở `quality_metrics.json`; không tự chạy lại pool khi dùng `--grades`. Khi chạy lại evaluator, cần chấm/tính lại theo template và hash tương ứng trước khi chạy notebook. Không lấy phiếu của bối cảnh cũ ghép vào đợt mới.

Notebook không cần API/OSRM đang chạy; đọc các artifact đã xuất và kiểm tra dataset/policy/hash. Tập hiện có: 4 development, 12 holdout theo yêu cầu; chia theo ngữ cảnh, không phải huấn luyện collaborative filtering. Báo cáo ghi rõ nhóm tự chấm và không suy rộng sang người dùng độc lập.

Kiểm tra ba trang và API:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check where2go scripts tests
.venv\Scripts\python.exe -X utf8 scripts\smoke_web.py --url http://127.0.0.1:8000
```

Smoke cần server và OSRM đúng snapshot cho phần tạo lịch thực; lưu ảnh desktop/mobile và JSON kiểm chứng tại `artifacts/recommendations/`. Dùng `smoke_web.py` cho bản hiện tại; hai tên script cũ cũng trỏ đến bộ smoke này. Nếu cổng 8000 đang chạy phiên bản cũ, dừng đúng terminal của app đó rồi chạy lại, hoặc chọn `--port 8001` và thay URL smoke tương ứng.
