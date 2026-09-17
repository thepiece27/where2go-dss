# Where2Go DSS — gợi ý lịch trình trong ngày

Where2Go giúp chọn 2–5 điểm tham quan, sắp xếp giờ ghé và quay về điểm xuất phát bằng ô tô. Hệ thống dùng **Fuzzy AHP + TOPSIS** để xếp hạng và thuật toán chèn tham lam để tạo lịch trình; không giải bài toán tối ưu tuyến toàn cục.

Dữ liệu tập trung **Hà Nội** và **Đà Nẵng mới, bao gồm Quảng Nam cũ**. Người dùng có thể chọn điểm xuất phát ở địa phương khác, nhưng mức độ đầy đủ dữ liệu không được bảo đảm. Thiếu dữ liệu/không có đường được trả thành trạng thái rõ ràng. Giờ chưa biết tạo lịch trình **tạm tính**, không được tự coi là mở cả ngày.

## Chạy ứng dụng

Yêu cầu Python 3.13, Docker Desktop dùng Linux containers/WSL2; dành khoảng 8 GB RAM cho Docker khi dựng mạng đường toàn quốc và đủ dung lượng lưu snapshot/graph. Môi trường đã kiểm tra: Windows, Python 3.13.15, Docker 29.7.2, OSRM 5.27.1.

Từ thư mục gốc trong PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.lock.txt
.venv\Scripts\python.exe scripts/setup_osrm.py --download
.venv\Scripts\python.exe scripts/build_catalog.py
.venv\Scripts\python.exe scripts/validate_manual_data_v2.py
.venv\Scripts\python.exe scripts/build_catalog_v2.py
.venv\Scripts\python.exe scripts/export_quality_queue_v2.py
.venv\Scripts\python.exe scripts/export_priority_set_v2.py
.venv\Scripts\python.exe scripts/export_dataset_v2.py
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Mở **http://127.0.0.1:8000**. API tương tác: **http://127.0.0.1:8000/docs**. Web sử dụng API v2; API v1 được giữ để đối chiếu. Khi catalog thay đổi, khởi động lại API để nạp phiên bản mới. OSRM phục vụ trên cổng 5001, chỉ bind localhost; script không sửa container của dự án khác.

Snapshot mặc định là `vietnam-260915.osm.pbf`. Nếu Geofabrik ngừng lưu bản này, cần lấy bản lưu có đúng SHA256 hoặc chủ động tạo phiên bản dữ liệu mới và dựng lại cả catalog lẫn graph. Không đổi tên snapshot mới để giả làm bản cũ.

## Sử dụng

1. Chọn thành phố, tìm tên hoặc loại hình. Bộ lọc danh sách độc lập với chủ đề ưu tiên của lịch trình.
2. Nhấp bản đồ để đặt điểm xuất phát, hoặc nhập tọa độ. Chọn ngày, giờ bắt đầu/kết thúc, bán kính và sở thích.
3. Có thể sửa sáu phán đoán AHP cho bốn tiêu chí: sở thích, rating hiệu chỉnh, thời gian lái xe và độ tin cậy dữ liệu. CR vượt 0,1 sẽ bị từ chối.
4. Tạo lịch trình; đọc timeline, giờ quay về và cảnh báo. Lưu địa điểm bằng ID canonical.

OSRM không có giao thông trực tiếp. Thời lượng ghé là ước lượng, chưa tính tìm bãi đỗ/đi bộ từ đường tới cổng. Đây là công cụ hỗ trợ lập kế hoạch theo dữ liệu, không phải bảo đảm khả thi ngoài thực địa.

## Kiểm tra và tái lập kết quả

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/evaluate_v2.py
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe scripts/smoke_web.py
```

Ba lệnh cuối liên quan routing/web cần OSRM và, riêng smoke web, API đang chạy. Fixture trong pytest không thay thế nghiệm thu tuyến thật. Báo cáo nằm trong `data/reports/`, ảnh kiểm tra web nằm trong `artifacts/`.

## Cấu trúc và tài liệu

| Đường dẫn | Vai trò |
|---|---|
| `where2go/` | Lõi chung: catalog, AHP/TOPSIS, giờ mở cửa, OSRM, planner, API, metrics |
| `scripts/build_catalog.py` | Dựng catalog v1 làm baseline tương thích |
| `scripts/build_catalog_v2.py` | Hợp nhất quan sát đa nguồn, curation, giờ, rating, duration và quan hệ POI |
| `scripts/export_dataset_v2.py` | Xuất dataset local dễ đọc từ catalog v2 |
| `data/curation/` | Biên bản đối soát nguồn và registry ID bền vững |
| `data/reports/` | Coverage, hàng kiểm duyệt, kiểm tra đường bộ, kết quả nghiên cứu tình huống |
| `web/` | Giao diện gọi API Python; không tính xếp hạng độc lập |
| `tests/` | Kiểm thử hồi quy với dữ liệu fixture được gắn nhãn |
| `poi_recommendation_system.ipynb` | Notebook gọi đúng lõi sản phẩm |
| `notebooks/archive/`, `docs/archive/` | Tài liệu/mô hình lịch sử; không đại diện hệ thống hiện tại |

- [Phương pháp và công thức](docs/fuzzy_ahp.md)
- [Hướng dẫn triển khai, dữ liệu và demo](docs/huong_dan_trien_khai.md)
- [Kết quả kiểm tra và giới hạn](docs/ket_qua_trien_khai.md)
- [Kết quả triển khai v2](docs/ket_qua_trien_khai_v2.md)
- [Kế hoạch nâng cấp dữ liệu và lịch trình v2](docs/ke_hoach_nang_cap_du_lieu_va_lich_trinh_v2.md)
- [Kế hoạch đã thống nhất](docs/ke_hoach_hoan_thien_where2go_dss.md)
- [Review nền tảng ban đầu](docs/bao_cao_review_du_an_where2go_dss.md)

Các tài liệu cũ về Google/HOTOSM và mô hình hybrid được giữ để truy vết lịch sử. Notebook lưu trữ và workbook đánh giá cũ không dùng làm bằng chứng cho phiên bản hiện tại. Entry point scraper Google và sửa workbook legacy đã vô hiệu hóa; nguồn Excel gốc được giữ nguyên.

## Nguồn dữ liệu và ghi công

© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), dữ liệu theo ODbL 1.0; snapshot từ [Geofabrik](https://download.geofabrik.de/asia/vietnam.html). Manifest chứa ngày nguồn, checksum, phiên bản pipeline và registry. Khi công bố cơ sở dữ liệu phái sinh, cần giữ attribution, thông tin ODbL và thực hiện nghĩa vụ cung cấp dữ liệu theo giấy phép.

Địa giới dùng snapshot đã có trong repo từ [vietnamese-provinces-database](https://github.com/thanglequoc/vietnamese-provinces-database). Giờ bổ sung có URL nguồn trong từng biên bản. Không sao chép bài viết/ảnh của địa điểm để lấp thiếu dữ liệu. Quan sát Google được giữ theo trạng thái `restricted_internal`; bản ghi chờ kiểm duyệt nằm trong `data/private/`. API v2 chỉ phục vụ POI vượt quality gate theo mặc định, còn dữ liệu bị chặn vẫn được giữ để audit.

Chưa có nhãn người dùng độc lập: kết quả so sánh hiện tại là **kiểm thử và nghiên cứu tình huống**, không chứng minh Fuzzy AHP + TOPSIS vượt baseline.
