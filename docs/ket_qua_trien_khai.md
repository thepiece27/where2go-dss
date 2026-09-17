# Kết quả triển khai và kiểm tra Where2Go DSS

Ngày kiểm tra: **17/09/2026**. Đây là báo cáo cho phiên bản lịch trình mới; không dùng kết quả mô phỏng của notebook cũ để khẳng định chất lượng hiện tại.

## 1. Kết quả chính

Đã có pipeline chạy thật từ snapshot OSM tới catalog, API, web và evaluator. OSRM tự chạy trong Docker trên máy này đã dựng mạng đường Việt Nam và trả tuyến thật. Bốn kịch bản ở Hà Nội, trung tâm Đà Nẵng và Hội An tạo được lịch trình 5 điểm, có giờ đến/rời và quay về. Mọi demo hiện mang trạng thái **provisional**, vì còn điểm chưa rõ giờ mở cửa.

Phần phần mềm đã có bằng chứng kiểm thử; **chưa thể gọi toàn bộ chất lượng dữ liệu, độ phù hợp du lịch và đánh giá người dùng là hoàn tất**. Biên bản nguồn có hỗ trợ công cụ không tương đương khảo sát thực địa hoặc đánh giá độc lập. Những giới hạn này được giữ rõ trong dữ liệu và giao diện.

## 2. Phiên bản và dữ liệu

| Hạng mục | Kết quả kiểm chứng |
|---|---|
| Dataset | `osm-4f7244d59895-7ea9ed33-390f398e-e118cf0e` |
| OSM | `vietnam-260915.osm.pbf`, timestamp nguồn `2026-09-15T20:20:37Z` |
| SHA256 PBF | `4f7244d59895803a521b8f6ef0b86629bf4470565ad329ed5d3336676db047e7` |
| Routing | OSRM 5.27.1, profile car, MLD, routing version `1e1d2ec5e5a86240` |
| Môi trường | Windows, Python 3.13.15, Docker Desktop/WSL2; Docker daemon 29.7.2 |
| Catalog | 10.202 POI OSM có tên và loại phù hợp; không phải 10.202 điểm đã xác minh |
| Nguồn legacy | Kiểm kê đủ 8.201 dòng, giữ nguyên workbook, không nhập mặc định vào catalog công bố |

Chi tiết nguồn, checksum địa giới, registry và pipeline nằm trong [manifest](../data/reports/manifest.json). Catalog SQLite lớn được tái tạo tại máy; CSV và các báo cáo được lưu trong repo.

| Độ phủ | Hà Nội | Đà Nẵng mới |
|---|---:|---:|
| Tổng bản ghi | 1.331 | 389 |
| Đủ điều kiện dữ liệu cơ bản (`usable`) | 1.317 | 328 |
| Cần kiểm duyệt | 1 | 4 |
| Loại khỏi gợi ý, vẫn giữ audit | 13 | 57 |
| Phân tích được lịch tuần, tính trên toàn bộ bản ghi | 36 | 24 |
| Có biên bản đối soát nguồn | 27 | 31 |
| Có tuyến đi/về từ điểm kiểm tra và snap ≤300 m | 1.313 / 1.317 | 302 / 328 |
| Có cả biên bản nguồn và kiểm tra đường đạt | 27 | 31 |

Kiểm tra đường dùng một xuất phát cố định mỗi thành phố; không chứng minh mọi xuất phát đều đi được, mọi cổng đều mở, hay xe được phép tiếp cận đúng cửa. Các request vẫn được kiểm tra lại theo tọa độ thực tế.

58 biên bản đã ghi nguồn OSM, danh tính/loại hình theo nguồn, bằng chứng tọa độ và địa giới, trạng thái giờ. Một số giờ được bổ sung từ nguồn địa điểm/cổng du lịch; chưa xác minh độc lập mọi giờ/lối vào trong mẫu. Số 25 POI mỗi thành phố đạt ở mức **đối soát nguồn có hỗ trợ công cụ + routing tự động**, không đạt nghĩa “25 POI đã khảo sát ngoài thực địa”. Danh sách chi tiết: [reviewed_sample.json](../data/reports/reviewed_sample.json).

