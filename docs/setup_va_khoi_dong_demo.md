# Setup và khởi động demo Where2Go đầy đủ trên Windows

Tài liệu này dùng cho **PowerShell**, chạy tại thư mục gốc dự án. Mục tiêu là mở được cả **Gợi ý POI → Khám phá → Lịch trình**, có dữ liệu hiện hành, đường ô tô OSRM và các kịch bản Đà Nẵng đã kiểm chứng.

**Trên máy hiện tại, dùng ngay mục 1.** Khi cài sang máy khác, làm mục 2–3 trước, rồi quay lại mục 1. Bộ kiểm tra trước buổi demo nằm ở mục 5; thiết lập thao tác trình diễn nằm ở mục 6.

Ngày kiểm chứng: **21/09/2026**. Python **3.13.15**, Docker Engine **29.7.2**, Linux containers. API tại **http://127.0.0.1:8000**; OSRM tại **http://127.0.0.1:5001**. Web là HTML/CSS/JavaScript tĩnh được FastAPI phục vụ: **không có bước `npm install`, `npm run dev`, hay build frontend**.

## 1. Chạy nhanh mỗi lần demo trên máy đã setup

### 1.1. Mở Docker Desktop

Mở Docker Desktop từ Start Menu, chờ engine hoạt động. Nếu muốn mở bằng PowerShell, lệnh dưới tìm hai vị trí cài phổ biến:

```powershell
$dockerDesktopExe = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
    "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($dockerDesktopExe) {
    Start-Process -FilePath $dockerDesktopExe -WindowStyle Hidden
} else {
    Write-Host 'Mở Docker Desktop từ Start Menu hoặc cài Docker Desktop trước.'
}
```

Docker phải dùng Linux containers. Kiểm tra:

```powershell
docker info --format '{{.ServerVersion}} {{.OSType}}'
```

Kết quả đã kiểm tra: `29.7.2 linux`. Nếu có lỗi kết nối daemon, chờ Docker khởi động xong rồi thử lại; chưa chạy API/demo đường đi ở bước này.

### 1.2. Terminal A — bật OSRM và API

Mở terminal PowerShell thứ nhất và chạy:

```powershell
Set-Location -LiteralPath 'D:\Desktop\NHAP\DSS_NGUYENVANHIEU\GKI-Project\where2go-dss'
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Chưa có môi trường Python. Làm mục 2 trước.'
}
if (-not (Test-Path -LiteralPath 'data\catalog_v2.sqlite')) {
    throw 'Thiếu catalog runtime. Làm mục 3 trước.'
}
if (-not (Test-Path -LiteralPath 'data\routing\manifest.json')) {
    throw 'Chưa có manifest OSRM. Làm mục 3.3 trước.'
}

docker start where2go-osrm
if ($LASTEXITCODE -ne 0) { throw 'Không bật được OSRM. Xem mục 3.3 và mục 8.' }

$env:OSRM_URL = 'http://127.0.0.1:5001'
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Lệnh cuối giữ terminal để chạy server. Thấy `Application startup complete` và `Uvicorn running on http://127.0.0.1:8000` là API đã lắng nghe. **Để terminal A mở**, dùng terminal B cho các lệnh tiếp theo. Không dùng `--reload` trong buổi demo để tránh tự khởi động lại khi sửa tài liệu/mã.

Nếu cổng 8000 đang có API của dự án chạy từ trước, có thể dùng server đó sau khi kiểm tra health. Muốn nạp thay đổi Python mới, dừng server cũ rồi chạy lệnh trên; không mở hai server tranh cùng cổng.

### 1.3. Terminal B — xác nhận cả ba dịch vụ sẵn sàng

```powershell
Set-Location -LiteralPath 'D:\Desktop\NHAP\DSS_NGUYENVANHIEU\GKI-Project\where2go-dss'
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

$demoHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 60
$demoHealth | ConvertTo-Json -Depth 5
if ($demoHealth.catalog -ne 'ready' -or $demoHealth.routing -ne 'ready' -or $demoHealth.basemap -ne 'ready') {
    throw 'Chưa đủ điều kiện demo đầy đủ: cần catalog, routing và basemap đều ready.'
}

$demoRoad = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/route/v1/driving/108.2022,16.0544;108.2450,16.0630?overview=false' -TimeoutSec 60
if ($demoRoad.code -ne 'Ok') { throw 'OSRM chưa trả được tuyến Đà Nẵng.' }
$demoRoad.routes | Select-Object distance, duration
```

