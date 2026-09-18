# Where2Go DSS

Where2Go khám phá địa điểm trên toàn Việt Nam và hỗ trợ lựa chọn lịch trình ô tô trong ngày tại Hà Nội/Đà Nẵng mới, gồm địa bàn Quảng Nam cũ. Người dùng chọn tối đa 12 địa điểm, đánh dấu nơi nhất định phải ghé, so sánh các lịch rồi chỉnh thứ tự, thời lượng và giờ xuất phát. Nhà hàng/cà phê cũng có thể được chọn. Địa điểm đề xuất thêm mặc định chỉ được đưa vào khi người dùng tick.

Fuzzy AHP/TOPSIS hỗ trợ xếp hạng địa điểm gợi ý; beam search thử thứ tự ghé các điểm đã chọn. OSRM kiểm tra tuyến cho từng phương án, không có giao thông trực tiếp. Giờ và điểm tiếp cận chưa xác minh được ghi rõ. Khi không xếp đủ điểm, ứng dụng đưa phương án đổi giờ hoặc bớt điểm để người dùng quyết định; khi thiếu đường đi, ứng dụng giữ danh sách và đưa hành động điều chỉnh. Đây là tìm kiếm có giới hạn, không bảo đảm tối ưu toàn cục.

Luồng mới dùng `POST /api/v2/trip-suggestions` và `POST /api/v2/trip-recommendations`. Endpoint `/api/v2/itineraries` vẫn giữ planner cũ để tương thích/nghiên cứu. Xem [hợp đồng, thuật toán và báo cáo bàn giao](docs/trai_nghiem_lua_chon_lich_trinh.md).

## Chạy ứng dụng

Yêu cầu Python 3.13 và Docker Desktop/WSL2. Từ thư mục gốc trong PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.lock.txt
.venv\Scripts\python.exe scripts\setup_osrm.py --download
.venv\Scripts\python.exe scripts\build_local_basemaps.py
.venv\Scripts\python.exe scripts\build_national_basemap.py
.venv\Scripts\python.exe scripts\build_catalog.py
.venv\Scripts\python.exe scripts\validate_manual_data_v2.py
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py --publish
.venv\Scripts\python.exe scripts\export_quality_queue_v2.py
.venv\Scripts\python.exe scripts\export_priority_set_v2.py
.venv\Scripts\python.exe scripts\inventory_sources_v2.py
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`; OpenAPI tại `http://127.0.0.1:8000/docs`. OSRM chạy cục bộ tại `127.0.0.1:5001`.

## Dataset hiện hành

- Catalog chuẩn: `data/catalog_v2.sqlite`.
- Bản CSV/JSON và workbook tổng hợp `merged_dataset.xlsx`: `data/reports/v2/dataset/`.
- Tập ưu tiên và hàng kiểm duyệt: `data/reports/v2/priority_set.csv`, `data/reports/v2/quality_queue.csv`.
- Quan sát Google nội bộ: `data/private/google_enrichment_v2.csv`, `data/private/google_opening_hours_v2.csv`.
- Workbook kiểm duyệt: `data/manual/poi_enrichment_v2.xlsx`.
- Nguồn cần giữ để rebuild: baseline `data/catalog.sqlite`, OSM PBF, địa giới, ba workbook Google/HOTOSM, `data/curation/`, workbook kiểm duyệt, `data/enrichment/` và cache hiện hành. Workbook `data/vietnam_destinations.xlsx` không phải đầu vào bắt buộc của pipeline hiện hành.

Ba Excel được hợp nhất theo thực thể và từng trường; web đọc SQLite. Dữ liệu khám phá được tách khỏi điều kiện lập lịch trình, có tìm bí danh không dấu, ảnh có nguồn và bản đồ toàn quốc. Xem số liệu đo trên catalog mới trong [báo cáo triển khai](docs/ket_qua_trien_khai_v2.md), cùng [quy trình hợp nhất, thu thập và hoàn tác](docs/du_lieu_hop_nhat_va_ban_do.md).

Nguồn Google được đánh dấu `restricted_internal`; không coi các CSV nội bộ là dataset được phép tái phân phối. Dữ liệu OSM theo ODbL 1.0 và phải giữ attribution.

## Kiểm tra

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
node --check web\app.js
node --check web\map.js
node --check web\dataset.js
.venv\Scripts\python.exe scripts\evaluate_v2.py
.venv\Scripts\python.exe scripts\evaluate_trip_choices.py
.venv\Scripts\python.exe scripts\smoke_explore_v2.py
.venv\Scripts\python.exe scripts\smoke_web.py
```

Evaluator và smoke lịch trình cần OSRM; hai smoke cần API đang chạy. Smoke khám phá kiểm tra riêng online và chặn mạng ngoài. Kết quả evaluator chỉ là nghiên cứu tình huống vì chưa có nhãn độc lập hoàn chỉnh.

## Cấu trúc chính

| Đường dẫn | Vai trò |
|---|---|
| `where2go/v2/` | Catalog, taxonomy, quality gate, ranking, planner và service v2 |
| `where2go/api.py` | API v1 đối chiếu, API v2 và frontend assets |
| `scripts/build_catalog_v2.py` | Hợp nhất nguồn, curation, giờ, rating, duration và quan hệ POI |
| `scripts/audit_dataset_v2.py` | Kiểm tra SQLite, export, ID, tọa độ, giờ, rating và coverage |
| `scripts/evaluate_v2.py` | 16 kịch bản x 4 phương pháp trên cùng lõi v2 |
| `where2go/v2/trips.py`, `trip_models.py` | Đề xuất điểm, lịch nhiều phương án và hợp đồng chọn tối đa 12 điểm |
| `scripts/evaluate_trip_choices.py` | Đối chiếu planner cũ/mới trên bảy kịch bản có chủ đích với OSRM thật |
| `scripts/smoke_trip_choices.py` | Luồng chọn/so sánh/chỉnh lịch, lưu nháp, phản hồi cũ và mobile |
| `web/` | Leaflet local, nền online toàn quốc, địa giới dự phòng và nền local chi tiết Hà Nội/Đà Nẵng |
| `scripts/build_local_basemaps.py` | Cắt OSM PBF theo địa giới, gộp lớp hình học và tạo GeoJSON gzip cho web |
| `tests/` | Kiểm thử toán học, dữ liệu, planner, routing và API |

Tài liệu đang dùng:

- [Phương pháp và công thức](docs/fuzzy_ahp.md)
- [Trải nghiệm chọn lịch, API mới và kết quả kiểm thử](docs/trai_nghiem_lua_chon_lich_trinh.md)
- [Hướng dẫn dữ liệu, triển khai và demo](docs/huong_dan_trien_khai.md)
- [Kết quả, đánh giá và giới hạn](docs/ket_qua_trien_khai_v2.md)
- [Hợp nhất dữ liệu, ảnh và bản đồ toàn quốc](docs/du_lieu_hop_nhat_va_ban_do.md)
- [Kế hoạch phát triển v2](docs/ke_hoach_nang_cap_du_lieu_va_lich_trinh_v2.md)
- [Mục lục tài liệu](docs/README.md)
