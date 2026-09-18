# Kết quả hợp nhất dữ liệu và bản đồ Where2Go DSS

Ngày kiểm tra: **18/09/2026**. Đã publish local và giữ bản hoàn tác. Dataset đã kiểm tra: **`v2-ae66988a1053d0de`**, schema **2.1**.

**Cập nhật luồng người dùng cùng ngày:** giao diện hiện dùng API lịch nhiều phương án, cho chọn thủ công POI thiếu rating/giờ khi danh tính/vị trí đủ tin cậy. Các số “đủ điều kiện metadata/lịch trình” trong báo cáo dữ liệu này vẫn là tiêu chuẩn planner cũ, không phải giới hạn tập người dùng được chủ động chọn. Xem [báo cáo lựa chọn lịch trình và 107 kiểm thử](trai_nghiem_lua_chon_lich_trinh.md).

Web đọc `data/catalog_v2.sqlite`. Cả ba workbook Google/HOTOSM là đầu vào thực sự, nhưng trước đây chỉ liên kết tới 139 POI và không có ảnh được chọn. Đợt này phục hồi dữ liệu trên toàn quốc, thu thập bổ sung có mục tiêu cho Hà Nội/Đà Nẵng và tách khám phá khỏi điều kiện lập lịch trình. Chưa cần crawl lại toàn bộ.

## 1. Trước và sau

| Chỉ số | Trước | Sau |
|---|---:|---:|
| POI trong catalog | 15.713 | 16.018 |
| POI liên kết từ ba Excel | 139 | 1.569 |
| Dòng Excel được liên kết | 303 | 4.853 |
| POI có ảnh được chọn | 0 | 1.048 |
| Địa điểm khám phá qua API mới | Chưa tách riêng | 15.245 |
| POI đạt điều kiện metadata cho lịch trình | 1.522 theo API | 1.475 |
| POI phục vụ có cặp rating/review được chấp nhận | 96 | 86 |

Phục hồi **8.153 giá trị trường** từ Excel; tạo **304 POI từ Excel** đủ bằng chứng và **1 POI từ đợt thu thập mới**. Toàn bộ ID của 15.713 POI trước được giữ. Không gộp Mỹ Khê Đà Nẵng với Mỹ Khê Quảng Ngãi. Ba checksum workbook gốc không đổi.

Số POI được dùng lập lịch giảm vì 175 quan sát rating cũ dùng phương pháp `same_source_row` không đủ chứng minh rating và review được lấy cùng lần. Các giá trị này vẫn được lưu để truy nguyên với `same_observation=0`; không dùng chúng để tăng điểm. Audit cũ ghi 1.536 nhưng API thực tế chỉ trả 1.522; báo cáo mới dùng chung điều kiện API, planner và export. Phạm vi lập lịch vẫn chỉ Hà Nội/Đà Nẵng; 1.475 là số đạt điều kiện metadata trên toàn catalog.

| Nguồn | Dòng đọc | Dòng liên kết | Giá trị trường bổ sung |
|---|---:|---:|---:|
| Workbook chính | 8.201 | 1.608 | 8.149 |
| Backup 15/09 | 8.710 | 1.623 | 4 |
| Backup 16/09 | 8.710 | 1.622 | 0 |

Ba file có 8.710 STT khác nhau, không phải 25.621 địa điểm riêng. Cột giá trị bổ sung phản ánh thứ tự chọn trường; backup vẫn đóng góp quan sát, liên kết và đối chiếu phiên bản. Thời điểm thu thập chưa biết giữ `null`; không suy từ tên backup hay mtime.

## 2. Thu thập và ảnh thực tế

- Đã chạy **149 mục tiêu duy nhất**, **179 lượt thử** có checkpoint. Pilot: **19/20** được đối chiếu, đạt cổng mở rộng. Đợt tiếp: **70/129** được chấp nhận.
- Tổng **89 kết quả được nhập**, **60 mục tiêu giữ để kiểm tra**. Tỷ lệ được chấp nhận sau đối chiếu là 89/149 (59,73%); đây không phải độ chính xác có nhãn độc lập của toàn bộ scraper. Không phát hiện liên kết sai trong nhóm chấp nhận qua các đối chiếu đã ghi; vẫn chưa có kiểm duyệt người.
- Quan sát mới có **84 cặp rating/review cùng panel**, **58 bộ giờ tuần**, **85 địa chỉ**, **36 website**, **40 số điện thoại** và **89 tọa độ thực thể**. Những số này là trường thu được, có thể cập nhật POI đã có; không được cộng như số địa điểm mới.
- **1.048 ảnh được chọn**: **960** từ liên kết Google trong Excel và **88** từ panel mới. Có kiểm tra chuyển hướng, MIME, nội dung ảnh, kích thước và tải thực tế. Nhóm ảnh website/Bing/link rút gọn chưa xác định liên hệ được giữ để đối chiếu.
- Ảnh hồ sơ, logo, ảnh quá nhỏ hoặc URL dùng chung cho nhiều thực thể không được tự chọn. Google giữ phân loại `restricted_internal`. Chưa có kiểm duyệt nội dung từng ảnh bởi người.

