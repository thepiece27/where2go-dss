# Dữ liệu hợp nhất và bản đồ Việt Nam

Ứng dụng khám phá POI trên toàn quốc; lập lịch trình ô tô trong ngày tại Hà Nội và Đà Nẵng mới. Catalog SQLite là nguồn phục vụ API. Các Excel là quan sát nguồn, không được web đọc trực tiếp.

## Nguồn và nguyên tắc hợp nhất

Ba workbook Google/HOTOSM được giữ nguyên. Bản chính có 8.201 dòng; mỗi backup có 8.710 dòng. Hợp của STT là 8.710, vì các file chứa nhiều phiên bản của cùng dữ liệu. Pipeline giữ sheet, số dòng, checksum và payload nguồn, rồi ghép bằng tên/bí danh, loại hình, ID Google và vị trí trên toàn quốc.

Thứ tự build: baseline OSM → bổ sung OSM → workbook kiểm duyệt → curation → quan sát crawl đã đối chiếu → Excel cũ → kiểm tra ảnh → tính lại trạng thái. Nguồn cũ chỉ bổ sung trường trống; không ghi đè nguồn đã được chọn từ bước kiểm duyệt. Quan sát mới không xóa payload cũ.

- ID canonical hiện hành được giữ. Một tên có thể chỉ nhiều địa điểm khác nhau; một địa điểm có nhiều tên Việt–Anh.
- POI dạng điểm chỉ tự ghép trong 300 m. Khu vực lớn có thể dùng hình học OSM hoặc bằng chứng cụ thể từ website địa điểm.
- Dòng có tỉnh mâu thuẫn giữa các snapshot, nhiều ứng viên hoặc ID ngoài xung đột nằm trong hàng kiểm tra.
- Có thể tạo POI Google mới khi tên gốc và tên panel khớp, có ID thực thể, loại hình, tọa độ nằm trong địa phương và không có ứng viên gần tương tự. Trường hợp chưa đủ bằng chứng tiếp tục chờ đối chiếu.
- Thời điểm thu thập chưa biết được giữ `null`. Ngày backup và thời gian sửa file không trở thành ngày thu thập hay xác minh.
- Rating và số review kế thừa từ Excel được giữ để truy nguyên với `same_observation=0`; chúng không tham gia xếp hạng như một cặp đã xác nhận. Quan sát mới trên cùng panel mới có thể tạo cặp hợp lệ.
- Điểm bản đồ Google lấy từ tọa độ thực thể hoặc marker đang được chọn, không lấy tâm khung nhìn `@lat,lng`. Điểm này vẫn chưa phải cổng/bãi đỗ đã xác minh.
- `tool_confirmed` là kết quả đối chiếu bằng công cụ; không phải kiểm duyệt bởi người hay khảo sát thực địa.

## Ảnh

URL ảnh có bảng riêng, nguồn, liên kết POI, trạng thái kiểm tra và kích thước. Loại URL ảnh hồ sơ `/ogw/`, avatar, logo và ảnh quá nhỏ. Bộ kiểm tra đọc nội dung thật, kiểu MIME, kích thước, giới hạn dung lượng và chuyển hướng; HTTP 200 riêng lẻ không đủ.

Chỉ ảnh liên kết với thực thể và kiểm tra nội dung thành công mới được chọn. URL dùng chung cho nhiều thực thể được giữ lại để kiểm tra. Giao diện tải lười, hiển thị nguồn ảnh và thay bằng thông báo khi URL hết hạn. Kiểm tra kỹ thuật không thay thế việc duyệt nội dung từng ảnh bởi người.

Ảnh Google kế thừa dùng nhãn `legacy_entity_link`; ảnh lấy từ panel trong đợt mới dùng `entity_panel`. Ảnh website, Bing hoặc link rút gọn trong cùng dòng Excel vẫn giữ để đối chiếu, chưa tự được coi là ảnh đúng địa điểm.

```powershell
.venv\Scripts\python.exe scripts\validate_images_v2.py --catalog artifacts\dataset-build\catalog_v2.sqlite
# Kiểm tra lại cả những URL từng hợp lệ:
.venv\Scripts\python.exe scripts\validate_images_v2.py --catalog data\catalog_v2.sqlite --refresh
```

Cache kết quả ở `data/cache/image_checks_v2.json`. Rebuild để áp dụng các kết quả mới vào catalog.