Kết quả hiện hành:

```json
{
  "catalog": "ready",
  "catalog_api_version": "v2",
  "poi_count": 16129,
  "routing": "ready",
  "dataset_version": "v2-c3ad315d02c5356a",
  "routing_version": "1e1d2ec5e5a86240",
  "basemap": "ready",
  "basemap_locations": ["danang", "hanoi"]
}
```

Tuyến kiểm tra từ tâm Đà Nẵng đến tọa độ gần Mỹ Khê trả **5.206,3 mét, 385,2 giây** trong lần chạy này. Đây là kết quả OSRM, không phải đo lái xe ngoài thực tế. Tọa độ trong URL OSRM có thứ tự **kinh độ,vĩ độ**.

### 1.4. Mở web

Mở trình duyệt đến **http://127.0.0.1:8000/**. Dùng cửa sổ InPrivate/Incognito mới để không mang theo nháp sở thích hoặc danh sách đã chọn từ lần trước.

| Trang | URL |
| --- | --- |
| Gợi ý POI | http://127.0.0.1:8000/ |
| Khám phá, tìm địa điểm và chọn điểm xuất phát | http://127.0.0.1:8000/explore |
| Lịch trình | http://127.0.0.1:8000/itinerary |
| Dữ liệu | http://127.0.0.1:8000/dataset.html |
| Thử API bằng Swagger | http://127.0.0.1:8000/docs |

Dùng thống nhất `127.0.0.1`; chuyển sang `localhost` tạo origin khác nên nháp trình duyệt không giống nhau. Không mở trực tiếp `web/index.html` bằng đường dẫn file hoặc Live Server, vì web cần gọi API cùng origin.

## 2. Setup Python và trình duyệt kiểm thử lần đầu

### 2.1. Công cụ cần cài

- **Python 3.13, 64 bit**, có lệnh `python` hoặc Windows Python Launcher `py`.
- **Docker Desktop** với WSL2/Linux containers để chạy OSRM.
- Trình duyệt Edge/Chrome để thao tác demo.
- **Node.js chỉ cần nếu chạy kiểm tra cú pháp JavaScript**, không bắt buộc để phục vụ web.

Kiểm tra công cụ:

```powershell
python --version
Get-Command python,docker -ErrorAction Stop | Select-Object Name,Source
docker info --format '{{.ServerVersion}} {{.OSType}}'
```

Nếu `python` trỏ nhầm bản, dùng `py -3.13` khi tạo môi trường. Cài đặt Python/Docker Desktop/WSL2 trên một máy Windows trắng là bước chuẩn bị hệ điều hành; phiên kiểm chứng này dùng các công cụ đã có, không phải cài mới hệ điều hành.

### 2.2. Tạo môi trường và cài đúng phiên bản dependency

```powershell
Set-Location -LiteralPath 'D:\Desktop\NHAP\DSS_NGUYENVANHIEU\GKI-Project\where2go-dss'
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'

# Chỉ tạo khi chưa có, không ghi đè môi trường đang dùng.
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Tạo virtualenv thất bại.' }
}

.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Cài dependency thất bại.' }

.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency chưa tương thích.' }

.venv\Scripts\python.exe -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Cài Chromium cho Playwright thất bại.' }
```

`requirements-dev.txt` đã bao gồm `requirements-app.lock.txt`, thêm Ruff; lock của app có cả pytest và Playwright. Cách này đủ cho API, kiểm thử và các script demo hiện tại. Nếu chỉ chạy API, có thể dùng `pip install -r requirements-app.lock.txt`. Không cần cài parser crawler hoặc Jupyter để demo web.

Không cần `Activate.ps1`; gọi trực tiếp `.venv\Scripts\python.exe` giúp tránh nhầm interpreter và lỗi Execution Policy. Không cần `pip install --upgrade` hàng loạt ngay trước demo. Nếu chuyển máy, tạo lại `.venv` trên máy mới thay vì sao chép nguyên virtualenv cũ.

## 3. Chuẩn bị dữ liệu và OSRM

### 3.1. Kiểm kê runtime hiện có