Collector dùng adapter trong repository, không sửa thư viện trong `.venv`. `@lat,lng` chỉ là tâm khung nhìn; tọa độ địa điểm lấy từ URL thực thể hoặc marker duy nhất đang được chọn. Kết quả mới giữ `tool_confirmed`, không chuyển thành xác minh thủ công. Tên gần giống cần quyết định đối chiếu riêng; khu lớn dùng hình học hoặc bằng chứng website thay vì nới bán kính chung.

## 3. Các thiếu sót trọng điểm

**Mỹ Khê:** sửa nguyên nhân `needs_review` do gán địa phương, giữ ID `osm:relation:19000664`. Tìm được bằng “my khe”, mở chi tiết, có ảnh và đủ điều kiện metadata cho lịch trình.

**Bãi tắm Phạm Văn Đồng:** có POI riêng `poi-google:9f6b613e52c6d0f34461666b`, Google ID `0x3142178599738b33:0xf208a358691762b3`, tọa độ 16.0732782, 108.2468342. Tìm được và hiển thị ảnh; còn thiếu giờ/rating nên chỉ khám phá. Không tự gán quan hệ cha/con với Mỹ Khê hoặc Công viên Biển Đông.

**Thanh Hà:** ưu tiên quan sát đã đối chiếu trước Excel để tránh Google ID Làng gốm Thanh Hà bị gán sang “Làng mộc Thanh Hà”. Giữ riêng làng gốm, công viên đất nung và bản ghi làng mộc; xung đột cũ nằm trong hàng kiểm tra.

**Bà Nà:** website chính thức nhúng cùng Google ID, cho phép đối chiếu khu vực lớn. Điểm Google chỉ là tọa độ tiếp cận dự phòng chưa xác minh, không thay điểm đại diện OSM hay tự được coi là cổng đã xác minh.

## 4. Độ đầy đủ và giới hạn

| Tập ưu tiên 70 POI | Hà Nội | Đà Nẵng |
|---|---:|---:|
| Tham quan + ăn/nghỉ | 50 + 20 | 50 + 20 |
| Có giờ cấu trúc | 58/70 (82,86%) | 59/70 (84,29%) |
| Đủ cả tuần | 54/70 | 57/70 |
| Có cặp rating/review | 39/70 | 47/70 |
| Thời lượng đã xác minh | 0 | 0 |
| Điểm tiếp cận đã xác minh | 0 | 0 |

Toàn tập 1.475 POI đạt điều kiện phục vụ vẫn có **257 chưa biết giờ**, **1.389 thiếu cặp rating/review**, **1.475 chưa xác minh duration/access**. Audit có 0 lỗi cấu trúc và 4.599 lượt cảnh báo; cảnh báo có thể lặp trên cùng POI. Hàng kiểm tra hợp nhất gồm 20.840 quan sát nguồn, không phải 20.840 POI riêng.

Các nguồn chưa đủ bằng chứng không được ép ghép. Ảnh URL ngoài có thể hết hạn; giao diện có thay thế khi tải lỗi. OSRM không có giao thông trực tiếp. Dữ liệu đã được cải thiện và truy nguyên được, nhưng chưa thể coi là đầy đủ hoặc tối ưu hoàn toàn; phần cần bổ sung tiếp theo nằm trong workbook và quality queue.

## 5. Bản đồ và kiểm thử

Bản đồ mở toàn Việt Nam, có nút về toàn quốc/chuyển nhanh Hà Nội/Đà Nẵng, marker theo loại và cụm khi thu nhỏ. Nền online dùng FOSSGIS/OSM vì CARTO Voyager trả ảnh có watermark `API KEY REQUIRED` trong kiểm tra thực tế. Attribution được giữ. Mất mạng dùng địa giới toàn quốc và nền local chi tiết hai địa phương.

API thêm `view=explore`, offset, tìm bí danh không dấu và endpoint marker theo bbox. Danh sách 250 hàng/trang không giới hạn marker; trên vùng toàn quốc kiểm tra được 15.245 marker. Chi tiết trả nguồn ảnh, bí danh, provenance và điều kiện lập lịch.