Kiểm kê legacy xác nhận cụm **202 điểm tại 10.8658688, 106.692608**; tổng các cụm đáng ngờ trên 5 bản ghi là 214 điểm. Ngoài ra có 2.901 URL chỉ chứa tọa độ viewport theo quy tắc audit, 2.938 tên kết quả là `Results`, 4.159 dòng thiếu loại. Các nhóm này có thể giao nhau, không cộng thành số dòng lỗi riêng biệt. Chưa khôi phục tọa độ từ backup vì chưa có bằng chứng đủ để ghi đè.

SHA256 workbook sau xử lý vẫn là `9ac0a4e69d99d3da7d1ffb45cf3100d0385539c3c6317e3faa6124ecf2940744`.

## 3. Lịch trình và baseline

Ngày cố định 20/09/2026, 08:00–18:00, bán kính 30 km, trọng số mặc định bằng nhau. Bảng dưới lấy đúng kết quả phương pháp fuzzy trong [evaluation.json](../data/reports/evaluation.json); tuyến và thời gian chi tiết từng điểm có trong file.

| Kịch bản | POI có đường trong pool | Điểm dừng | Giờ về | Tổng lái xe | Trạng thái |
|---|---:|---:|---|---:|---|
| Hoàn Kiếm | 40 | 5 | 11:49 | 3,9 phút | provisional |
| Tây Hồ | 40 | 5 | 13:10 | 9,3 phút | provisional |
| Trung tâm Đà Nẵng | 40 | 5 | 12:38 | 7,7 phút | provisional |
| Hội An, Quảng Nam cũ | 40 | 5 | 14:31 | 3,6 phút | provisional |

Thời gian lái xe ngắn do thuật toán chọn các điểm rất gần nhau. Điều này **không chứng minh đây là hành trình du lịch tốt**: nhiều điểm là công trình nhỏ, chưa cộng tìm chỗ đỗ/đi bộ và chưa phạt việc chọn nhiều điểm cùng loại. Không kéo dài lịch tới 18:00 khi không cần; 18:00 là hạn chót quay về.

Bốn phương pháp nearby, weighted sum đều, crisp AHP + TOPSIS, fuzzy AHP + TOPSIS đều tạo được 5 điểm trên cả bốn kịch bản: **16/16 lượt qua kiểm tra ràng buộc mô hình**. Evaluator xác nhận cùng pool giữa các phương pháp. Chưa có nhãn người dùng nên AP/NDCG/Recall là null; không báo độ chính xác, không tuyên bố phương pháp nào tốt hơn.

Với gamma chung và fuzzification đối xứng hiện hành, trọng số fuzzy sau chuẩn hóa bằng trọng số crisp geometric mean. Đây là tính chất toán học đã được test, không phải bằng chứng lợi ích của fuzzy. [Tài liệu công thức](fuzzy_ahp.md) có phép giải thích vì sao hệ số mờ triệt tiêu.

## 4. Bằng chứng kiểm thử

Quy ước: `PASS` là đã chạy và qua; `FAIL` là đã chạy nhưng chưa đạt; `NOT RUN` là chưa thực hiện. Một kiểm thử qua không bảo đảm mọi dữ liệu ngoài fixture đều đúng.