```powershell
$demoRequiredFiles = @(
    'data\catalog_v2.sqlite',
    'data\reports\v2\catalog\manifest.json',
    'data\reports\v2\dataset\summary.json',
    'data\routing\manifest.json',
    'web\data\basemap-manifest.json',
    'web\data\basemap-danang.json.gz',
    'web\data\basemap-hanoi.json.gz',
    'web\data\vietnam-boundaries.json',
    'web\vendor\leaflet.js',
    'web\vendor\leaflet.css'
)
$demoRequiredFiles | ForEach-Object {
    [PSCustomObject]@{ File = $_; Exists = (Test-Path -LiteralPath $_) }
}
```

Các file này đã hiện hữu trên máy được kiểm chứng. Để trang Dữ liệu xuất bảng đầy đủ, giữ **toàn bộ** `data/reports/v2/dataset/` cùng thế hệ catalog, không chỉ `summary.json`.

**Clone Git chưa đủ để có cùng demo.** SQLite, PBF, cache và Docker volume có thành phần không nằm trong Git. CSV `sources.csv`, `ratings.csv` hoặc `opening_hours.csv` là báo cáo dẫn xuất; API không thay catalog bằng cách đọc từng CSV đó.

### 3.2. Nếu chuyển sang máy mới

Ưu tiên mang bộ snapshot đã dùng để demo: `data/catalog_v2.sqlite`, `data/reports/v2/catalog/`, `data/reports/v2/dataset/`, bộ bản đồ `web/data/`, mã nguồn/curation tương ứng. Chuẩn bị thêm **PBF đúng phiên bản** để dựng OSRM trên máy mới; chép `manifest.json` không tự tạo Docker volume hoặc dữ liệu đường đi.

Snapshot hiện dùng:

```text
Catalog: v2-c3ad315d02c5356a
PBF: data/raw/vietnam-260915.osm.pbf
PBF SHA-256: 4f7244d59895803a521b8f6ef0b86629bf4470565ad329ed5d3336676db047e7
OSRM container: where2go-osrm
OSRM volume: where2go-osrm-data
Profile: car.lua
Algorithm: mld
```

Nếu đã có PBF:

```powershell
Get-FileHash -LiteralPath 'data\raw\vietnam-260915.osm.pbf' -Algorithm SHA256
```

Catalog, routing và basemap phải dựa trên cùng PBF. Không thay PBF bằng bản mới nhất rồi giữ nguyên các manifest cũ.

### 3.3. Tạo OSRM lần đầu hoặc xác nhận setup đã có

