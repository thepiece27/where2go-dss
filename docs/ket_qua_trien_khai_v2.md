# Kết quả triển khai Where2Go DSS v2

**Ngày chốt lần chạy:** 18/09/2026  
**Dataset:** `v2-c829c8f3e2414108`  
**Phạm vi ưu tiên:** Hà Nội và Đà Nẵng mới, gồm địa bàn Quảng Nam cũ  
**Trạng thái chung:** Chạy được end-to-end; dữ liệu đủ để nghiên cứu tình huống và demo có cảnh báo, chưa đạt mức xác minh thực địa.

## 1. Kết quả kỹ thuật

Pipeline v2 đã có catalog đa nguồn, provenance theo quan sát, quality gate, Fuzzy AHP + TOPSIS bốn tiêu chí, planner có đường về, giờ, thời lượng, ăn/nghỉ và dự phòng. API v1 vẫn tồn tại để đối chiếu; web sử dụng `/api/v2/*`.

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Catalog SQLite v2 và CSV local | PASS | 15.713 POI; `data/catalog_v2.sqlite`; `data/reports/v2/dataset/` |
| ID bền vững và provenance | PASS | Source file, source record, field observation, selected field trong SQLite |
| Google collector có resume | PASS kỹ thuật | `noworneverev/google-maps-scraper` tại commit đã pin trong code; 20 bản ghi được xác nhận chéo tự động |
| Kiểm duyệt Google bởi người ở ngưỡng 95% | NOT RUN | Chưa có người kiểm tra độc lập đủ mẫu pilot |
| OSM/OSRM cùng snapshot | PASS | OSRM container trả tuyến và health báo `routing=ready` |
| Fuzzy AHP/TOPSIS v2 | PASS kiểm thử | Kiểm tra CR, hoán vị tiêu chí, missing rating và TOPSIS biên |
| Planner v2 | PASS kiểm thử | 64/64 lượt evaluator trả lịch `provisional` |
| API/web desktop và mobile | PASS | Smoke test tạo lịch, sửa duration, thematic mode, tile failure và mobile 390x844 |
| Chủ dự án chấm 12 holdout | NOT RUN | Evaluator chưa có phiếu chấm hoàn chỉnh |
| Khảo sát người dùng độc lập | NOT RUN | Chưa thu nhãn người dùng |

Không có kết quả nào trong tài liệu này chứng minh Fuzzy AHP vượt baseline về chất lượng cảm nhận. Evaluator mới xác nhận các phương pháp cùng chạy trên kịch bản và tạo được đầu ra.

## 2. Dataset đang dùng

Catalog chuẩn là `data/catalog_v2.sqlite`. Bộ dễ đọc nằm tại:

| File | Nội dung |
|---|---|
| `data/reports/v2/dataset/pois.csv` | Một dòng cho mỗi POI, category, tọa độ, trạng thái và quality gate |
| `data/reports/v2/dataset/opening_hours.csv` | Khoảng giờ cấu trúc; ngày thiếu giữ `unknown`, chỉ 24/7 khi nguồn nói rõ |
| `data/reports/v2/dataset/ratings.csv` | Rating và review count theo quan sát; `same_observation=1` mới dùng để xếp hạng |
| `data/reports/v2/dataset/duration_profiles.csv` | Mức ngắn/thông thường/dài và phương pháp tạo |
| `data/reports/v2/dataset/access_points.csv` | Điểm tiếp cận và trạng thái xác minh |
| `data/reports/v2/dataset/sources.csv` | Nguồn, checksum, vai trò và quyền sử dụng |
| `data/reports/v2/dataset/summary.json` | Coverage toàn catalog và tập ưu tiên |

Dữ liệu Google chờ xử lý được lưu riêng tại `data/private/google_enrichment_v2.csv` và `data/private/google_opening_hours_v2.csv`. Thư mục này bị Git bỏ qua. Quan sát Google là `restricted_internal`, không phải bộ dữ liệu công khai để tái phân phối.

Workbook kiểm tra `data/manual/poi_enrichment_v2.xlsx` hiện có 80 seed, 147 dòng giờ và 20 bản ghi `tool_confirmed`. Số bản ghi `confirmed` bởi người là 0. `tool_confirmed` chỉ có nghĩa URL địa điểm và nguồn chéo khớp bằng công cụ, không thay thế kiểm duyệt người.

## 3. Coverage thực tế

### 3.1. Toàn catalog ưu tiên theo địa phương

| Chỉ số | Hà Nội | Đà Nẵng |
|---|---:|---:|
| POI usable | 4.474 | 2.682 |
| POI serviceable mặc định | 802 | 504 |
| Điểm tham quan serviceable | 113 | 69 |
| Ăn/nghỉ serviceable | 689 | 435 |
| Có cặp rating/review hợp lệ | 67 | 29 |
| Có giờ cấu trúc | 611 | 414 |
| Có đủ bảy ngày giờ | 580 | 392 |
| Có hồ sơ duration riêng | 15 | 17 |
| Duration đã xác minh | 0 | 0 |
| Điểm tiếp cận đã xác minh | 0 | 0 |

