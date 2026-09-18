# Hướng dẫn triển khai, dữ liệu và kiểm tra

## 1. Vai trò dữ liệu

Không sửa trực tiếp CSV trong `data/reports/v2/dataset/`; đây là đầu ra dẫn xuất.

| Nhóm | File/thư mục | Xử lý |
|---|---|---|
| Nguồn gốc | `data/vietnam_destinations*.xlsx`, `data/raw/*.pbf`, file địa giới | Giữ bất biến; dùng để rebuild |
| Curation | `data/curation/` | Quy tắc/biên bản có kiểm soát, được version hóa |
| Quan sát thủ công | `data/manual/poi_enrichment_v2.xlsx` | Sửa tại đây rồi validate/rebuild |
| Quan sát Google | `data/enrichment/`, `data/google-pilot/`, `data/google-focus-resolved/`, `data/private/google_*.csv` | Raw/checkpoint, kết quả đối chiếu và `restricted_internal` |
| Runtime | `data/catalog.sqlite`, `data/catalog_v2.sqlite`, `data/cache/`, `data/routing/` | Có thể tái tạo, không chỉnh tay |
| Báo cáo | `data/reports/v2/` | Dataset đọc, audit, quality queue và evaluation |

Giờ thiếu được giữ `unknown`. Chỉ ghi cả ngày khi nguồn nói rõ `24/7` hoặc `Open 24 hours`; không suy từ việc không tìm thấy giờ.

## 2. Build đầy đủ

```powershell
.venv\Scripts\python.exe scripts\setup_osrm.py --download
.venv\Scripts\python.exe scripts\build_local_basemaps.py
.venv\Scripts\python.exe scripts\build_national_basemap.py
.venv\Scripts\python.exe scripts\build_catalog.py
.venv\Scripts\python.exe scripts\validate_manual_data_v2.py
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py --publish
.venv\Scripts\python.exe scripts\export_quality_queue_v2.py
.venv\Scripts\python.exe scripts\export_priority_set_v2.py
.venv\Scripts\python.exe scripts\inventory_sources_v2.py
```

`build_catalog.py` tạo baseline v1 vì v2 còn nhập ID/provenance từ catalog này. Báo cáo baseline mới nằm trong `data/reports/v1/` và bị Git bỏ qua; sản phẩm dùng `data/reports/v2/`.

OSRM, catalog và basemap **local chi tiết** phải dùng cùng SHA256 PBF. Nền online toàn quốc độc lập với snapshot routing. Manifest routing chỉ được ghi sau khi route probe thành công. Nền local chi tiết nằm tại `web/data/basemap-{hanoi,danang}.json.gz`; API từ chối phục vụ lớp này nếu checksum không khớp catalog hoặc OSRM.

Với workspace hiện tại, giữ baseline `data/catalog.sqlite` để dựng v2; lệnh `build_catalog.py` chỉ cần khi xây lại baseline và có đủ nguồn gốc. Quy trình ảnh, thu thập có checkpoint, staging/publish và hoàn tác được mô tả tại [Dữ liệu hợp nhất và bản đồ](du_lieu_hop_nhat_va_ban_do.md).

## 3. Chạy API và web

```powershell
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

- Web: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health: `GET /api/health`
- Dataset: `GET /api/v2/dataset`
- POI serviceable: `GET /api/v2/pois`
- Khám phá toàn quốc: `GET /api/v2/pois?view=explore&offset=0`
- Marker theo vùng nhìn: `GET /api/v2/map-pois?bbox=102,7,118,24`
- Gợi ý địa điểm cho chuyến đi: `POST /api/v2/trip-recommendations`
- Lịch nhiều phương án trên giao diện: `POST /api/v2/trip-suggestions`
- Lịch trình planner cũ cho tương thích/nghiên cứu: `POST /api/v2/itineraries`
- Trang thông tin dữ liệu: `/dataset.html`
- Basemap local: `GET /api/v2/basemaps/hanoi`, `GET /api/v2/basemaps/danang`

API nạp catalog lúc khởi động. Sau rebuild phải restart uvicorn.

## 4. Làm giàu có mục tiêu

1. Lấy hàng ưu tiên từ `data/reports/v2/priority_set.csv` và `quality_queue.csv`.
2. Xác định đúng thực thể trước khi nhập rating, giờ, duration hoặc access.
3. Ghi rating và review count trong cùng quan sát.
4. Giờ tuần phải phân biệt `open`, `closed`, `unknown`; không lấy phần trăm đông khách làm giờ.
5. Duration cần short/typical/long, nguồn và phương pháp. `category_default` chỉ là fallback.
6. Tách tọa độ POI với cổng/bãi đỗ. OSRM tìm được đường không phải xác minh cổng thực tế.
7. Chạy validator, rebuild và audit sau mỗi lô.

Collector Google chỉ phục vụ pilot/đối soát có kiểm soát. Khi gặp CAPTCHA hoặc chặn truy cập thì dừng và ghi lỗi; không xây cơ chế vượt chặn.

## 5. Kiểm tra

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
node --check web\app.js
node --check web\map.js
node --check web\dataset.js
.venv\Scripts\python.exe scripts\audit_dataset_v2.py
.venv\Scripts\python.exe scripts\evaluate_v2.py
.venv\Scripts\python.exe scripts\evaluate_trip_choices.py
.venv\Scripts\python.exe scripts\smoke_explore_v2.py
.venv\Scripts\python.exe scripts\smoke_web.py
```

Evaluator cần OSRM. Smoke cần API mới khởi động và Chromium Playwright. Ảnh/số liệu smoke nằm trong `artifacts/`; đây là artifact tái sinh.

`smoke_web.py` hiện gọi bộ smoke luồng người dùng `smoke_trip_choices.py`. Có thể dùng `--url http://127.0.0.1:8001` để kiểm tra API riêng. Nháp mới dùng localStorage `where2go-trip-v1:<địa phương>`, độc lập với `where2go-saved-v2`. Thay code planner chỉ cần restart API, không cần rebuild/crawl dữ liệu. Xem [báo cáo và hợp đồng luồng mới](trai_nghiem_lua_chon_lich_trinh.md).

## 6. Chẩn đoán

- `routing_unavailable`: kiểm tra container `where2go-osrm`, port 5001 và SHA256 trong hai manifest.
- `choose_places`: chọn ít nhất một địa điểm; `adjustment_needed`: đọc `issues` và `actions` của API mới. `suggestions` có thể chứa phương án cần xác nhận đổi giờ/bớt điểm bắt buộc; không coi mọi phương án là đáp ứng nguyên yêu cầu.
- `insufficient_data`: xem `reason`, `candidate_counts`, `excluded_candidates`; thường do bộ lọc, bán kính, giờ, access hoặc đường về.
- Bản đồ nền xám: kiểm tra `basemap` trong `/api/health`, các file `web/data/basemap-*.json.gz` và checksum PBF trong `web/data/basemap-manifest.json`. Chạy lại `scripts/build_local_basemaps.py` rồi restart API nếu đổi snapshot OSM.
- Audit FAIL: xử lý lỗi cứng trước khi chạy demo. Warning là hàng làm giàu, nhưng phải báo trung thực.
- Dataset version không đổi sau sửa code/data quan trọng: kiểm tra danh sách input hash trong `build_catalog_v2.py`.