Sau khi Docker hoạt động và Python đã cài dependency:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\setup_osrm.py --download
if ($LASTEXITCODE -ne 0) { throw 'Setup OSRM chưa hoàn tất. Đọc lỗi trước khi tiếp tục.' }
```

Script sẽ dùng PBF hiện có; nếu thiếu mới tải file snapshot, sau đó tạo volume/container của dự án và chạy tiền xử lý. Khi container và manifest đã đúng, script dùng lại chúng. **Lệnh này đã chạy PASS trong phiên kiểm chứng theo nhánh dùng lại runtime; không tải lại hoặc tiền xử lý toàn Việt Nam trong phiên này.**

Kết thúc thành công có dòng `OSRM route PASS; manifest: ...`. Script chỉ ghi manifest thành công sau khi gọi được tuyến thật. Tiền xử lý mới dùng giới hạn container 6 GB RAM, 8 GB RAM+swap, 2 CPU; service có giới hạn 5 GB RAM. Chuẩn bị dung lượng Docker và thời gian xử lý trước ngày trình diễn.

Nếu URL snapshot cũ không còn truy cập được, lấy đúng PBF đã lưu; không tự đổi tên một snapshot khác để vượt kiểm tra. Nếu gặp `Existing where2go-osrm has another/missing manifest`, kiểm tra container/manifest tại mục 8, không xóa volume để thử may rủi.

Các lần sau chỉ cần:

```powershell
docker start where2go-osrm
docker ps --filter name=where2go-osrm --format '{{.Names}} | {{.Status}} | {{.Ports}}'
```

### 3.4. Chỉ khi không có catalog snapshot: dựng từ nguồn

Đây là nhánh tái dựng dữ liệu, **không phải bước khởi động hằng ngày**. Chỉ thực hiện khi đã có đủ PBF, bộ địa giới, workbook nguồn, curation và các quan sát bổ sung cần thiết. Tên/đầu vào chi tiết nằm trong [hướng dẫn bảo trì dữ liệu](huong_dan_chay.md), mục 5.

```powershell
.venv\Scripts\python.exe scripts\build_catalog.py
if ($LASTEXITCODE -ne 0) { throw 'Build catalog nền thất bại.' }
.venv\Scripts\python.exe scripts\extract_osm_supplement_v2.py
if ($LASTEXITCODE -ne 0) { throw 'Trích OSM bổ sung thất bại.' }
.venv\Scripts\python.exe scripts\extract_poi_geometry_v2.py
if ($LASTEXITCODE -ne 0) { throw 'Trích hình học POI thất bại.' }
.venv\Scripts\python.exe scripts\build_local_basemaps.py
if ($LASTEXITCODE -ne 0) { throw 'Build bản đồ local thất bại.' }
.venv\Scripts\python.exe scripts\build_national_basemap.py
if ($LASTEXITCODE -ne 0) { throw 'Build địa giới bản đồ thất bại.' }
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py
if ($LASTEXITCODE -ne 0) { throw 'Build/audit staging thất bại.' }
```

Xem `artifacts/dataset-build/dataset/audit.json`, `summary.json` và báo cáo catalog staging. Chỉ khi muốn dùng bộ mới, dừng API rồi publish:

```powershell
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py --publish
if ($LASTEXITCODE -ne 0) { throw 'Chưa publish được dataset mới.' }
```

Sau publish, quay lại mục 1 để nạp dataset mới. Phiên bản và Top-10 có thể khác tài liệu demo cũ; chạy sàng lọc lại trước khi đọc lời thoại có số liệu. **Nhánh rebuild/publish này không được chạy trong phiên kiểm chứng setup**, vì máy đã có snapshot đúng; không gọi nó là đã kiểm chứng fresh build.

## 4. Thử một yêu cầu gợi ý Đà Nẵng bằng PowerShell

Giữ terminal A chạy. Tại terminal B:

```powershell
$demoRequest = @{
    location = 'Đà Nẵng'
    scope = 'danang_hoian'
    tourism_only = $true
    date = '2026-09-21'
    start = @{ latitude = 16.0544; longitude = 108.2022 }
    interests = @('thiên nhiên')
    preferred_categories = @()
    selected_poi_ids = @()
    preset = 'balanced'
    radius_km = 15
    top_k = 10
} | ConvertTo-Json -Depth 6

$demoResponse = Invoke-WebRequest -UseBasicParsing -Method Post `
    -Uri 'http://127.0.0.1:8000/api/v2/recommendations' `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($demoRequest)) `
    -TimeoutSec 120

# Windows PowerShell 5.1 có thể đoán sai encoding của JSON trả về.
$demoJson = [System.Text.Encoding]::UTF8.GetString($demoResponse.RawContentStream.ToArray())
$demoRecommendation = $demoJson | ConvertFrom-Json

$demoRecommendation | Select-Object dataset_version,policy_version,eligible_count,candidate_count,travel_metric
$demoRecommendation.items | Select-Object rank,name,category
```

Kết quả đếm và tên POI phụ thuộc snapshot/policy. Với checkout hiện tại phải thấy policy `poi-recommendation-3.0`; kiểm tra `matching_count`, `interpreted_request` và không dùng số lịch sử policy 1.1 làm kết quả hiện hành.

Ngay cả khi health báo routing ready, ca này vẫn có thể dùng `geographic_distance`: toàn bộ tập ứng viên không có ma trận tuyến hợp lệ thì thuật toán dùng một đơn vị khoảng cách thống nhất. Đây là phân biệt giữa “dịch vụ OSRM đang chạy” và “mọi POI trong lượt này có đường đi đầy đủ”. Kịch bản K2 đã chọn tập có `road_time` để minh họa chi phí đường ô tô.

## 5. Chạy kiểm tra đầy đủ trước buổi demo

### 5.1. Test, cú pháp và audit dữ liệu

```powershell
New-Item -ItemType Directory -Force 'artifacts\demo-readiness' | Out-Null

.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'pip check chưa đạt.' }
.venv\Scripts\python.exe -m ruff check where2go scripts tests
if ($LASTEXITCODE -ne 0) { throw 'Ruff chưa đạt.' }
.venv\Scripts\python.exe -X utf8 -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Pytest chưa đạt.' }

foreach ($demoJs in @('common', 'recommend', 'explore', 'app', 'map', 'dataset')) {
    node --check ('web/' + $demoJs + '.js')
    if ($LASTEXITCODE -ne 0) { throw ('Lỗi cú pháp JavaScript: ' + $demoJs) }
}

.venv\Scripts\python.exe -X utf8 scripts\audit_dataset_v2.py --output artifacts\demo-readiness\audit.json
if ($LASTEXITCODE -ne 0) { throw 'Audit dữ liệu có lỗi cứng.' }
```

