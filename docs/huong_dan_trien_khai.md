# Hướng dẫn triển khai và demo Where2Go DSS

Phạm vi: lịch trình ô tô một ngày, 2–5 POI, quay về điểm xuất phát; ưu tiên Hà Nội và Đà Nẵng mới. Tài liệu này đi cùng [công thức hiện hành](fuzzy_ahp.md) và [báo cáo kết quả](ket_qua_trien_khai.md).

## 1. Kiến trúc đang phục vụ

```text
Snapshot OSM + snapshot địa giới + reviews.json + id_registry.json
                         ↓ scripts/build_catalog.py
                 SQLite + CSV + manifest + audit
                         ↓ where2go/catalog.py
Lọc cứng → shortlist → OSRM Table → Fuzzy AHP/TOPSIS → chèn lịch → OSRM Route
                         ↓
           FastAPI / notebook / evaluator cùng một lõi
                         ↓
             Web: danh sách, bản đồ, timeline, lưu POI
```

Workbook Google cũ được đọc để kiểm kê, không hòa vào catalog công bố. `data/private/legacy_review.csv` ghi các dòng cần xem lại. Không sửa workbook/backup và không dùng bảng điểm lịch sử làm kết quả mới.

## 2. Chuẩn bị và khởi động

Python đã thử: 3.13.15 trên Windows. Docker Desktop phải chạy Linux containers/WSL2. Dựng graph quốc gia dùng bộ nhớ đáng kể; cấu hình script dành 6 GB RAM, 8 GB RAM+swap cho build, hai CPU; service giới hạn 5 GB RAM. Không giả định có Docker CLI là có daemon hoạt động.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.lock.txt
docker info
wsl --list --verbose
.venv\Scripts\python.exe scripts/setup_osrm.py --download
.venv\Scripts\python.exe scripts/build_catalog.py
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Lệnh API chạy ở terminal riêng. Truy cập http://127.0.0.1:8000; tài liệu hợp đồng tại `/docs`. Script OSRM pin image bằng digest, chạy `extract → partition → customize → routed`, dùng riêng volume `where2go-osrm-data`, container `where2go-osrm` và cổng localhost 5001. Không tác động container khác.

Snapshot mặc định `data/raw/vietnam-260915.osm.pbf`; checksum trong `data/reports/manifest.json`. `data/routing/manifest.json` chỉ được ghi sau preprocessing và route thực thành công. Catalog và router phải có cùng SHA256 PBF; khác nhau trả `routing_unavailable`.

Khi khởi động lại máy, mở Docker Desktop, chạy lại `setup_osrm.py` để kiểm tra graph/service đang có; sau đó chạy API. Khi sửa dữ liệu hoặc rebuild catalog, khởi động lại API vì catalog được cache trong tiến trình. Không xóa manifest để ép tái sử dụng graph không rõ phiên bản.

Nếu chuyển OSRM sang Linux tự quản lý, dùng cùng image/profile/PBF, đưa manifest tương ứng về `data/routing/manifest.json`, đặt `$env:OSRM_URL='http://dia-chi-may:5001'` trước khi chạy Python. Cổng service chỉ nên mở cho máy ứng dụng. Chưa có kiểm thử triển khai trên máy Linux thứ hai.

## 3. Pipeline dữ liệu và cách bổ sung

`build_catalog.py` nhập node/area OSM có tên và loại phù hợp, gán địa phương bằng polygon `covers`; không dùng địa phương gần nhất cho điểm nằm ngoài polygon. Địa giới hiện có gán Hội An vào Đà Nẵng. Area dùng representative point và được gắn nhãn **không phải lối vào**.

ID là `osm:<node|way|relation>:<id>`. Registry được version control tại `data/curation/id_registry.json`; phải mang theo khi tái tạo dữ liệu. Bản ghi đã có canonical ID không được tự đổi vì thứ tự import. Liên kết cũ mâu thuẫn hoặc canonical biến mất được đưa vào kiểm duyệt. Ghép mới chỉ xét cùng tên chuẩn hóa, địa phương, loại và tọa độ gần; đây vẫn là heuristic, chưa có đo precision độc lập.