## Thu thập bổ sung có giới hạn

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-enrichment.txt
.venv\Scripts\python.exe -m playwright install firefox chromium
.venv\Scripts\python.exe scripts\prepare_enrichment_v2.py
.venv\Scripts\python.exe scripts\collect_enrichment_v2.py --seeds data\enrichment\seeds.json --output data\enrichment\pilot.json --limit 20
.venv\Scripts\python.exe scripts\review_enrichment_v2.py --input data\enrichment\pilot.json --output data\enrichment\accepted-pilot.json --report data\reports\v2\collection_pilot.json
```

Collector dùng trình duyệt thông thường, chạy tuần tự, giữ kết quả từng lần thử và dừng nếu gặp yêu cầu xác minh truy cập. `--retry` mặc định chỉ thử lại `transient_error,unresolved`; có thể dùng `--retry-status partial,needs_review` khi đã có thay đổi phù hợp để giải quyết nguyên nhân.

Adapter nằm trong `where2go/v2/google_collector.py`; thư viện ngoài chỉ cung cấp parser DOM, được pin commit trong `requirements-enrichment.txt`. Không sửa mã bên trong `.venv`. Tên gần giống không tự được review chấp nhận: cần quyết định đối chiếu riêng có bằng chứng trong CSV curation.

Lệnh có `--limit` lớn hơn 20 yêu cầu báo cáo pilot đạt ít nhất 19/20 kết quả được đối chiếu. Mỗi lô tối đa 200 POI. Các file `accepted*.json` được importer đọc; chỉ hàng có `accepted=true` và danh tính `tool_confirmed` được nhập. Quyết định bổ sung có bằng chứng nằm trong `data/curation/collection_identity_reviews_v2.csv`.

Kết quả `complete` chỉ nói collector đã lấy đủ nhóm trường yêu cầu; bước review độc lập vẫn có thể không chấp nhận danh tính. Kết quả chưa rõ không bị đổi thành thành công để tăng tỷ lệ.

## Build, kiểm tra và xuất bản local

```powershell
.venv\Scripts\python.exe scripts\extract_poi_geometry_v2.py
.venv\Scripts\python.exe scripts\build_national_basemap.py
.venv\Scripts\python.exe -m pytest -q
node --check web\app.js
node --check web\map.js
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py
# Chỉ thay dữ liệu đang dùng sau khi build và audit đạt:
.venv\Scripts\python.exe scripts\rebuild_dataset_v2.py --publish
```

Build riêng nằm tại `artifacts/dataset-build/`. Khi publish, bản trước được sao lưu dưới `artifacts/dataset-backups/<timestamp>/`. SQLite được thay sau khi export và audit đạt. Cần khởi động lại API để nạp thế hệ dữ liệu mới.

Để kiểm tra tái lập như đợt bàn giao này, chạy `scripts/report_merge_v2.py --catalog artifacts/dataset-build/catalog_v2.sqlite --dataset artifacts/dataset-build/dataset --output artifacts/staged-report.json`, sau đó `scripts/rebuild_dataset_v2.py --publish --compare-report artifacts/staged-report.json`. Script so sánh các bảng ngữ nghĩa, ID, ảnh và giá trị đã chọn trước khi publish; metadata thời điểm build không tham gia phép so sánh. Báo cáo so sánh với bản trước dùng snapshot `artifacts/enrichment-20260918/`.

Hoàn tác: dừng API, sao chép `catalog_v2.sqlite` và hai thư mục `dataset/`, `catalog/` từ một snapshot trong `artifacts/dataset-backups/` về đúng vị trí tương ứng, rồi khởi động lại API. Endpoint tải file từ chối phục vụ lúc publish hoặc khi phiên bản export khác catalog đang nạp.

Các file đọc và bàn giao ở `data/reports/v2/dataset/`:

| File | Nội dung |
|---|---|
| `merged_dataset.xlsx` | POI, nguồn từng trường, ảnh, trường thiếu và hàng cần kiểm tra |
| `pois.csv` | POI hợp nhất, bí danh, ảnh, trạng thái khám phá/lịch trình |
| `field_provenance.csv` | Giá trị được chọn, nguồn, phương pháp và lý do |
| `images.csv` | Tất cả ứng viên ảnh cùng kết quả kiểm tra |
| `ratings.csv`, `opening_hours.csv` | Quan sát rating và giờ cấu trúc |
| `summary.json`, `audit.json` | Độ phủ và kiểm tra cấu trúc |

Workbook xuất là dẫn xuất nội bộ để kiểm tra. Giữ phân loại `restricted_internal` của quan sát Google và attribution của từng nguồn.

## API và bản đồ

- `GET /api/v2/pois`: giữ mặc định tập đủ điều kiện phục vụ lịch trình; có `offset`, `limit`.
- `GET /api/v2/pois?view=explore`: tìm kiếm toàn quốc theo tên, mô tả và bí danh, có hoặc không dấu.
- `GET /api/v2/pois/{poi_id}?view=explore`: chi tiết POI, ảnh, nguồn và điều kiện lập lịch trình.
- `GET /api/v2/map-pois?bbox=west,south,east,north`: GeoJSON nhẹ cho vùng nhìn, độc lập phân trang danh sách.
- `POST /api/v2/itineraries`: chỉ phục vụ Hà Nội/Đà Nẵng; dữ liệu ước lượng vẫn tạo kết quả `provisional`.

Nền online dùng tile OpenStreetMap do FOSSGIS phục vụ tại `tile.openstreetmap.de`. Trong kiểm tra trực quan, CARTO Voyager trả PNG có watermark `API KEY REQUIRED`, nên đã thay nhà cung cấp để giữ phương án không cần API key. Không tải hàng loạt tile; trình duyệt chỉ tải vùng đang xem.

Khi mất mạng, giao diện có lớp địa giới toàn quốc và nền OSM local chi tiết cho hai địa phương trọng tâm. Nền local chi tiết vẫn kiểm tra snapshot PBF với catalog/OSRM. Nền online hoạt động độc lập với phiên bản dữ liệu định tuyến.

```powershell
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
.venv\Scripts\python.exe scripts\smoke_explore_v2.py
.venv\Scripts\python.exe scripts\smoke_web.py
```

Smoke khám phá kiểm tra cả online và mobile offline; smoke lịch trình dùng OSRM thật và chặn mạng ngoài để kiểm tra dự phòng local. Ảnh chụp nằm trong `artifacts/enrichment-web/`; chúng là bằng chứng giao diện, không chứng minh độ chính xác ngoài thực địa.