Node cần có cho vòng kiểm tra cú pháp, xem mục 2. Kết quả phiên này: **134 tests passed**, Ruff PASS, sáu file JS đạt cú pháp, audit **0 lỗi cứng / 4.818 cảnh báo dữ liệu**. Cảnh báo không đồng nghĩa startup thất bại, nhưng cũng không được diễn giải thành dữ liệu hoàn hảo.

### 5.2. Kiểm thử ba trang bằng Chromium

API và Docker/OSRM phải đang chạy:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\smoke_web.py --url http://127.0.0.1:8000
if ($LASTEXITCODE -ne 0) { throw 'Luồng trình duyệt chưa đạt. Đọc lỗi trước khi trình diễn.' }
Get-Content -LiteralPath 'artifacts\recommendations\verification.json' -Encoding UTF8
```

Kết quả đã quan sát sau sửa lỗi `exploreFilters`:

```json
{
  "human_quality": "NOT GRADED",
  "cross_page_city_drafts": "PASS",
  "actual_osrm_itinerary_confirmation": "PASS",
  "stale_response": "PASS",
  "broken_image_fallback": "PASS",
  "mobile_offline_basemap": "PASS",
  "javascript_errors": []
}
```

Bộ này thực hiện gợi ý, giữ lựa chọn qua trang/tải lại, tách nháp theo địa phương, lịch trình có đường OSRM thật, chọn/hủy phương án, chặn phản hồi cũ, ảnh dự phòng, mobile và bản đồ offline. `human_quality: NOT GRADED` nghĩa là chưa có chấm chất lượng từ người dùng độc lập, không phải lỗi khởi động.

Ảnh và báo cáo nằm trong `artifacts/recommendations/`. Script có thể ghi đè bằng chứng smoke cũ; nếu cần giữ lịch sử, sao lưu thư mục trước khi chạy. Không dùng báo cáo cũ để kết luận lần mới đạt nếu tiến trình mới vừa báo lỗi.

### 5.3. Chạy lại các kịch bản trình diễn đã chọn

Lần chuẩn bị đầy đủ, chạy sàng lọc rồi replay trên web vào thư mục riêng, giữ nguyên bằng chứng lần chọn demo ban đầu:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\select_demo_danang.py sweep --output artifacts\demo-readiness\scenarios
if ($LASTEXITCODE -ne 0) { throw 'Sàng lọc API chưa hoàn tất.' }
.venv\Scripts\python.exe -X utf8 scripts\select_demo_danang.py browser --output artifacts\demo-readiness\scenarios
if ($LASTEXITCODE -ne 0) { throw 'Replay kịch bản trên web chưa đạt.' }
```

Lệnh đầu chạy 113 lượt với 111 cấu hình; lệnh sau chạy 11 bước chọn lọc và kiểm tra lặp lại. Không cần chạy lại sàng lọc trước mỗi lần bấm demo. Trong phiên startup này, đã replay 11 bước và 3 lần lặp với **bằng chứng sàng lọc đã lưu từ phiên trước**, kết quả khớp; không tuyên bố đã chạy thêm 113 lượt ở phiên startup.

Nếu muốn đối chiếu đúng bảng thứ hạng đã viết, dùng `screening.json` từ lần viết tài liệu, sao chép nó sang thư mục riêng rồi replay. Chạy sweep mới chỉ bảo đảm UI khớp API hiện tại, không tự xác nhận các con số cố định trong Markdown cũ vẫn đúng. Lệnh `export_demo_danang_selection.py` có cập nhật tài liệu/báo cáo; chỉ chạy khi chủ động làm mới bộ chứng cứ, không phải bước khởi động.

## 6. Thiết lập trình duyệt trước khi trình diễn

Theo [2 kịch bản chính và 1 kịch bản dự phòng](demo_da_nang_2_kich_ban_chinh.md). Dùng đúng ngày **21/09/2026** để tái lập, dù ngày chạy thực tế sau đó có thể khác. Đây là ngày mô phỏng cố định; nếu dùng ngày hiện tại phải kiểm tra kết quả lại.