Cache import gắn checksum PBF, địa giới và mã importer/parser/config. Thay quy tắc import sẽ tạo cache mới. Đọc header dùng `osmium.osm.NOTHING`, pool mặc định một worker để tránh treo thoát tiến trình đã gặp trên Windows. Không có lệnh tự tắt tiến trình hệ thống.

Các đầu ra cần đọc:

| File | Nội dung |
|---|---|
| `data/reports/catalog.csv` | Bảng kiểm kê canonical, trạng thái và URL nguồn |
| `data/reports/manifest.json` | Nguồn, checksum, pipeline, registry, audit legacy |
| `data/reports/coverage.json` | Số lượng theo địa phương, loại và tình trạng giờ |
| `data/reports/review_queue.json` | Điểm nghi vấn/trùng/bị loại cùng lý do |
| `data/reports/routing_audit.json` | Kiểm tra OSRM cho toàn bộ usable ở hai thành phố |
| `data/reports/reviewed_sample.json` | Mẫu có biên bản đối soát; ghi rõ chưa xác minh thực địa |
| `data/reports/enrichment_queue.csv` | POI và trường còn thiếu cần bổ sung, có ưu tiên |

Chiến lược bổ sung tiếp theo:

1. Ưu tiên mẫu đã đối soát và có đường, xác nhận giờ/cổng vào ở các cụm Hoàn Kiếm, Ba Đình–Tây Hồ, trung tâm Đà Nẵng, Hội An; sau đó mở rộng vùng còn ít loại hình phù hợp. Không mặc định mọi phường đều đủ dữ liệu.
2. Tìm nguồn chính thức của địa điểm/cơ quan quản lý. Lưu URL, ngày kiểm tra, trường đã đối soát, người/công cụ và giới hạn. Không tạo nhận xét/rating hoặc tự gán giờ khi thiếu nguồn.
3. Thêm biên bản vào `data/curation/reviews.json`. Phiên bản hiện tại cho phép override `hours_raw`; sửa tọa độ hoặc taxonomy cần mở rộng schema override, validation và fixture trước, không sửa SQLite bằng tay.
4. Rebuild, chạy audit/evaluator, so sánh coverage và hàng nghi vấn. Khởi động lại API. Nếu sửa tọa độ phải kiểm tra snap/lối vào; chưa tìm được bằng chứng thì giữ hàng chờ.

Ưu tiên 1 trong queue là các điểm có biên bản nguồn và có đường; ưu tiên 2 là điểm còn lại có đường; ưu tiên 3 là cần làm rõ đường đi. Queue không được dùng để tự nâng độ tin cậy.

`hours_status=known` trong catalog chỉ nói parser đọc được lịch tuần. Planner giải lại theo ngày: ngày lễ/ngoại lệ chưa được giải chắc chắn vẫn chuyển thành unknown. Hiện chỉ hỗ trợ một tập con bảo thủ của OSM opening_hours; chuỗi phức tạp được giữ nguyên và không suy đoán.