| Kiểm tra | Trạng thái | Bằng chứng |
|---|---|---|
| Test tự động | PASS | 74 test; 1 deprecation warning Starlette |
| JavaScript/dependency | PASS | `node --check` hai JS, `pip check` |
| Whitespace code/tài liệu | PASS | `git diff --check` ngoài báo cáo dữ liệu |
| Whitespace toàn bộ diff | FAIL | Một khoảng trắng cuối dòng trong mô tả CSV nhiều dòng được giữ theo nguồn |
| SQLite, CSV, API, checksum nguồn, ID | PASS | `merge_report.json`, audit 0 hard error |
| Desktop online | PASS | Toàn quốc, phân trang, ảnh hai bãi biển, 0 page error |
| Mobile chặn mạng ngoài | PASS | Nền dự phòng, không tràn ngang, 0 page error |
| OSRM thật + smoke lịch trình | PASS | 5 điểm, đổi duration, lọc/chủ đề, desktop/mobile |
| Evaluator | PASS kỹ thuật | 16 kịch bản × 4 phương pháp, 64/64 `provisional` trên phiên bản mới |
| Tái lập hai build và publish | PASS | ID và 9 bảng ngữ nghĩa giống nhau; bản publish có cùng checksum staging |
| Xác minh người/khảo sát thực địa | NOT RUN | Không có bản ghi mới được gán human verified |
| Owner grading/nhãn độc lập | NOT RUN | Không suy chất lượng trải nghiệm từ trạng thái scraper |

Ảnh kiểm tra: `artifacts/enrichment-web/national-online.png`, `danang-beach-online.png`, `mobile-offline.png`. Smoke máy: `artifacts/enrichment-web/smoke.json` và `artifacts/web-smoke.json`.

## 6. Đánh giá thuật toán

Điểm mạnh:

- Bốn tiêu chí thống nhất giữa model, API, web và evaluator.
- Rating được co theo số review; thiếu rating giữ trung tính và không hiển thị số giả.
- TOPSIS xử lý cột hằng/toàn 0, cost direction và tie-break ổn định.
- Planner kiểm tra giờ, nghỉ trưa, duration, access, ăn/nghỉ, đường về và reserve.
- POI cha/con bị chặn; category ưu tiên được tách khỏi chế độ chuyên đề.

Giới hạn:

- Confidence hiện thấp chủ yếu vì chưa có access/duration/activity verification; nó phản ánh bằng chứng chứ không phản ánh trải nghiệm.
- TF-IDF và tag matching còn đơn giản; chưa có embedding tiếng Việt hoặc nhãn sở thích độc lập.
- Với cùng hệ số bất định 1,2 cho mọi cặp, trọng số Fuzzy AHP bằng crisp geometric-mean AHP. Không được tuyên bố fuzzy tốt hơn vì tên phương pháp.
- Multi-start hiện thử ba seed và ba vòng thay điểm, thấp hơn mục tiêu kế hoạch ban đầu; phù hợp demo nhưng chưa phải tìm kiếm mạnh.
- Không có giao thông trực tiếp, parking/walking graph hay lịch ngày lễ đầy đủ.

Evaluator xác nhận bốn phương pháp chạy trên cùng 16 kịch bản và đều tạo được đầu ra. Kết quả này chỉ chứng minh pipeline hoạt động; chưa có phiếu chấm nên không có cơ sở xếp phương pháp nào tốt hơn. Objective đã được tính lại sau khi OSRM Route thay các leg ước lượng của Table, tránh báo điểm mục tiêu cũ khi timeline cuối thay đổi.

## 7. Bàn giao và chạy lại

- Catalog: `data/catalog_v2.sqlite`. API đang chạy local tại `http://127.0.0.1:8000`; health báo catalog/routing/basemap `ready`.
- Hàng thu thập tiếp: `data/reports/v2/next_collection_queue.json`, 110 mục tiêu có trường thiếu, **chưa chạy**; không crawl lại các kết quả tốt chỉ để tăng số lượng.
- Workbook chấm evaluator mới: `artifacts/enrichment-20260918/owner_grading.xlsx`; workbook chấm cũ được giữ nguyên.
- [Workbook tổng hợp](../data/reports/v2/dataset/merged_dataset.xlsx): POI, nguồn từng trường, ảnh, nguồn dữ liệu, trường thiếu và hàng kiểm tra.
- [CSV POI](../data/reports/v2/dataset/pois.csv), [provenance](../data/reports/v2/dataset/field_provenance.csv), [ảnh](../data/reports/v2/dataset/images.csv).
- [Báo cáo trước/sau máy đọc](../data/reports/v2/merge_report.json), [audit](../data/reports/v2/dataset/audit.json), [coverage](../data/reports/v2/dataset/summary.json).
- Bản trước để hoàn tác: `artifacts/dataset-backups/20260918_080614/`; snapshot khảo sát gốc: `artifacts/enrichment-20260918/`.

Lệnh build/thu thập, các nguồn cần giữ và cách hoàn tác: [Dữ liệu hợp nhất và bản đồ](du_lieu_hop_nhat_va_ban_do.md). Không chỉnh trực tiếp workbook dẫn xuất để nhập dữ liệu; nhập qua nguồn/curation rồi rebuild.