**K1 mở đầu:** Đà Nẵng; phạm vi Đà Nẵng–Hội An–Cù Lao Chàm; nhóm Tham quan và ngoài trời; bán kính 15 km; Cân bằng các yếu tố; chủ đề thiên nhiên; Nhu cầu trống; Loại hình không chọn; tọa độ **16.0544 / 108.2022**; chuyến đi chưa chọn POI nào. Bấm Nhận gợi ý.

**K2 mở đầu:** giữ ngày/địa phương/phạm vi/nhóm; bỏ mọi chủ đề; nhập **biển**; chọn **Đi gần**; bán kính **5 km**; không chọn Loại hình; cùng tọa độ trung tâm. Sau đó đổi tâm sang **16.0630 / 108.2450**, rồi đổi bán kính theo hướng dẫn.

Các nút chủ đề là chọn nhiều, không tự bỏ nút cũ khi bật nút mới. Sau mỗi thay đổi phải bấm **Nhận gợi ý**. Không thêm POI vào chuyến giữa các bước so sánh thứ hạng, vì POI đã chọn bị loại khỏi gợi ý sau. Sau khi xong phần so sánh mới chuyển sang luồng lập lịch nếu muốn.

K1 dùng đường chim bay, K2 dùng OSRM trong lần kiểm chứng. Nền bản đồ/ảnh online cần mạng; thiếu ảnh có ô “Chưa có ảnh”. Browser smoke chứng minh ô dự phòng hoạt động, **không chứng minh mọi ảnh ngoài Internet đều tải được**.

## 7. Dừng và chạy lại đúng cách

Tại terminal A, bấm **Ctrl+C** để dừng Uvicorn. Khi cần dừng riêng đường đi:

```powershell
docker stop where2go-osrm
```

Lần sau chạy lại mục 1.2. `docker stop` giữ container/volume; không dùng `docker system prune`, xóa volume hoặc rebuild catalog chỉ để tắt demo.

Nếu API chạy nền và không có terminal A, xác định tiến trình đang giữ cổng:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

Đối chiếu `OwningProcess` rồi xem chính xác dòng lệnh trước khi dừng:

```powershell
$demoApiProcessId = [int](Read-Host 'Nhập PID giữ cổng 8000 cần kiểm tra')
Get-CimInstance Win32_Process -Filter "ProcessId=$demoApiProcessId" |
    Select-Object ProcessId,ExecutablePath,CommandLine | Format-List
```

Chỉ khi đúng Uvicorn của checkout này mới dừng PID vừa kiểm tra:

```powershell
Stop-Process -Id $demoApiProcessId
```

Không dừng hàng loạt `python.exe` hoặc mọi container Docker. Sau đổi mã Python/catalog, khởi động lại API để nạp bản mới. Sau đổi JavaScript, tải lại trang bằng **Ctrl+F5**.

## 8. Xử lý lỗi thường gặp khi khởi động