| Kiểm tra | Trạng thái | Bằng chứng/phạm vi |
|---|---|---|
| Regression Python | PASS | 23 ca pytest; cả môi trường hiện có và môi trường mới cài từ lock |
| Dependency môi trường mới | PASS | `pip check`: không có yêu cầu dependency hỏng |
| Compile Python | PASS | `compileall` cho lõi, scripts, tests |
| Import PBF thật không dùng cache cũ | PASS | 10.202 POI; tiến trình kết thúc bình thường |
| Rebuild cùng nguồn | PASS | Giữ version, ID registry và checksum CSV |
| Notebook hiện hành | PASS | Chạy ba code cell; gọi planner thật, không pipeline thay thế |
| OSRM extract/partition/customize/routed | PASS | Graph quốc gia, image pin, manifest cùng PBF, route thật |
| Routing audit hai thành phố | PASS | Toàn bộ 1.645 usable được kiểm tra; lưu cả lý do không đạt |
| Bốn kịch bản × bốn phương pháp | PASS | 16 kết quả provisional, 5 điểm/kết quả, có đường về |
| Web đầu cuối | PASS | Save ban đầu/sau lọc, timeline, đổi loại hình, chống URL ảnh chèn HTML; không có page error |
| Nền bản đồ | PASS ở lần chạy cuối | 25 tile tải thành công; trước đó có lỗi DNS, đã có thông báo mất nền bản đồ |
| Ngừng/khởi động lại OSRM thật | PASS | Health và itinerary báo unavailable khi dừng; trở lại hoạt động sau start; không dùng cache để che mất kết nối |
| Xác minh cổng/giờ ngoài thực địa | NOT RUN | Không gán nhãn kiểm tra tự động thành xác minh thực địa |
| Nhãn liên quan/người dùng độc lập | NOT RUN | Chỉ case study, chưa có kết luận vượt baseline |
| Đo tải đồng thời/triển khai Linux máy khác | NOT RUN | Chưa phải nghiệm thu hệ thống production |

Artifact cục bộ: `artifacts/web-smoke.json`, `artifacts/web-itinerary.png`, `artifacts/live-outage.json`, `artifacts/notebook-output.txt`. Những file này không tự commit; có thể tạo lại bằng hướng dẫn. Một cảnh báo deprecation từ Starlette/AnyIO trong TestClient còn xuất hiện; không làm fail test và chưa có lỗi tương ứng khi chạy API.

## 5. Đối chiếu lỗi trong review ban đầu

| Mã | Đã xử lý trong phiên bản mới | Phần còn thiếu |
|---|---|---|
| R01 | Query tình huống viết trước, không sinh từ đáp án | Chưa có nhãn người dùng độc lập |
| R02 | Evaluator dùng `plan_itinerary`/`rank_pois` như API | Chưa có kết luận chất lượng định lượng |
| R03 | AP dùng tổng relevant; IDCG dùng toàn tập nhãn; fixture phản ví dụ qua | Cần bộ nhãn thật |
| R04 | Bỏ viewport; audit cụm 202; không ghép legacy tọa độ nghi sai; giữ provenance | Chưa đo precision ghép thực thể thủ công, chưa khôi phục tọa độ legacy |
| R05 | ID OSM + registry; web/notebook/export chung catalog; test import lại | Khi nguồn thay đổi thực thể phải kiểm duyệt alias |
| R06 | Chung ba tên tiêu chí cho AHP/TOPSIS/API | Không tái sử dụng ma trận năm tiêu chí cũ |
| R07 | Kiểm tra reciprocal, hữu hạn, CR; request sai trả 422 | Không tự gán trọng số thay khi người dùng nhập sai |
| R08 | Fuzzification reciprocal đối xứng; test hoán vị | Gamma chung không tạo trọng số khác crisp |
| R09 | Hard filter, shortlist nội dung/vị trí, OSRM trước xếp hạng | Chưa đo candidate recall độc lập; khớp token còn yếu |
| R10 | Bộ lọc danh sách và lịch dùng cùng request | Chưa có kiểm thử toàn bộ thiết bị/trình duyệt |
| R11 | Save đúng POI đang hiển thị bằng canonical ID | Lưu localStorage, chưa có tài khoản đồng bộ |
| R12 | DOM setters, kiểm tra protocol/host ảnh | Chưa xây kho ảnh có giấy phép đầy đủ |
| R13 | Taxonomy OSM, trạng thái thiếu và queue bổ sung | Coverage giờ rất thấp; cần kiểm tra correctness thủ công |
| R14 | Bỏ hành vi mô phỏng khỏi sản phẩm, helper split trước cutoff có fixture | Chưa có dữ liệu tương tác thật để đánh giá thời gian |
| R15 | Tách Google khỏi API mặc định, OSM attribution/manifest, nguồn giờ theo trường | Workbook Google lịch sử vẫn ở repo; không mặc nhiên phân phối lại dữ liệu cũ |
| R16 | Shortlist 40, cache routing có version, danh sách web giới hạn 1.000 | Chưa benchmark tải; API chưa có phân trang đầy đủ |
| R17 | Điểm được mô tả tương đối, không xác suất | Độ tin cậy vẫn là quy tắc thiết kế chưa hiệu chuẩn |
| R18 | Dependency khóa, test, manifest, import lại và môi trường mới đã thử | Chưa thiết lập CI/checkout trên máy thứ hai |

