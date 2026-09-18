# Kết quả kiểm tra và đánh giá Where2Go DSS v2

**Ngày kiểm tra:** 18/09/2026

**Dataset:** `v2-91f833f05c8c7ef8`

**Phạm vi ưu tiên:** Hà Nội và Đà Nẵng mới, gồm Quảng Nam cũ

**Kết luận:** Hệ thống chạy được với catalog đa nguồn, routing thật và web/API chung lõi. Dataset đủ cho demo/nghiên cứu tình huống có cảnh báo; chưa đủ bằng chứng để gọi là lịch trình đã xác minh ngoài thực địa.

## 1. Kết quả kỹ thuật

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Catalog v2 và export local | PASS | 15.713 POI; SQLite và 6 bảng CSV |
| Audit cấu trúc | PASS | 0 hard error; SQLite integrity/foreign key/export khớp |
| Test tự động | PASS | 65 test; 1 deprecation warning từ Starlette TestClient |
| Dependency | PASS | `pip check`: không có dependency hỏng |
| JavaScript | PASS | `node --check web/app.js` |
| Web dùng POI serviceable | PASS kiểm thử | API mặc định ẩn hàng quality gate không đạt |
| OSRM cùng snapshot | PASS | Container `where2go-osrm` và route probe dùng đúng SHA256 PBF |
| Evaluator trên dataset mới | PASS kỹ thuật | 16 kịch bản x 4 phương pháp = 64/64 lịch `provisional` |
| Smoke desktop/mobile trên code mới | PASS | 5 điểm, sửa duration, lọc/chủ đề, basemap local khi chặn mạng ngoài, mobile; 0 page error |
| Kiểm duyệt người | NOT RUN | 0 record `confirmed` bởi người |
| Owner grading/nhãn độc lập | NOT RUN | Workbook chưa có điểm chấm hoàn chỉnh |

## 2. Chất lượng dataset

Audit hiện có 1.536 POI serviceable toàn catalog và 4.853 cảnh báo làm giàu:

| Cảnh báo | Số lượng |
|---|---:|
| Tên điểm tham quan trùng trong cùng địa phương | 3 |
| POI serviceable chưa biết giờ | 335 |
| Thiếu cặp rating/review hợp lệ | 1.439 |
| Duration chưa được người kiểm duyệt xác minh | 1.536 |
| Access chưa được người kiểm duyệt xác minh | 1.536 |
| Mục tiêu priority chưa đạt | 4 |

Quality gate đã được siết: POI ăn uống không còn đủ điều kiện chỉ nhờ một mô tả dài; phải có bằng chứng mạnh hơn như giờ cấu trúc, rating hợp lệ hoặc website. Thay đổi này loại 23 hàng yếu khỏi tập phục vụ so với bản audit trước.

### Hai địa phương ưu tiên

| Chỉ số | Hà Nội | Đà Nẵng |
|---|---:|---:|
| POI usable | 4.474 | 2.682 |
| POI serviceable | 784 | 499 |
| Điểm tham quan serviceable | 113 | 69 |
| Ăn/nghỉ serviceable | 671 | 430 |
| Có cặp rating/review hợp lệ | 67 | 29 |
| Có giờ cấu trúc | 611 | 414 |
| Duration đã xác minh | 0 | 0 |
| Access đã xác minh | 0 | 0 |

Tập ưu tiên 70 POI mỗi thành phố đủ 50 tham quan + 20 ăn/nghỉ, nhưng giờ chỉ đạt 65,71% ở Hà Nội và 62,86% ở Đà Nẵng; mục tiêu là 80%. Duration xác minh vẫn 0%, nên các lịch có duration/access ước lượng phải là `provisional`.

Ba cảnh báo trùng tên điểm tham quan gồm hai đối tượng “Chùa Linh Ứng” ở Đà Nẵng và các cụm ở Huế/An Giang. Đà Nẵng cần kiểm duyệt xem đây là hai chùa riêng hay bản ghi trùng; không tự gộp chỉ dựa trên tên.

## 3. Đánh giá thuật toán

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

## 4. Web và cleanup

- Web không tự mở panel POI đầu tiên; có nút đóng và giới hạn 250 POI hiển thị.
- Timeline mở được chi tiết POI qua API riêng dù POI không còn trong danh sách đang lọc.
- Đổi thành phố xóa required POI, duration override và panel cũ.
- Leaflet JS/CSS/icon và basemap OSM cho Hà Nội/Đà Nẵng đều được lưu local; web không còn gọi tile CDN.
- Basemap được sinh từ cùng PBF với catalog/OSRM và chỉ được API phục vụ khi checksum khớp. Hà Nội có 139.007 đối tượng nguồn, Đà Nẵng có 60.130; mỗi nơi được gộp thành 13 lớp Canvas để tránh tạo hàng chục nghìn Leaflet layer.
- Smoke chặn toàn bộ request ngoài origin local; nền, tuyến OSRM, marker và timeline vẫn render trên desktop/mobile, kiểm tra pixel Canvas PASS và không có page error.
- Các notebook, tài liệu v1, scraper legacy, workbook đánh giá mô phỏng và JSON frontend cũ đã bị xóa.
- Nguồn/snapshot cần rebuild v2, catalog, curation, workbook kiểm duyệt và dữ liệu Google có provenance được giữ lại.

## 5. Việc ưu tiên tiếp theo

1. Xác minh người thật cho ít nhất 40/50 điểm tham quan mỗi thành phố: danh tính, giờ, duration và access.
2. Bổ sung giờ cho ít nhất 10 POI priority Hà Nội và 12 POI priority Đà Nẵng để tiến tới 80%.
3. Xử lý cảnh báo “Chùa Linh Ứng” và các quan hệ khu-cha/con trước khi demo chuyên đề.
4. Khi đổi snapshot OSM hoặc địa giới, rebuild basemap local và xác nhận `/api/health` báo `basemap: ready` trước khi demo.
5. Hoàn thành 12 phiếu holdout trước khi so sánh phương pháp; AP/NDCG chỉ dùng khi pool có nhãn độc lập đầy đủ.

Nguồn số liệu: `data/reports/v2/dataset/summary.json`, `audit.json`, `source_manifest.json` và `manual_validation.json`.