### 3.2. Tập ưu tiên 70 POI mỗi thành phố

| Chỉ số | Hà Nội | Đà Nẵng | Mục tiêu |
|---|---:|---:|---:|
| Tham quan | 50 | 50 | 50 |
| Ăn/nghỉ | 20 | 20 | 20 |
| Có giờ cấu trúc | 65,71% | 62,86% | 80% |
| Có hồ sơ duration riêng/ước lượng | 30% | 34% | Theo dõi riêng |
| Duration đã xác minh | 0% | 0% | 80% |
| Có cặp rating/review | 25 | 24 | Không bịa để đạt tỷ lệ |

Số POI đã đủ, nhưng coverage giờ, duration xác minh và access xác minh chưa đạt. Vì vậy giao diện hiển thị `CHƯA ĐẠT`, và lịch có dữ liệu chưa chắc chắn mang trạng thái `provisional`.

## 4. Các sửa lỗi quan trọng

- Ngày không được nguồn nêu trong chuỗi giờ giữ `unknown`; không tự chuyển thành đóng cửa.
- Google tool-confirmed thay lịch OSM cũ của cùng POI, tránh nối khoảng giờ lặp.
- Chỉ `Open 24 hours` hoặc nguồn tương đương mới tạo khoảng 00:00–24:00.
- Rating Google có độ chính xác bất thường như `4.97` bị loại khỏi ranking.
- Missing rating nhận giá trị trung tính, không dùng prior nhà cung cấp như rating thật.
- Category là ưu tiên mềm; thematic mode mới là ràng buộc chỉ chọn category đã chỉ định.
- POI cha/con không được chọn thành nhiều lượt ghé trùng trải nghiệm.
- Cơ sở văn hóa-thể thao bị gắn nhầm `park`, tên kỹ thuật và tên dạng khoảng cách bị quality gate chặn.
- `/api/v2/pois` mặc định chỉ trả POI serviceable; dữ liệu bị chặn vẫn còn trong dataset để audit.
- Coverage tách hồ sơ duration riêng khỏi duration đã xác minh; mục tiêu 80% dựa trên phần đã xác minh.
- Dataset version băm cả dữ liệu curation và code biến đổi quan trọng để tránh nội dung đổi nhưng version giữ nguyên.

## 5. Kết quả kiểm thử

Lần chạy cuối:

```text
pytest: 55 passed, 1 deprecation warning từ Starlette TestClient
pip check: No broken requirements found
node --check web/app.js: PASS
OSRM route probe: Ok
evaluator: 16 kịch bản x 4 phương pháp = 64/64 provisional
web smoke: PASS desktop và mobile; không có page error
```

Smoke web đã kiểm tra lưu POI, tạo lịch, sửa thời lượng và tính lại ở backend, tách bộ lọc danh sách khỏi chủ đề lịch, thematic mode, mất tile OSM và responsive mobile. Tile nền ngoài mạng không tải được trong lần chạy; ứng dụng đã hiện cảnh báo và OSRM/API vẫn hoạt động.

## 6. Việc còn phải làm để đạt mục tiêu dữ liệu

1. Người kiểm duyệt xác nhận danh tính, giờ, duration và access cho tập ưu tiên; cập nhật workbook nguồn rồi rebuild, không sửa CSV dẫn xuất.
2. Bổ sung giờ cho ít nhất 10 POI Hà Nội và 12 POI Đà Nẵng trong tập ưu tiên để đạt mốc 80% trên 70 POI.
3. Thu bằng chứng duration riêng cho ít nhất 40/50 điểm tham quan mỗi thành phố; hiện chưa có hồ sơ nào mang `verified_at`.
4. Xác minh điểm đỗ/cổng tiếp cận. OSRM tìm được đường không chứng minh cổng thực tế sử dụng được.
5. Hoàn thành phiếu chấm 12 holdout rồi mới tính so sánh phương pháp; chỉ dùng AP/NDCG khi có nhãn POI độc lập.
6. Làm mới dữ liệu có mục tiêu theo hàng thiếu; dừng khi CAPTCHA/chặn truy cập, không xây cơ chế vượt chặn.

## 7. Lệnh tái lập

```powershell
.venv\Scripts\python.exe scripts\validate_manual_data_v2.py
.venv\Scripts\python.exe scripts\build_catalog_v2.py
.venv\Scripts\python.exe scripts\export_quality_queue_v2.py
.venv\Scripts\python.exe scripts\export_priority_set_v2.py
.venv\Scripts\python.exe scripts\export_dataset_v2.py
.venv\Scripts\python.exe scripts\inventory_sources_v2.py
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\evaluate_v2.py
.venv\Scripts\python.exe scripts\smoke_web.py
```

API và OSRM phải chạy khi thực hiện evaluator/smoke. Health hiện hành: `GET /api/health`. Dataset tải qua `GET /api/v2/dataset` và `GET /api/v2/dataset/{filename}`.