## 6. Những lỗi kỹ thuật phát hiện khi triển khai

- OSRM có thể trả distance âm rất nhỏ ở cặp điểm snap gần trùng: vô hiệu đúng cạnh có hướng, không bịa số 0 hay loại cả ma trận.
- Planner điều chỉnh thời gian theo Route từng làm thay đổi dữ liệu trong cache Table: đã trả deep copy để baseline sau không bị ảnh hưởng baseline trước.
- Health đọc cache có thể che OSRM đã dừng: health và route kiểm chứng cuối gọi trực tiếp dịch vụ.
- Đọc header PBF từng gây treo lúc thoát trên Windows: đọc header không nạp entity và giới hạn pool, đã kiểm tra import thật lẫn rebuild kết thúc.
- Cache importer cũ chưa gắn mã parser: cache mới có fingerprint importer/parser/config để tránh dùng dữ liệu dẫn xuất lỗi thời.
- Console Windows từng lỗi mã hóa khi in tiếng Việt: script báo cáo cấu hình stdout UTF-8.
- SQLite cần đóng kết nối thực trước thay file trên Windows: dùng `closing`, commit và thay file tạm.
- ID sau deduplicate có thể đổi khi thêm nguồn: giữ registry canonical đã cấp; liên kết mơ hồ đưa vào review.
- Parser giờ nhận sai cú pháp ngày như `Mo--Fr`: từ chối thành unknown; không diễn giải tùy tiện.
- Catalog tọa độ NaN/ngoài miền và OSRM trả JSON không phải object: lọc/báo lỗi rõ, không để làm sập request.

## 7. Việc cần làm tiếp để nâng chất lượng báo cáo/sản phẩm

1. **Giờ và lối vào:** xử lý [enrichment_queue.csv](../data/reports/enrichment_queue.csv), bắt đầu mẫu 58 điểm rồi mở rộng cụm; xác nhận chính thức giờ ngày lễ, điểm đỗ/cổng. Tách kiểm tra nguồn và kiểm tra thực địa.
2. **POI có giá trị tham quan:** kiểm duyệt công trình phụ và điểm trùng chức năng, bổ sung mô tả thật; đo precision ghép. Số lượng OSM lớn không đồng nghĩa bộ điểm du lịch tốt.
3. **Nhãn độc lập:** có người chấm mức phù hợp trên toàn pool và phản hồi lịch trình; đóng băng query trước khi thấy kết quả, không dùng nhãn để chỉnh test.
4. **Thời gian thực tế:** thêm thời gian đệm đỗ xe/đi bộ bằng nguồn hoặc tham số công khai; kiểm thử lại trước khi đổi ý nghĩa ready. Không gọi kết quả hiện tại là tối ưu toàn cục.
5. **Mô hình tốt hơn sau khi có nhãn:** đánh giá khớp cụm từ/ngữ nghĩa, độ đa dạng loại hình, chất lượng điểm đến; cân nhắc bất định riêng từng phán đoán nếu muốn fuzzy tạo khác biệt có cơ sở.

Phiên bản hiện tại đủ làm demo kỹ thuật có giải thích, bằng chứng và giới hạn; mức hoàn thiện dữ liệu thực địa và bằng chứng hiệu quả với người dùng vẫn cần công việc độc lập tiếp theo.