| Hiện tượng | Cách xử lý |
| --- | --- |
| `python` mở Microsoft Store hoặc sai phiên bản | Kiểm tra `Get-Command python`; tạo venv bằng `py -3.13 -m venv .venv` nếu launcher đã có |
| `ModuleNotFoundError` | Chạy đúng `.venv\Scripts\python.exe`, cài `requirements-dev.txt` rồi `pip check` |
| `Browser executable doesn't exist` | `.venv\Scripts\python.exe -m playwright install chromium` |
| Docker pipe/daemon unavailable | Mở Docker Desktop, kiểm tra WSL2/Linux containers và chạy lại `docker info` |
| `No such container: where2go-osrm` | Làm mục 3.3, không chỉ tạo file manifest |
| Manifest/container không cùng thế hệ | Xem `docker inspect where2go-osrm`, `data/routing/manifest.json` và checksum PBF; đối chiếu trước khi dựng lại |
| OSRM chưa phản hồi | `docker logs --tail 60 where2go-osrm`; kiểm tra cổng 5001 và URL tuyến ở mục 1.3 |
| API báo cổng 8000 đã dùng / WinError 10048 | Xem PID theo mục 7, dùng server đúng đang chạy hoặc dừng đúng tiến trình rồi bật lại |
| Không có catalog hoặc ứng dụng không tìm thấy bảng SQLite | Bổ sung snapshot ở đúng `data/catalog_v2.sqlite`; CSV báo cáo không thay runtime SQLite |
| Health routing không ready dù container Up | Kiểm tra tuyến trực tiếp, `OSRM_URL`, manifest và PBF đồng bộ; khởi động lại API sau sửa runtime |
| Health ready nhưng gợi ý dùng đường chim bay | Có ứng viên thiếu tuyến hợp lệ cho ma trận; đọc `travel_metric`, không gọi km là phút lái xe |
| Khám phá/Lịch trình báo `exploreFilters is not defined` | Dùng bản mã hiện tại: hàm được chuyển sang `web/map.js` dùng chung; Ctrl+F5 và chạy lại smoke |
| Đổi sở thích nhưng thấy kết quả lạ | Bỏ chủ đề/loại hình cũ, kiểm tra tọa độ/ngày/POI đã chọn, bấm Nhận gợi ý; xem thông báo bộ lọc |
| Kết quả khác bảng kịch bản | Đối chiếu phiên bản catalog/routing, ngày 21/09/2026, vị trí, bán kính, trọng số, chủ đề và danh sách đã chọn |
| Request tiếng Việt bị lỗi | Gửi JSON UTF-8 như mục 4, không phụ thuộc encoding mặc định của Windows PowerShell |
| Tên POI trên PowerShell hiện `BÃ£i...` | Dùng cách đọc byte phản hồi UTF-8 ở mục 4; Windows PowerShell 5.1 có thể giải mã JSON sai dù web hiển thị đúng |
| Link tải snapshot không còn | Khôi phục PBF đúng checksum đã lưu; nếu đổi dữ liệu thì dựng đồng bộ và kiểm tra lại toàn bộ demo |

## 9. Biên bản chạy thực tế của hướng dẫn này

| Bước đã thực hiện | Kết quả |
| --- | --- |
| `pip install -r requirements-dev.txt` trên `.venv` hiện có | PASS; các gói đã đúng phiên bản |
| `pip check` và `playwright install chromium` | PASS |
| Docker info + `setup_osrm.py --download` | PASS, nhánh sử dụng lại runtime đúng manifest |
| Khởi động lại Uvicorn tại 127.0.0.1:8000 | PASS |
| Health catalog/routing/basemap | Cả ba ready |
| So checksum PBF giữa catalog SQLite, routing và basemap | Trùng SHA-256 đã ghi ở mục 3 |
| Tuyến trực tiếp Đà Nẵng → gần Mỹ Khê | OSRM `Ok`, 5.206,3 m / 385,2 s |
| Pytest, Ruff, cú pháp 6 file JS | 134 PASS; Ruff/JS PASS |
| Audit dataset | PASS, 0 lỗi cứng, 4.818 cảnh báo |
| Smoke ba trang trước sửa | FAIL: `exploreFilters is not defined` ở Lịch trình |
| Smoke ba trang sau chuyển hàm sang mã bản đồ dùng chung | PASS toàn bộ, `javascript_errors: []` |
| Replay ban đầu gặp ảnh bị thay bằng ô dự phòng | Đã sửa script kiểm thử để cuộn theo thẻ POI ổn định, thay vì phần tử ảnh có thể bị thay thế |
| Replay bộ demo 11 bước + 3 lần lặp sau khởi động | PASS, khớp bằng chứng sàng lọc đã có |
| Cài hệ điều hành, fresh virtualenv trên máy trắng, tải/tiền xử lý PBF mới, rebuild/publish catalog | **NOT RUN** trong phiên này; hướng dẫn nhánh chuẩn bị riêng |

Bằng chứng cục bộ: [bản ghi startup](../artifacts/demo_startup_20260921/verification.json), [audit](../artifacts/demo_startup_20260921/audit.json), [log pytest](../artifacts/demo_startup_20260921/pytest.log), [log smoke sau sửa](../artifacts/demo_startup_20260921/smoke_web_after.log), [replay demo](../artifacts/demo_startup_20260921/demos/browser_report.json). Tệp trong `artifacts/` bị Git bỏ qua; có thể không hiện hữu trong bản clone mới.

Hướng dẫn này tập trung vận hành demo. Các công việc notebook, crawling và bảo trì dữ liệu dài hạn tiếp tục được mô tả trong [huong_dan_chay.md](huong_dan_chay.md).