## 4. Kiểm thử

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q where2go scripts tests
.venv\Scripts\python.exe scripts/audit_focus.py
.venv\Scripts\python.exe scripts/evaluate_itineraries.py
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe scripts/smoke_web.py
```

Pytest chạy fixture không cần mạng: AHP/CR/hoán vị, TOPSIS biên, giờ đóng/nghỉ trưa/chờ/qua đêm/lễ, tuyến một chiều/không có đường, snap, lỗi dịch vụ, ID, tọa độ viewport, API và metrics. Playwright cần API và OSRM thật; kiểm tra save trước/sau lọc, tạo lịch, đổi loại hình, URL ảnh, lỗi JavaScript. Ảnh và báo cáo browser nằm trong `artifacts/`.

Notebook hiện tại gọi lõi Python, không có pipeline làm sạch/xếp hạng riêng. Mở với môi trường Jupyter tùy chọn; chạy cell từ gốc repo sau khi catalog và OSRM sẵn sàng. Bộ dependency app không bao gồm giao diện Jupyter.

## 5. Bốn kịch bản demo

Dùng ngày **20/09/2026**, khung **08:00–18:00**, bán kính **30 km**, phán đoán AHP đều bằng 1. Đây là ngày cố định để tái lập; khi demo ngày khác phải đọc lại kết quả giờ mở cửa.

| Mã | Địa phương | Xuất phát (lat, lon) | Sở thích |
|---|---|---|---|
| `hanoi_hoan_kiem` | Hà Nội | 21.0285, 105.8542 | văn hóa, lịch sử |
| `hanoi_west_lake` | Hà Nội | 21.0437, 105.8364 | thiên nhiên, văn hóa |
| `danang_center` | Đà Nẵng | 16.0612, 108.2227 | văn hóa, ngắm cảnh |
| `quangnam_hoi_an` | Đà Nẵng | 15.8794, 108.3278 | văn hóa, lịch sử |

Tạo lịch, chỉ ra giờ đến/bắt đầu/rời, thời gian chờ, chặng về và cảnh báo. Mở phần trọng số để giải thích ba tiêu chí. Thử một khung thời gian rất ngắn để thấy `insufficient_data`; thử phán đoán 9, 1/9, 9 để thấy lỗi CR. Không sửa dữ liệu để cố tạo ra ca unknown.

`scripts/evaluate_itineraries.py` chạy cả bốn baseline trên cùng pool/planner. Khi có nhãn độc lập, truyền `--judgments file.json`: object theo bốn mã kịch bản, mỗi giá trị là ánh xạ POI ID → độ liên quan 0..3. File phải bao phủ toàn bộ pool mỗi kịch bản. Lưu cách tuyển người chấm, thời gian, hướng dẫn chấm và phiên bản dữ liệu riêng; chưa có hồ sơ này thì không gọi đó là đánh giá người dùng đã hoàn thành.

## 6. Chẩn đoán lỗi và giới hạn

- `routing_unavailable`: kiểm tra `docker ps`, `docker logs where2go-osrm`, `/api/health`, URL và checksum manifest. Tuyệt đối không thay bằng thời gian chim bay.
- `insufficient_data`: xem `candidate_counts`, `excluded`, `reason`; có thể do bộ lọc, thiếu điểm có đường, snap xa, giờ đóng hoặc khung thời gian quá ngắn. Tăng bán kính/giờ là lựa chọn của người dùng, không tự nới ràng buộc.
- Nền bản đồ xám: kiểm tra thông báo trên bản đồ. Tile OSM và Leaflet CDN cần mạng; đường OSRM nội bộ vẫn có thể chạy. Không nhầm lỗi tile với lỗi tính đường, không tải hàng loạt tile để chữa lỗi DNS.
- Catalog thiếu: build trước khi chạy API. File SQLite là đầu ra có thể tái tạo, không phải nguồn để chỉnh sửa thủ công.
- Dữ liệu Google cũ: không truy cập qua API web; các entry point sửa workbook/crawl Google cũ đã dừng. Các module lưu trữ chỉ phục vụ truy vết lịch sử.

Các nguồn giờ bổ sung được ghi theo trường. Ví dụ Bảo tàng Phụ nữ công bố giờ hàng ngày 08:00–17:00 trên [website chính thức](https://baotangphunu.org.vn/phong-kham-pha/); đây là bằng chứng giờ công bố, chưa phải xác nhận mở cửa cho mọi ngày lễ. Attribution OSM phải được giữ khi chia sẻ catalog; không coi URL nguồn là giấy phép sao chép ảnh hoặc bài viết.
