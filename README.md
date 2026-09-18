# Where2Go DSS

Where2Go gợi ý lịch trình ô tô trong ngày cho Hà Nội và Đà Nẵng mới, gồm địa bàn Quảng Nam cũ. Người dùng chọn điểm xuất phát, ngày, khung giờ, sở thích và nhịp đi; hệ thống xếp hạng POI bằng AHP/TOPSIS, chèn 1-5 điểm tham quan, bữa ăn/nghỉ và đường quay về.

Đây là hệ hỗ trợ quyết định theo dữ liệu hiện có. OSRM không có giao thông trực tiếp; giờ, thời lượng và điểm tiếp cận chưa xác minh làm kết quả mang trạng thái `provisional`. Thuật toán chèn là heuristic có ràng buộc, không phải tối ưu tuyến toàn cục.

## Chạy ứng dụng

Yêu cầu Python 3.13 và Docker Desktop/WSL2. Từ thư mục gốc trong PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.lock.txt
.venv\Scripts\python.exe scripts\setup_osrm.py --download
.venv\Scripts\python.exe scripts\build_local_basemaps.py
.venv\Scripts\python.exe scripts\build_catalog.py
.venv\Scripts\python.exe scripts\validate_manual_data_v2.py
.venv\Scripts\python.exe scripts\build_catalog_v2.py
.venv\Scripts\python.exe scripts\export_quality_queue_v2.py
.venv\Scripts\python.exe scripts\export_priority_set_v2.py
.venv\Scripts\python.exe scripts\export_dataset_v2.py
.venv\Scripts\python.exe scripts\audit_dataset_v2.py
.venv\Scripts\python.exe scripts\inventory_sources_v2.py
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`; OpenAPI tại `http://127.0.0.1:8000/docs`. OSRM chạy cục bộ tại `127.0.0.1:5001`.

## Dataset hiện hành

- Catalog chuẩn: `data/catalog_v2.sqlite`.
- Bản CSV/JSON để đọc: `data/reports/v2/dataset/`.
- Tập ưu tiên và hàng kiểm duyệt: `data/reports/v2/priority_set.csv`, `data/reports/v2/quality_queue.csv`.
- Quan sát Google nội bộ: `data/private/google_enrichment_v2.csv`, `data/private/google_opening_hours_v2.csv`.
- Workbook kiểm duyệt: `data/manual/poi_enrichment_v2.xlsx`.
- Nguồn cần giữ để rebuild: OSM PBF, địa giới, ba workbook Google/HOTOSM, `data/vietnam_destinations.xlsx`, `data/curation/` và cache OSM hiện hành.

Dataset hiện tại là `v2-91f833f05c8c7ef8`, gồm 15.713 POI. Audit PASS với 0 lỗi cấu trúc, nhưng thiếu dữ liệu vẫn lớn: 335 POI phục vụ chưa biết giờ, 1.439 thiếu cặp rating hợp lệ, và toàn bộ 1.536 POI phục vụ chưa có duration/access được người kiểm duyệt xác minh. Xem số liệu đầy đủ trong [báo cáo triển khai](docs/ket_qua_trien_khai_v2.md).

Nguồn Google được đánh dấu `restricted_internal`; không coi các CSV nội bộ là dataset được phép tái phân phối. Dữ liệu OSM theo ODbL 1.0 và phải giữ attribution.

## Kiểm tra

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
node --check web\app.js
.venv\Scripts\python.exe scripts\evaluate_v2.py
.venv\Scripts\python.exe scripts\smoke_web.py
```

Hai lệnh cuối cần OSRM; smoke web cần API đang chạy. Kết quả evaluator hiện chỉ là nghiên cứu tình huống vì chưa có nhãn độc lập hoàn chỉnh.

## Cấu trúc chính

| Đường dẫn | Vai trò |
|---|---|
| `where2go/v2/` | Catalog, taxonomy, quality gate, ranking, planner và service v2 |
| `where2go/api.py` | API v1 đối chiếu, API v2 và frontend assets |
| `scripts/build_catalog_v2.py` | Hợp nhất nguồn, curation, giờ, rating, duration và quan hệ POI |
| `scripts/audit_dataset_v2.py` | Kiểm tra SQLite, export, ID, tọa độ, giờ, rating và coverage |
| `scripts/evaluate_v2.py` | 16 kịch bản x 4 phương pháp trên cùng lõi v2 |
| `web/` | Giao diện dùng API v2; Leaflet và basemap Hà Nội/Đà Nẵng đều chạy local |
| `scripts/build_local_basemaps.py` | Cắt OSM PBF theo địa giới, gộp lớp hình học và tạo GeoJSON gzip cho web |
| `tests/` | Kiểm thử toán học, dữ liệu, planner, routing và API |

Tài liệu đang dùng:

- [Phương pháp và công thức](docs/fuzzy_ahp.md)
- [Hướng dẫn dữ liệu, triển khai và demo](docs/huong_dan_trien_khai.md)
- [Kết quả, đánh giá và giới hạn](docs/ket_qua_trien_khai_v2.md)
- [Kế hoạch phát triển v2](docs/ke_hoach_nang_cap_du_lieu_va_lich_trinh_v2.md)
- [Mục lục tài liệu](docs/README.md)
