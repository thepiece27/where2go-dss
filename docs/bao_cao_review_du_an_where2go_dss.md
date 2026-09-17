# Báo cáo review dự án Where2Go DSS

**Ngày đánh giá:** 16/09/2026.  
**Phiên bản mã nguồn:** `43c4161` — `Refactor code structure for improved readability and maintainability`.  
**Phạm vi:** tài liệu, toàn bộ mã nguồn được theo dõi trong repository, notebook, các workbook đầu vào/đầu ra và dữ liệu web hiện có. Đã chạy lại phần tính toán, đánh giá và các phép thử chẩn đoán được ghi ở cuối báo cáo. Không sửa thuật toán hoặc ghi đè dữ liệu nghiệp vụ trong đợt review này.

**Nhận định chính:** dự án có giá trị như một đồ án tích hợp dữ liệu địa điểm, hệ hỗ trợ ra quyết định đa tiêu chí và giao diện bản đồ. Tuy nhiên, hiện chưa có bằng chứng đủ tin cậy rằng hệ gợi ý hiểu sở thích người dùng hoặc Fuzzy AHP + TOPSIS tốt hơn các phương pháp đơn giản. Các điểm cần ưu tiên là tính đúng của dữ liệu, thiết kế đánh giá và sự thống nhất giữa notebook với sản phẩm web.

Ba kết quả nổi bật đã kiểm chứng:

- Đánh giá `content_cold_start` đạt `HitRate@10 = MRR@10 = NDCG@10 = 1.0`, nhưng truy vấn được tạo từ nội dung của chính POI đang được giữ lại làm đáp án. Đây là rò rỉ đáp án vào đầu vào.
- Có **202 POI dùng chung một cặp tọa độ**; **50,71%** số dòng nguồn thiếu `maps_destination_type`; **2.938** dòng có `maps_result_name = "Results"` nhưng vẫn mang trạng thái `matched`.
- Web và notebook đang dùng dữ liệu, ID và thuật toán khác nhau. Cùng `POI-00001` là **Bãi Dài Cam Ranh** trong notebook nhưng là **Tháp Bà Ponagar** trong JSON của web.

Các con số trên là kết quả kiểm tra snapshot hiện tại, không phải kết luận rằng toàn bộ dữ liệu sai hoặc dự án không có giá trị.

**Gợi ý đọc:** mục 1 và 8 trình bày bài toán và đánh giá sản phẩm; mục 3–7 phân tích bằng chứng kỹ thuật; mục 9–13 là danh sách việc cần làm và hướng mở rộng; mục 14 ghi rõ đã kiểm tra gì và chưa kiểm tra gì.

## 1. Dự án đang giải quyết vấn đề gì?

### 1.1. Bài toán có ý nghĩa thực tế

Người đi du lịch thường có nhiều địa điểm để lựa chọn, nhưng thông tin phân tán và các tiêu chí xung đột: phù hợp sở thích, gần vị trí hiện tại, có chất lượng tốt, thuộc nhóm hoạt động muốn trải nghiệm, có thông tin đủ rõ để quyết định. Chọn một địa điểm có rating cao chưa chắc giải quyết được nhu cầu này.

Dự án hướng đến hai việc:

1. **Tổ chức và khám phá dữ liệu POI tại Việt Nam:** tổng hợp địa điểm, tọa độ, tỉnh/thành, loại hình, rating, review, hình ảnh và giờ mở cửa; cung cấp tìm kiếm và bản đồ.
2. **Hỗ trợ lựa chọn POI:** kết hợp nội dung, lịch sử tương tác, khoảng cách và chất lượng để tạo danh sách ưu tiên.

Có thể phát biểu bài toán xếp hạng như sau:

\[
L_K(u,c)=\operatorname{TopK}_{i\in\mathcal{C}(u,c)} S(u,i,c),
\]

trong đó \(u\) là người dùng, \(c\) là ngữ cảnh, \(\mathcal{C}\) là tập địa điểm hợp lệ và \(S\) là điểm ưu tiên. Điểm quan trọng là **phải xác định tập hợp lệ trước khi tối ưu điểm ưu tiên**.

Ví dụ: người dùng cần đi trong bán kính 30 km và đến trước giờ đóng cửa. Địa điểm cách 400 km không nên trở thành lựa chọn hợp lệ chỉ vì có điểm nội dung cao. Hiện dự án chưa tách rõ ràng ràng buộc bắt buộc khỏi tiêu chí có thể đánh đổi.

### 1.2. Những gì dự án hiện thực sự cung cấp

| Nhu cầu | Hiện trạng | Nhận xét |
|---|---|---|
| Tra cứu địa điểm, xem bản đồ | Có web tĩnh, tìm kiếm, bộ lọc, chi tiết | Là phần sản phẩm rõ ràng nhất |
| Gợi ý theo truy vấn và vị trí | Có trong notebook | Candidate generation và ràng buộc khoảng cách còn hạn chế |
| Gợi ý dựa trên hành vi | Có mã popularity, association rules, item-CF | Dữ liệu hành vi huấn luyện/đánh giá là mô phỏng |
| Ra quyết định đa tiêu chí | Có AHP, fuzzy weights, TOPSIS | Cần thống nhất ngữ nghĩa tiêu chí và kiểm chứng lợi ích |
| Cá nhân hóa trên web | Có `user_demo` và localStorage | Chưa phải hệ người dùng thực đa thiết bị |
| Chọn điểm đến tiếp theo trong chuyến đi | Mới có xếp hạng danh sách | Chưa mô hình hóa lộ trình, trạng thái chuyến đi hay chuyển tiếp theo thời gian |
| Lập lịch trình khả thi | Chưa có | Thiếu thời lượng tham quan, thời gian di chuyển, ngân sách, giờ mở cửa có cấu trúc |

Vì vậy, tên gọi phù hợp ở thời điểm này là **nguyên mẫu hệ hỗ trợ lựa chọn địa điểm đa tiêu chí**. Cụm “next POI” nên được giải thích là danh sách gợi ý tiếp theo trên giao diện; chưa đủ cơ sở coi đây là mô hình dự đoán chuyển tiếp địa điểm hoặc lập lịch trình.

### 1.3. Điểm khác biệt nên tập trung

Giá trị có thể bảo vệ được của project không nằm ở việc có nhiều tên thuật toán. Hướng tốt hơn là trả lời một nhu cầu cụ thể: “Trong bối cảnh chuyến đi này, những địa điểm nào thực sự khả thi, vì sao được gợi ý, và người dùng có thể điều chỉnh ưu tiên thế nào?”.

Một phạm vi thử nghiệm tại một khu vực, với dữ liệu được kiểm tra và vài tình huống du lịch rõ ràng, có thể thuyết phục hơn phạm vi toàn quốc nhưng chất lượng POI không đồng đều.

## 2. Cấu trúc và luồng xử lý đã đọc

Các đường dẫn dưới đây là nguồn bằng chứng nội bộ. Số cell dùng trong báo cáo là **index bắt đầu từ 0 trong JSON notebook**, không phải execution count của Jupyter.

| Mã nguồn/tài liệu | Vai trò |
|---|---|
| [README](../README.md) | Mô tả mục tiêu, cách chạy, kiến trúc và các tuyên bố về đánh giá |
| [Notebook](../poi_recommendation_system.ipynb) | Tiền xử lý, TF-IDF, dữ liệu mô phỏng, behavioral models, Fuzzy AHP, TOPSIS, evaluation, xuất Excel |
| [Tài liệu hệ gợi ý](poi_recommendation_system.md) | Giải thích pipeline và chỉ số |
| [Tài liệu Fuzzy AHP](fuzzy_ahp.md) | Công thức, ma trận so sánh cặp, suy diễn fuzzy và TOPSIS |
| [Scraper](../scripts/scrape_google_maps_browser.py) | Tìm tên trên Google Maps, bổ sung loại và số review còn thiếu |
| [Gán tỉnh theo tọa độ](../scripts/fill_location_from_coordinates.py) | Đọc tọa độ URL, kiểm tra polygon, fallback bbox/nearest, sao lưu workbook |
| [Exporter](../scripts/export_web_data.py) | Đọc workbook riêng, làm sạch một phần, xác định tỉnh, tính quality và xuất JSON |
| [JavaScript web](../web/app.js) | Bộ lọc, bản đồ, lịch sử localStorage, mô hình gợi ý riêng trên trình duyệt |
| [HTML](../web/index.html), [CSS](../web/styles.css) | Bố cục giao diện, các điều khiển, thiết kế responsive |
| [Requirements](../requirements.txt) | Thư viện Python, hiện chưa khóa phiên bản |
| [Tài liệu nguồn OSM](osm_hotosm_enrichment.md), [Google](google_places_enrichment.md), [địa giới](location_from_coordinates.md) | Mô tả quá trình làm giàu và nguồn boundary |

Luồng notebook hiện tại:

`Excel → làm sạch → TF-IDF → tạo interaction mô phỏng → behavioral scores → candidate pool → điểm ngữ cảnh → fuzzy weights/evaluation → TOPSIS → Top-K`.

Luồng web:

`Excel → exporter riêng → JSON → token overlap + local interaction heuristics → TOPSIS với trọng số cố định → 8 gợi ý`.

Hai luồng có chung ý tưởng, nhưng **không dùng chung implementation của mô hình**. Chưa có backend phục vụ `recommend_pois()` cho giao diện. “Production API” trong README hiện là một hàm Python trong notebook, không phải một dịch vụ đã triển khai và kiểm chứng vận hành.

## 3. Review nguồn dữ liệu và chất lượng dữ liệu

### 3.1. Những gì xác nhận được về nguồn

| Thành phần | Bằng chứng hiện có | Phần chưa truy vết đầy đủ |
|---|---|---|
| `vietnam_destinations.xlsx` | 315 dòng, 7 cột; có tên, vị trí, mô tả, rating, ảnh, từ khóa | Không tìm thấy manifest xác định tác giả, phương pháp thu thập, thời điểm, URL nguồn từng dòng và quyền sử dụng từng trường |
| Workbook chính đã làm giàu | 8.201 dòng, 18 cột | Không có pipeline đầy đủ để tái tạo toàn bộ bảng từ nguồn ban đầu |
| Dữ liệu OSM/HOTOSM | 7.886 mô tả chứa chuỗi `OpenStreetMap/HOTOSM`; tài liệu xác nhận bước nhập đã thực hiện | Script nhập cũ và các trường OSM ID, source file, tags… đã bị loại khỏi workflow hiện tại |
| Trường Google Maps | Có URL, trạng thái, tên kết quả, loại, review và một số dữ liệu khác đã lưu | Scraper hiện tại chỉ bổ sung 2 trường; không tái tạo được toàn bộ lịch sử rating, ảnh, giờ mở cửa, tọa độ |
| Boundary tỉnh/thành | Có ZIP cache; bộ đọc hiện tại nhận 34 feature cấp tỉnh | URL tải trỏ đến nhánh `master`; không có commit/hash nguồn và ngày hiệu lực trong metadata nghiệp vụ |
| Hành vi người dùng | Notebook tạo bằng RNG seed 42 | Không có log người dùng thực độc lập để huấn luyện/đánh giá |

**Nhận xét:** dự án đã làm được bước tích hợp nhiều nguồn, nhưng đánh đổi quá nhiều thông tin nguồn khi dồn dữ liệu về các cột `maps_*`. Tọa độ nằm trong `maps_latitude` không tự chứng minh nó được lấy từ Google Maps. Chính tài liệu OSM ghi rằng tọa độ OSM đã được chép vào các cột này.

Repository boundary được tham chiếu là một dự án cộng đồng; tác giả công bố không trực thuộc cơ quan thống kê hoặc Chính phủ. Có thể dùng làm nguồn kỹ thuật, nhưng nên lưu phiên bản và kiểm tra phù hợp với snapshot của dự án, thay vì diễn giải cache là dữ liệu hành chính đã được xác nhận chính thức. [Nguồn boundary](https://github.com/thanglequoc/vietnamese-provinces-database).

### 3.2. Kiểm kê snapshot hiện tại

| Đối tượng | Kết quả đọc/chạy lại |
|---|---:|
| Workbook nguồn ban đầu | 315 dòng |
| Workbook chính hiện tại | 8.201 dòng |
| Mỗi workbook backup ngày 15/09 và 16/09 | 8.710 dòng, 18 cột |
| Bị notebook loại do ngoài bounding box | 9 dòng |
| Bị loại tiếp bởi khóa trùng tên + tọa độ làm tròn | 6 dòng |
| Catalog notebook sau làm sạch | 8.186 POI |
| JSON web hiện tại | 7.695 POI |
| Cleaned workbook đã lưu | 8.695 dòng |
| Interaction mô phỏng đã lưu | 1.165 event |
| Interaction mô phỏng chạy lại với catalog hiện tại | 1.147 event |
| Kích thước JSON web | 6.732.225 byte, khoảng 6,42 MiB |

Đã chạy exporter vào một file tạm để đối chiếu: kết quả **7.695 POI và nội dung JSON khớp JSON đang lưu**. Vì vậy, không nên kết luận mọi artifact đều cũ. Điểm không đồng bộ xác nhận được tập trung ở các output của notebook so với workbook hiện tại.

### 3.3. Thiếu dữ liệu ở các trường quan trọng

Mẫu số của bảng sau là **8.201 dòng nguồn**, đo bằng giá trị thiếu do pandas nhận diện:

| Trường | Số dòng thiếu | Tỷ lệ |
|---|---:|---:|
| `maps_destination_type` | 4.159 | 50,71% |
| `maps_review_count` | 4.059 | 49,49% |
| `maps_open_hours` | 5.960 | 72,67% |
| `maps_first_open_hours` | 5.960 | 72,67% |
| `Ảnh` | 1.228 | 14,97% |
| `Đánh giá ` | 701 | 8,55% |
| `maps_result_name` | 926 | 11,29% |
| `Từ Khóa` | 100 | 1,22% |

Sau làm sạch, `Unknown` vẫn chiếm **4.154/8.186 POI**. Tên, mô tả, vị trí và tọa độ không có ô trống trong nguồn; điều đó chỉ chứng minh độ đầy đủ cú pháp, không chứng minh đúng thực tế.

Hệ quả:

- Type là thành phần lớn của `context`, nhưng khoảng một nửa catalog không có type để chấm điểm đáng tin cậy.
- Quality bị ảnh hưởng mạnh bởi review chưa có. Một POI thiếu review và một POI thực sự có 0 review bị gom vào cùng giá trị 0.
- “Có giờ mở cửa” mới là cờ tồn tại văn bản; chưa kiểm tra POI đang mở vào thời điểm người dùng đến.
- Việc bù rating bằng median hỗ trợ tính toán, nhưng cần giữ cờ `rating_observed`/`rating_imputed`. Không nên trình bày rating bù như đánh giá thật.

Đáng chú ý, **3.326 dòng thiếu `maps_review_count` nhưng trường `Đánh giá ` có chứa `Reviews`**. Đây là dấu hiệu có thể khôi phục một phần dữ liệu từ chính snapshot, sau khi xác thực rằng chuỗi rating/review thuộc đúng POI. Không nên tự động sao chép hàng loạt trước khi giải quyết chất lượng ghép thực thể.

### 3.4. Ghép sai thực thể là rủi ro lớn nhất của dữ liệu

Trong `scrape_destination()` tại `scripts/scrape_google_maps_browser.py:273`, truy vấn chủ yếu là tên địa điểm. Điều kiện `matched` là trang có `h1` hoặc đọc được `result_name`. Không có kiểm tra bắt buộc về độ giống tên, tỉnh, tọa độ hay định danh địa điểm.

Đã đếm được:

- `matched`: 7.326 dòng.
- `not_found`: 875 dòng.
- `maps_result_name = "Results"`: 2.938 dòng, toàn bộ vẫn mang `matched`.

`Results` là bằng chứng trường tên kết quả không cung cấp định danh POI hữu ích. Không thể suy ra tất cả rating/type của 2.938 dòng này đều sai, nhưng cũng không được lấy tỷ lệ `matched` làm tỷ lệ ghép đúng.

Scraper hiện còn không lưu tên kết quả, URL mới, raw review label, lỗi chi tiết và thời điểm của mỗi lần bổ sung. Trạng thái cũ trong workbook được giữ nguyên trong chế độ chỉ điền thiếu. Như vậy, một dòng có thể chứa các trường được lấy ở nhiều lần truy cập nhưng không đủ dấu vết để xác nhận chúng cùng thuộc một thực thể.

**Hướng sửa:** truy vấn có tên + khu vực; kiểm tra tên/địa chỉ/tọa độ; lưu định danh nhà cung cấp khi có; phân loại `verified`, `ambiguous`, `unmatched`, `needs_review`; lưu bằng chứng từng trường. Tối ưu độ chính xác của tập được tự động chấp nhận trước, phần còn lại đưa vào hàng đợi kiểm duyệt.

### 3.5. Vấn đề tọa độ và suy luận địa giới

**Phát hiện 1 — cụm tọa độ đáng ngờ.** Có 202 POI cùng tọa độ `(10.8658688, 106.692608)`. Trong đó có các tên như “Công viên địa chất Đắk Nông”, “Ngôi nhà quái dị”, “Trận địa pháo 105”, “Dark reef”… Đây là dấu hiệu bất thường cần kiểm tra nguồn, không phải bằng chứng đo lường rằng 202 địa điểm đều sai.

Đối chiếu với `vietnam_destinations_google_maps_browser_hotosm_backup_20260915_163012.xlsx` theo `STT`, cả 202 dòng vẫn khớp tên. Trong backup, nhóm này có **202 cặp tọa độ khác nhau**; chỉ 1 dòng giữ tọa độ như hiện tại, **201 dòng đã thay đổi**. Ví dụ, “Ngôi nhà quái dị” từng ở `(11.934631, 108.430611)`, “Trận địa pháo 105” từng ở `(21.428227, 103.049311)`. Đây là bằng chứng về sự thay đổi tập trung tọa độ giữa hai snapshot; chưa đủ xác định chính xác thao tác nào gây ra hoặc xác nhận mọi tọa độ backup là đúng. Nên dùng backup làm nguồn đối soát để khôi phục có chọn lọc, không ghi đè toàn bảng bằng bản cũ.

**Phát hiện 2 — hai parser URL bất nhất.**

- Exporter chỉ lấy cặp `!3d...!4d...`, bỏ tọa độ viewport `@lat,lng`.
- `fill_location_from_coordinates.py:300` vẫn dùng `@lat,lng` khi thiếu cặp tọa độ place.
- Có 2.901 URL thuộc nhánh chỉ có tọa độ viewport được parser thứ hai chấp nhận.

Tọa độ tâm khung nhìn không đủ để xác nhận tọa độ POI. Khi được gán vào workbook, nó còn kéo theo tỉnh/thành sai và làm sai khoảng cách gợi ý. Dù exporter đã bỏ cách đọc viewport, nó vẫn sử dụng tọa độ workbook nếu không có tọa độ place; không tự khôi phục được các tọa độ đã bị ghi sai trước đó.

**Phát hiện 3 — “nearest boundary” thực tế là gần bounding box.**

`province_for_point()` kiểm tra polygon trước, đây là hướng đúng. Nhưng fallback tại `scripts/fill_location_from_coordinates.py:284` có thể chọn tỉnh theo bbox có diện tích nhỏ hơn. Bước “nearest” tiếp theo dùng khoảng cách đến **hình chữ nhật bao**, không phải khoảng cách tới đường biên polygon. Ngưỡng 25 km cũng không được áp dụng như kiểm tra khoảng cách polygon ở nhánh bbox.

Đối chiếu trực tiếp tọa độ nguồn với cache hiện có:

| Kết quả | Số dòng |
|---|---:|
| Nằm trong polygon | 7.702 |
| Không trong polygon, fallback bbox | 292 |
| Không trong polygon, fallback nearest bbox | 133 |
| Không khớp sau fallback mặc định | 74 |

Tổng cộng **499 dòng không nằm trong polygon** theo phép kiểm tra này. **Không được gọi 499 dòng là “địa điểm ngoài Việt Nam”**: có thể bao gồm bãi biển, đảo, điểm ven bờ, sai số địa giới hoặc sai số tọa độ. Tập này cần kiểm duyệt theo loại hình và nguồn bằng chứng.

Exporter loại POI không nằm trong polygon và có thể ưu tiên tọa độ place từ URL, còn notebook chủ yếu dùng bounding box trên tọa độ workbook. Điều này giải thích một phần khác biệt catalog. Chính sách quá chặt cũng có thể làm rơi POI ven biển đúng; cần trạng thái độ tin cậy thay vì chỉ một quyết định giữ/xóa.

### 3.6. Độ lệch phân bố và tính phù hợp với du lịch

Trong catalog notebook, các vị trí nhiều nhất gồm Hồ Chí Minh 3.056 POI, Hà Nội 664, Đồng Nai 594. Sau `Unknown`, các type phổ biến gồm `Buddhist temple` 622, `Market` 515, `Catholic church` 376, `Place of worship` 341, `Village hall` 246.

Điều này cho thấy tập dữ liệu không phải một mẫu cân bằng của “địa điểm du lịch Việt Nam”. Dữ liệu đang bao gồm nhiều địa điểm sinh hoạt cộng đồng và tôn giáo. Đó không tự thân là sai, nhưng sản phẩm cần quyết định rõ: khám phá địa điểm địa phương hay gợi ý điểm tham quan cho khách du lịch?

Mô tả OSM thường là văn bản theo mẫu có chứa type, địa chỉ, tọa độ và tên nguồn. Chúng giúp lấp ô trống, nhưng không tương đương mô tả trải nghiệm. TF-IDF có thể học các chuỗi lặp do quá trình sinh mô tả, thay vì đặc trưng khiến người dùng thích một địa điểm.

### 3.7. Định danh và artifact không nhất quán

Notebook cấp `poi_id` theo thứ tự sau làm sạch ở cell 14. Exporter cấp `poiId` theo số lượng dòng đã xuất tại `scripts/export_web_data.py:183`. Khi một pipeline loại một dòng mà pipeline kia giữ lại, ID bị lệch.

| ID | Notebook hiện tại | JSON web hiện tại |
|---|---|---|
| `POI-00001` | Bãi Dài Cam Ranh | Tháp Bà Ponagar |
| `POI-00002` | Tháp Bà Ponagar | Thành cổ Diên Khánh |
| `POI-00003` | Thành cổ Diên Khánh | VinWonders Nha Trang |

Ghép theo chuỗi `poi_id`/`poiId` hiện cho **7.695/7.695 cặp có tên khác nhau**. Đây là lỗi hợp đồng định danh nghiêm trọng nếu tích hợp hành vi web với notebook. Web hiện lưu interaction theo `poi.id` số lấy từ `STT`, nên kết quả này **chưa có nghĩa toàn bộ lịch sử localStorage hiện tại đã bị gán nhầm**. Nó chứng minh rằng không thể ghép hai hệ bằng `POI-xxxxx` như đang xuất.

Ngoài ra, 62 event trong `synthetic_user_behavior.xlsx` có số ID lớn hơn 8.186, không còn nằm trong miền ID của catalog notebook tái tạo hiện tại. Các ID còn nằm trong miền cũng chưa được bảo đảm giữ nguyên thực thể.

**Hướng sửa:** cấp ID bền vững một lần, lưu mapping đến ID nguồn và alias; tạo một catalog chuẩn duy nhất cho notebook và web; artifact phải có `dataset_version`, `schema_version`, hash input, commit code và cấu hình mô hình. Không suy ID từ vị trí dòng.

### 3.8. Quyền sử dụng và khả năng công bố dữ liệu

Đây là vấn đề nguồn dữ liệu trực tiếp của dự án, không phải một kết luận pháp lý về từng bản ghi:

- OSM có điều kiện ODbL, yêu cầu attribution và các điều kiện áp dụng khi phân phối cơ sở dữ liệu dẫn xuất. Web đã có dòng ghi công OSM trên bản đồ, nhưng bộ Excel/JSON vẫn cần thông tin giấy phép và nguồn ở cấp dataset. [Quy định OSM](https://www.openstreetmap.org/copyright).
- Điều khoản Google Maps có giới hạn về sao chép nội dung, tải hàng loạt và tái sử dụng. Vì dự án lấy dữ liệu qua trình duyệt rồi xuất bảng/JSON, cần xác định quyền sử dụng phù hợp trước khi phát hành rộng. Báo cáo chưa xác nhận quyền của từng ảnh, rating hoặc mô tả. [Điều khoản Google Maps](https://maps.google.com/help/terms_maps/).
- Chuyển sang Places API không đồng nghĩa mọi dữ liệu đều được lưu vô thời hạn hoặc hiển thị tự do trên bản đồ khác. API có yêu cầu lưu trữ, attribution và hiển thị riêng, cần thiết kế theo phạm vi sử dụng cụ thể. [Chính sách Places API](https://developers.google.com/maps/documentation/places/web-service/policies).

Hướng bền vững là giữ ranh giới nguồn rõ: catalog mở có giấy phép phù hợp, dữ liệu tự biên tập có nguồn, và dữ liệu từ nhà cung cấp được dùng đúng điều kiện. Không trộn tất cả thành các cột `maps_*` rồi mất khả năng truy vết.

## 4. Review thuật toán trước Fuzzy AHP/TOPSIS

### 4.1. Tiền xử lý văn bản và TF-IDF

Notebook chuẩn hóa chữ thường, bỏ dấu tiếng Việt, dùng TF-IDF word unigram/bigram với `max_features=8000`, `min_df=2`, `max_df=0.95`. Điểm nội dung là cosine similarity.

Với cấu hình mặc định tương ứng, IDF có dạng làm trơn:

\[
\operatorname{idf}(t)=\log\frac{1+N}{1+\operatorname{df}(t)}+1,
\qquad
C_i=\frac{\mathbf q^\top\mathbf x_i}{\|\mathbf q\|_2\|\mathbf x_i\|_2}.
\]

TF-IDF là baseline hợp lý cho quy mô hiện tại: đơn giản, không cần dữ liệu hành vi, dễ kiểm tra các từ làm tăng điểm. Nó là mô hình tương đồng từ vựng; cách gọi “semantic preference matching” trong tài liệu có thể làm người đọc kỳ vọng quá mức. [Tài liệu scikit-learn về TF-IDF](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction).

Các hạn chế cụ thể:

- Bỏ dấu giúp tìm kiếm thuận tiện nhưng làm mất một phần phân biệt nghĩa tiếng Việt.
- Không tách từ tiếng Việt theo đơn vị từ ghép; bigram chỉ bù được một phần.
- Truy vấn tiếng Anh trong `EVAL_PROFILES` và mô tả/từ khóa tiếng Việt không có bước ánh xạ ngôn ngữ.
- `min_df=2` có thể loại từ riêng chỉ xuất hiện ở một POI, giảm khả năng tìm đúng tên hiếm.
- Truy vấn rỗng hoặc ngoài vocabulary cho vector 0; cần fallback có chủ đích.
- Từ khóa suy diễn sử dụng phép tìm chuỗi con, có thể phát hiện nhầm từ trong từ khác; cần kiểm tra token/phrase thay vì substring tùy tiện.

Tài liệu nói content không chứa type/location để tránh tính trùng. Code không nối trực tiếp hai cột này, nhưng `infer_keywords()` dùng type, còn mô tả OSM đã chứa type và địa chỉ. Như vậy, tách cột chưa loại được sự trùng lặp thông tin.

### 4.2. Fuzzy string matching

Điểm type/location lấy giá trị lớn nhất giữa `ratio`, `partial_ratio` và `token_set_ratio` của RapidFuzz. Đây là fuzzy matching theo ký tự/token, khác với số mờ tam giác trong Fuzzy AHP.

Ưu điểm là dễ xử lý một số lỗi chính tả và tên viết khác nhau. Hạn chế là phép lấy `max` ưu ái khớp một phần, không xác nhận quan hệ ngữ nghĩa hoặc quan hệ hành chính. `Ha Noi`, `Hanoi`, quận/huyện cũ và tỉnh mới nên được xử lý bằng mã định danh/alias có cấu trúc trước.

Fallback sang `difflib` cũng không tính tương đương hoàn toàn với RapidFuzz. Vì vậy, cùng dữ liệu có thể cho điểm khác tùy môi trường cài đặt. Nên khóa dependency và ghi rõ engine được dùng trong artifact.

### 4.3. Điểm khoảng cách

Haversine trong notebook dùng bán kính Trái Đất `6371.0088 km`, phù hợp để ước lượng khoảng cách đường chim bay:

\[
a=\sin^2\frac{\Delta\varphi}{2}+
\cos\varphi_1\cos\varphi_2\sin^2\frac{\Delta\lambda}{2},
\qquad d=2R\operatorname{atan2}(\sqrt a,\sqrt{1-a}).
\]

Với bán kính ưu tiên hợp lệ \(D>0\), utility tương ứng là:

\[
D_i=\max(0,1-d_i/D).
\]

Công thức có ý nghĩa và chiều tiêu chí đúng: gần hơn cho utility cao hơn. Tuy nhiên:

- Khoảng cách đường chim bay không phải thời gian đi xe, đi bộ hoặc đi phà.
- `max_distance_km` hiện chỉ làm utility bằng 0 khi quá xa; không loại POI khỏi tập hợp lệ.
- Không có vị trí người dùng thì tất cả nhận 1. Vì cột này hằng số, nó không phân biệt các phương án trong khoảng cách TOPSIS; không nên hiểu là mọi POI đều “rất gần”.
- Cần kiểm tra đầu vào hữu hạn, miền latitude/longitude và \(D>0\); có thể clip \(a\) vào `[0,1]` để tránh lỗi số học ở biên.

Tái hiện với profile Nha Trang trong notebook, `top_k=10`: có kết quả Lam Kinh cách khoảng **946 km** dù `max_distance_km=120`. Profile Đà Nẵng trả cả Bãi Dài Cam Ranh cách khoảng **460,3 km**. Đây là hành vi đúng theo code utility mềm hiện tại, nhưng lệch kỳ vọng nếu người dùng hiểu “max distance” là giới hạn bắt buộc.

### 4.4. Điểm chất lượng

Notebook dùng:

\[
Q_i=0.55\frac{r_i}{5}+0.35\,\operatorname{minmax}(\log(1+n_i))
+0.05 I_{image,i}+0.05 I_{hours,i}.
\]

Log review giúp giảm ảnh hưởng của chênh lệch đếm quá lớn. Các hệ số cộng thành 1 nên utility dễ đọc. Nhưng `quality` đang gộp ba khái niệm: mức đánh giá, độ phổ biến và độ đầy đủ thông tin.

Những điểm cần điều chỉnh:

- Rating 5 sao với 1 review và rating ổn định qua nhiều review chưa được mô hình hóa độ tin cậy riêng.
- Điểm ảnh/giờ mở cửa thưởng cho tính đầy đủ dữ liệu, không trực tiếp chứng minh trải nghiệm tốt.
- Review missing biến thành 0; rating missing lại được bù median, hai cách xử lý có giả định khác nhau.
- Min-max phụ thuộc catalog; thêm một cực trị có thể đổi utility của nhiều POI cũ.
- Parser review dạng chuỗi chưa hiểu hậu tố: `1.2K reviews` được đọc thành 12 trong cả helper notebook và exporter. Đây là lỗi parser tái hiện bằng đầu vào tổng hợp, chưa đo mức phổ biến của chuỗi này trong nguồn thật.

Một baseline cải thiện dễ giải thích là rating co về prior:

\[
\hat r_i=\frac{n_i\bar r_i+m\mu}{n_i+m},
\]

với \(\mu\) là mức trung bình tham chiếu và \(m\) là cường độ prior được chọn trên validation. Chỉ áp dụng khi số review và rating thuộc cùng nguồn/thực thể; công thức không khắc phục được ghép sai dữ liệu. Nên tách `quality`, `popularity`, `data_confidence` thành các khái niệm riêng.

### 4.5. Sinh dữ liệu hành vi

Cell 14 tạo 120 user, mỗi user có 5–15 sự kiện, chọn POI không lặp với xác suất:

\[
p(i)\propto 0.35+0.65Q_i.
\]

Action được lấy ngẫu nhiên theo phân phối cố định; timestamp là các offset ngẫu nhiên trong năm 2025 rồi sắp tăng dần. Snapshot chạy lại có 1.147 event, 1.071 item đã xuất hiện, mật độ khoảng **0,1168%** trên ma trận 120 × 8.186.

**Giá trị:** dữ liệu deterministic giúp kiểm tra schema, tính toán và khả năng chạy pipeline.

**Giới hạn:** các user không có sở thích riêng trong quy luật sinh, không có chuyến đi, quan hệ chuyển tiếp, giới hạn địa lý, exposure hoặc xu hướng theo thời gian. Việc gắn `user_id` và timestamp không tự tạo tín hiệu cá nhân hóa.

Do đó, nếu CF/association không dự đoán tốt trên tập này, chưa thể kết luận các thuật toán đó kém cho POI thực. Ngược lại, mô hình có điểm cao cũng chưa chứng minh đáp ứng nhu cầu người thật.

### 4.6. Popularity, association rules và item-based CF

Trọng số action hiện là `view=1`, `click=2`, `save=3`, `like=4`, `visit=5`.

Popularity cộng trọng số các sự kiện theo POI rồi min-max. Đây là baseline hợp lệ, nhưng thứ tự và khoảng cách giữa các action là giả định thiết kế. Một lượt ghé không luôn đồng nghĩa thích, còn click có thể do tò mò hoặc kết quả đặt ở vị trí dễ thấy.

Association rules coi tập POI của một user là một transaction:

\[
\operatorname{support}(A,B)=\frac{N_{AB}}{N_u},\quad
\operatorname{confidence}(A\to B)=\frac{N_{AB}}{N_A},\quad
\operatorname{lift}(A\to B)=\frac{N_{AB}/N_A}{N_B/N_u}.
\]

Các công thức trong code nhất quán với cách đếm này. Tuy nhiên, đây là đồng xuất hiện trong toàn bộ lịch sử, không phải luật “đi A rồi đến B”. Bộ sinh hiện tại chỉ tạo được **2 luật** trên toàn bộ interaction; chưa đủ để coi association là nguồn tín hiệu mạnh. Điểm `confidence × lift` có thể ưu ái các cặp hiếm; nên thêm số quan sát tối thiểu, shrinkage và kiểm tra ổn định.

Item-CF tạo ma trận user-item trọng số, dùng cosine giữa item và các item user đã tương tác:

\[
\hat s_{ui}=\sum_{j\in H_u}\operatorname{cosine}(\mathbf r_i,\mathbf r_j)r_{uj}.
\]

Code tránh tính ma trận item-item đầy đủ bằng cách chỉ so với lịch sử user. Đây là một quyết định tốt. Nhưng pivot vẫn là ma trận dense trên toàn catalog và được dựng lại theo lần gọi; item chưa từng có interaction chỉ có vector 0. Mô hình cũng chưa có giảm trọng số theo thời gian hoặc hiệu chỉnh độ tin cậy khi chỉ có rất ít user chung.

Behavioral hybrid:

\[
B_i=0.30P_i+0.25A_i+0.45CF_i.
\]

Các thành phần được min-max riêng, nhưng cùng khoảng `[0,1]` không có nghĩa cùng độ tin cậy hoặc cùng ý nghĩa thống kê. Một association score dựa trên vài lượt đồng xuất hiện vẫn có thể đạt 1 sau chuẩn hóa.

### 4.7. Candidate generation là điểm nghẽn chất lượng

Với user đã biết:

\[
G_i=0.65B_i+0.35C_i.
\]

Với cold-start: \(G_i=C_i\). Sau đó chỉ giữ candidate pool để xếp hạng đa tiêu chí; `recommend_pois()` mặc định dùng `max(100, top_k × 10)`.

Hạn chế quan trọng:

1. Vị trí và type chưa tham gia bảo đảm candidate recall. POI gần và phù hợp có thể bị loại trước khi TOPSIS nhìn thấy.
2. Query rỗng hoặc không có từ trong vocabulary khiến content bằng 0 toàn bộ. Pool bị chọn theo xử lý hòa điểm/thứ tự dữ liệu, không phải fallback chất lượng hoặc địa lý có chủ đích.
3. Kiểm tra query rỗng với pool 100 xác nhận POI có quality cao nhất toàn catalog (`Central Park`, `POI-05020`) không nằm trong pool. Không dùng ví dụ này để khẳng định POI đó tốt nhất thực tế; nó cho thấy fallback không tối ưu ngay cả theo chính quality của hệ thống.
4. Known-user path chưa loại tất cả item đã xem/ghé trước khi sinh gợi ý. Fixture có một user với một event `visit` đã tái hiện chính POI đó xuất hiện lại trong Top-10. Hành vi này khác evaluator và web, vốn loại lịch sử.
5. `exclude_names` chỉ áp dụng sau khi lấy pool; có thể trả thiếu K mà không bổ sung ứng viên khác.
6. Giá trị K làm thay đổi pool mặc định, do đó cũng có thể thay đổi thứ hạng qua TOPSIS. Top-10 của lần gọi K=10 không được bảo đảm bằng 10 dòng đầu của lần gọi K=20.

Nên tạo hợp của các candidate source — text, địa lý, category, popularity và lịch sử — rồi áp dụng ràng buộc bắt buộc, loại trùng, rerank. Cần đo `CandidateRecall@M` riêng; reranker không thể cứu một POI đã bị loại ở bước trước.

## 5. Review toán học Fuzzy AHP và TOPSIS

### 5.1. Phần triển khai hợp lý

Notebook có ma trận so sánh cặp đầu vào, tính trọng số AHP, CR, số mờ tam giác, geometric mean để tạo fuzzy weights, defuzzification và khoảng cách TOPSIS. Đây là một implementation đa tiêu chí thực sự, có thể đọc và tính lại từng bước.

AHP crisp dùng chuẩn hóa cột và trung bình hàng:

\[
w_i=\frac{1}{n}\sum_j\frac{a_{ij}}{\sum_k a_{kj}},\qquad
\hat\lambda=\frac1n\sum_i\frac{(Aw)_i}{w_i},
\]

\[
CI=\frac{\hat\lambda-n}{n-1},\qquad CR=CI/RI_n.
\]

Đây là cách xấp xỉ trọng số/eigenvalue; không nên mô tả là đã giải eigenvector chính xác. Với ma trận hiện tại, chạy lại được **CR = 0,00296376846**, khớp giá trị làm tròn trong tài liệu.

Fuzzy weights dùng geometric mean theo từng thành phần rồi chuẩn hóa bằng tổng biên ngược:

\[
G_j=\left((\prod_k l_{jk})^{1/n},(\prod_k m_{jk})^{1/n},(\prod_k u_{jk})^{1/n}\right),
\]

\[
\tilde w_j=\left(\frac{G_j^l}{\sum_kG_k^u},\frac{G_j^m}{\sum_kG_k^m},\frac{G_j^u}{\sum_kG_k^l}\right).
\]

Tên “Buckley-style” phù hợp hơn tuyên bố toàn bộ pipeline là một thuật toán chuẩn duy nhất của Buckley. Bài gốc dùng làm nguồn phương pháp là J. J. Buckley, *Fuzzy hierarchical analysis*, 1985; phần kết hợp với TOPSIS và spread điểm trong dự án là lựa chọn triển khai cần mô tả riêng. Đã xác minh thông tin xuất bản/DOI; không coi đó là việc kiểm chứng toàn văn bài gốc hay chứng minh tính đúng của mọi biến thể trong code. [Thông tin bài gốc](https://www.sciencedirect.com/science/article/pii/0165011485900909/pdf).

### 5.2. Một ma trận, hai ý nghĩa tiêu chí

Cell 26 khai báo:

`FUZZY_AHP_CRITERIA = [content, type, location, distance, quality]`.

Cell 27 dùng lại cùng `EXPERT_PAIRWISE_MATRIX` cho:

`TOPSIS_CRITERIA = [behavior, content, distance, quality, context]`.

Về số học, cả hai đều có 5 chiều nên chạy được. Về ý nghĩa, phát biểu “content quan trọng gấp 3 location” ở ma trận cũ bị biến thành “behavior quan trọng gấp 3 distance” ở ranker cuối. Không có bằng chứng trong repository về việc thu thập đánh giá chuyên gia cho sự thay đổi này.

| Vị trí ma trận | Tiêu chí ở `fuzzy_ahp_scores` | Tiêu chí ở `fuzzy_ahp_topsis` | Crisp weight | Defuzzified fuzzy weight |
|---|---|---|---:|---:|
| 1 | content | behavior | 0,297622 | 0,294655 |
| 2 | type | content | 0,157902 | 0,156916 |
| 3 | location | distance | 0,088951 | 0,088514 |
| 4 | distance | quality | 0,157902 | 0,158663 |
| 5 | quality | context | 0,297622 | 0,301252 |

**CR thấp chỉ cho thấy các con số tương đối nhất quán; không xác nhận tên tiêu chí đúng, đánh giá chuyên gia có thật, hay sở thích người dùng được biểu diễn đúng.** Nên khai báo ma trận kèm tên hàng/cột và version; tách hẳn ma trận của diagnostic cũ khỏi ma trận của ranker cuối.

### 5.3. CR đang được ghi nhận, chưa được thực thi

`cr_accepted` là một cờ metadata. Ranker vẫn trả kết quả khi CR cao.

Phép thử với ma trận reciprocal nhưng thiếu nhất quán cho **CR ≈ 0,239206**, vượt 0,10, vẫn xếp hạng bình thường. Một fixture ma trận không reciprocal cũng được nhận, vì ranker chủ yếu kiểm tra shape 5×5. Trong khi đó, fuzzy conversion chỉ dùng tam giác trên rồi tự dựng tam giác dưới; crisp CR và fuzzy weights có thể được tính từ hai tập phán đoán không tương đương.

Cần kiểm tra: shape, finite, dương, đường chéo 1, reciprocal, miền `uncertainty` và `spread`. Với CR vượt ngưỡng, nên yêu cầu sửa đánh giá hoặc dùng một fallback được công bố, thay vì âm thầm tiếp tục rồi chỉ lưu cờ.

### 5.4. Fuzzification có phụ thuộc thứ tự tiêu chí

Code biến giá trị ở tam giác trên thành:

\[
f(a)=(0.8a,a,1.2a),
\]

rồi dựng vị trí reciprocal bằng nghịch đảo. Cách này giữ reciprocal trong ma trận fuzzy, nhưng:

\[
f(1/a)=(0.8/a,1/a,1.2/a)
\ne
f(a)^{-1}=(1/(1.2a),1/a,1/(0.8a)).
\]

Vì vậy, việc một phán đoán nằm ở trên hay dưới đường chéo có thể làm thay đổi spread gán cho nó. Khi đảo thứ tự cả hàng/cột rồi ánh xạ trọng số về thứ tự cũ, phép thử đo được độ lệch lớn nhất **0,00659731** ở defuzzified weight.

Đây là hiệu ứng nhỏ về trị số trong ma trận hiện tại, nhưng đáng sửa về nguyên lý: đổi tên/thứ tự hiển thị tiêu chí không nên tự làm thay đổi mức ưu tiên.

Một hướng sửa là dùng khoảng nhân đối xứng trong miền log, ví dụ `(a/γ, a, aγ)` với `γ>1`, hoặc một bảng số mờ reciprocal được định nghĩa theo ý nghĩa phán đoán. Cần test bất biến theo hoán vị. Với đánh giá “bằng nhau”, phải xác định rõ có bất định hay không và áp dụng nhất quán.

### 5.5. Fuzzy uncertainty chưa được gắn với độ tin cậy dữ liệu

Điểm mỗi tiêu chí được đổi thành:

\[
\tilde x_{ij}=(\max(0,x_{ij}-s),x_{ij},\min(1,x_{ij}+s)),\quad s=0.08.
\]

Tất cả tiêu chí dùng cùng spread; pairwise dùng uncertainty 0,20. Đây là các **siêu tham số do người thiết kế chọn**, chưa phải mức bất định được suy ra từ sai số vị trí, số review hay mức đồng thuận chuyên gia.

Cũng cần nói đúng bản chất: membership fuzzy không phải xác suất, không phải confidence interval. Phép nhân theo từng thành phần của hai triangular fuzzy numbers là một xấp xỉ tam giác thường dùng; không nên mô tả như phép nhân số mờ tổng quát luôn cho kết quả tam giác chính xác.

Nếu muốn phát huy giá trị “fuzzy”, nên gắn bất định với trường dữ liệu: tọa độ suy đoán có khoảng rộng hơn tọa độ xác nhận, type chưa rõ không nên nhận một độ tin cậy giả bằng type đã kiểm tra. Hoặc thu thập phán đoán ngôn ngữ từ nhiều người rồi kiểm tra độ ổn định xếp hạng qua các bộ trọng số.

### 5.6. `H = A × W` trong tài liệu chưa mô tả chính xác ranker cuối

Hàm diagnostic `fuzzy_ahp_scores()` tính:

\[
\tilde H_i=\sum_j\tilde x_{ij}\tilde w_j,
\]

rồi defuzzify thành một điểm trên mỗi POI.

Trong `fuzzy_ahp_topsis()` thực tế, biến `fuzzy_h` là tensor **số ứng viên × số tiêu chí × 3**, chứa tích từng tiêu chí với trọng số; chưa cộng theo tiêu chí. Code tính:

\[
z_{ij}=\frac{x^l_{ij}w^l_j+x^m_{ij}w^m_j+x^u_{ij}w^u_j}{3},
\]

\[
r_{ij}=\frac{z_{ij}}{\sqrt{\sum_i z_{ij}^2}},\qquad
v_{ij}=r_{ij}\bar w_j,
\]

với \(\bar w_j\) là defuzzified weight đã chuẩn hóa. Sau đó:

\[
v_j^+=\max_i v_{ij},\quad v_j^-=\min_i v_{ij},
\]

\[
d_i^+=\sqrt{\sum_j(v_{ij}-v_j^+)^2},\quad
d_i^-=\sqrt{\sum_j(v_{ij}-v_j^-)^2},\quad
T_i=\frac{d_i^-}{d_i^++d_i^-}.
\]

`final_score = T_i`. Còn `fuzzy_h_score = Σ_j z_ij` chỉ là giá trị chẩn đoán, không phải một vector một chiều được đưa trực tiếp vào TOPSIS. Tài liệu cần sửa cách gọi và kích thước ma trận để người đọc phân biệt hai thuật toán.

**Không nên vội kết luận “code nhân trọng số hai lần nên chắc chắn thành bình phương trọng số”.** Khi fuzzy spread và uncertainty bằng 0, phép nhân trọng số đầu có thể bị triệt tiêu bởi chuẩn hóa cột, rồi trọng số được áp dụng ở bước sau. Với spread không bằng 0, hiệu ứng phức tạp hơn.

Với \(s<x_{ij}<1-s\), có thể rút gọn từ chính code:

\[
z_{ij}=a_jx_{ij}+b_j,\quad
a_j=(w_j^l+w_j^m+w_j^u)/3,\quad
b_j=s(w_j^u-w_j^l)/3.
\]

Điều này cho thấy một phần tác động fuzzy tương đương biến đổi affine theo từng cột; clipping ở 0/1 làm biến đổi thành từng đoạn. Độ phức tạp thêm cần được chứng minh bằng ablation, không thể suy lợi ích chỉ từ tên thuật toán.

### 5.7. Tính trùng tiêu chí và thang đo

Context được định nghĩa:

\[
X_i=0.60\,Type_i+0.25\,Location_i+0.15\,Content_i.
\]

Content vì thế có mặt trực tiếp trong một tiêu chí và gián tiếp trong context. Trong dữ liệu mô phỏng, behavior cũng có nguồn gốc một phần từ quality. Các tiêu chí không độc lập về thông tin.

Điều đó không tự làm MCDA vô hiệu, nhưng cách giải thích “mỗi tiêu chí đo một khía cạnh riêng, không tính trùng” là quá mạnh. Cần đo tương quan, làm ablation bỏ thành phần trùng, và giải thích trọng số theo tác động thực tế. Không lấy các hệ số trung gian rồi cộng cơ học để diễn giải trọng số hiệu dụng của TOPSIS phi tuyến.

### 5.8. Điểm TOPSIS phụ thuộc candidate pool

Chuẩn hóa vector và ideal best/worst đều được tính trên tập ứng viên hiện tại. Thêm hoặc bỏ ứng viên có thể làm đổi điểm, thậm chí thứ tự giữa những POI giữ nguyên. Đây là đặc tính cần kiểm soát khi dùng TOPSIS trong hệ truy xuất; nghiên cứu về TOPSIS cũng xem lựa chọn chuẩn hóa là một phần quan trọng của phương pháp. [Nghiên cứu về chuẩn hóa TOPSIS](https://www.sciencedirect.com/science/article/pii/S2215016123002248).

Hệ quả sản phẩm:

- `0.8` ở hai truy vấn khác nhau không nhất thiết cùng mức phù hợp.
- `min_final_score` không phải ngưỡng xác suất chọn địa điểm.
- Hiển thị `topsisScore × 100` kèm `%` dễ khiến người dùng tưởng là xác suất hài lòng.
- Khi chỉ có một ứng viên hoặc mọi điểm như nhau, cả hai khoảng cách bằng 0 và code trả 0; không nên diễn giải là ứng viên duy nhất hoàn toàn không phù hợp.

Nên gọi là “điểm ưu tiên tương đối”, kèm lý do gợi ý. Nếu cần điểm có thể so sánh qua thời gian/truy vấn, phải xác định thang utility và điểm neo ổn định, hoặc hiệu chuẩn bằng dữ liệu độc lập.

## 6. Review thiết kế đánh giá và các chỉ số

### 6.1. Hai bộ evaluation hiện tại đang đo những gì?

| Bộ đánh giá | Dữ liệu/nhãn | Mô hình thật sự được gọi | Khả năng kết luận |
|---|---|---|---|
| Weak-label theo 4 profile, cell 35 | Nhãn được sinh bằng tổng trọng số content/type/location/distance/quality | Các baseline và `fuzzy_ahp_scores()` cũ | Đo mức đồng thuận với oracle tự thiết kế; không phải chất lượng đối với người dùng |
| Chronological, cell 37 | Giữ event cuối mỗi user mô phỏng làm test | Popularity, association, item-CF, behavioral hybrid, content | Có thể kiểm tra cơ chế split/scoring; đang có rò rỉ đáp án ở content và chưa thử ranker cuối |

README nói đường gợi ý cuối cùng được đánh giá chronological. Nhưng `evaluate_chronological()` **không gọi** `recommend_pois()` hoặc `fuzzy_ahp_topsis()`. Nhãn `fuzzy_ahp` trong weak evaluation lại dùng 5 tiêu chí cũ và không có TOPSIS.

Đây là khoảng trống quan trọng nhất khi muốn chứng minh “hybrid + Fuzzy AHP + TOPSIS cải thiện chất lượng”. Hiện các metric không đo đúng hệ thống mà lời giới thiệu đang nói tới.

### 6.2. Rò rỉ đáp án trong chronological evaluation

Trong cell 37, trước khi gọi scorer, code đọc chính POI test:

```python
poi = df.loc[df["poi_id"].eq(held_out.poi_id)].iloc[0]
profile = {
    "query": poi["content_text"],
    "preferred_types": [poi["poi_type"]],
    "preferred_locations": [poi["location"]],
}
```

Content model được hỏi bằng chính văn bản đã dùng để tạo vector của đáp án. Cosine của vector với chính nó bằng 1 nếu vector khác 0, nên việc truy hồi đúng POI gần như đã được cung cấp sẵn thông tin quyết định.

Kết quả chạy lại trên dữ liệu hiện tại:

| Mô hình | HitRate@10 | Recall@10 | MRR@10 | NDCG@10 | Coverage@10 |
|---|---:|---:|---:|---:|---:|
| `content_cold_start` | 1,000000 | 1,000000 | 1,000000 | 1,000000 | 0,108967 |
| `association_rules` | 0,008333 | 0,008333 | 0,000833 | 0,002409 | 0,001222 |
| `behavioral_hybrid` | 0 | 0 | 0 | 0 | 0,057415 |
| `item_based_cf` | 0 | 0 | 0 | 0 | 0,059614 |
| `popularity` | 0 | 0 | 0 | 0 | 0,001710 |

Có 120 user test. Content đúng 120/120; association đúng 1/120 ở hạng 10. **Không dùng bảng này để xếp hạng năng lực thật của các thuật toán**, vì các mô hình không được cung cấp cùng một lượng thông tin hợp lệ.

Phép thử đối chứng: tạo query bằng cách nối nội dung những POI chỉ nằm trong train history của user, không dùng POI test; giữ TF-IDF, loại item trong lịch sử, lấy Top-10. Kết quả là **0/120 hit**. Đây là chẩn đoán cho thấy kết quả 100% không tồn tại dưới đầu vào lịch sử hợp lệ; chưa phải một mô hình content đã tối ưu hoặc benchmark người dùng thật.

Có thể giữ bài kiểm tra truy hồi bằng chính văn bản POI, nhưng nên đặt tên “self-retrieval sanity check”, tách khỏi đánh giá gợi ý.

### 6.3. Split theo thời gian mới bảo toàn thứ tự từng user

`chronological_split()` giữ event cuối mỗi user, nhưng train chung vẫn có thể chứa sự kiện của user khác xảy ra sau thời điểm dự đoán của user đang test.

Kiểm tra hiện tại: **102/120 thời điểm test có ít nhất một event train xảy ra sau nó**. Điều này không xóa bỏ giá trị kiểm tra leave-last-out, nhưng khiến nó không mô phỏng đúng một hệ thống chỉ nhìn dữ liệu đã biết ở thời điểm dự đoán.

Nên dùng mốc thời gian toàn cục hoặc replay theo thời gian: mô hình cho thời điểm `t` chỉ học interaction có timestamp trước `t`. Validation cũng phải nằm trước test. Các rủi ro do bỏ qua global timeline đã được nghiên cứu trong offline recommender evaluation. [Nghiên cứu về data leakage](https://arxiv.org/abs/2010.11060).

Đối với dữ liệu mô phỏng năm 2025 trong khi metadata POI là snapshot khác thời điểm, cũng không nên coi kết quả là một backtest lịch sử thật. Nếu sau này có log thật, cần quản lý cả thời điểm cập nhật feature như review/rating.

### 6.4. Weak labels có tính vòng tròn

Oracle hiện tại:

\[
O_i=0.25C_i+0.15Type_i+0.15Location_i+0.20D_i+0.25Q_i.
\]

Nhãn relevant là top 5% theo oracle. Trong khi đó, các mô hình được chấm dùng chính những thành phần này. Điểm cao chứng minh mô hình gần với tiêu chuẩn do tác giả đặt ra, không chứng minh đúng sở thích ngoài hệ thống.

Vẫn có thể dùng oracle để kiểm tra hành vi mong muốn, nhưng phải gọi là **diagnostic theo utility giả định**, không phải accuracy thực. Bốn profile cũng quá ít để đánh giá đa dạng nhu cầu, vùng địa lý và nhóm người dùng.

Với 8.186 POI, mỗi profile hiện có 410 relevant. Lấy 10 kết quả thì recall tối đa theo quy ước này chỉ là `10/410 ≈ 2,439%`. Vì thế recall nhỏ không tự là dấu hiệu thuật toán yếu; phải đọc cùng số relevant và K.

### 6.5. AP@K đang bỏ qua relevant không được tìm thấy

`average_precision_at_k()` tính trung bình precision chỉ tại những vị trí hit tìm được trong Top-K. Mẫu số bằng số hit đã tìm thấy, khiến việc bỏ sót nhiều relevant không bị phạt đúng ý nghĩa AP.

Một quy ước AP@K phổ biến cần được công bố rõ là:

\[
AP@K=\frac{\sum_{r=1}^{K} P@r\cdot rel_r}{\min(K,R)},
\]

với \(R\) là tổng relevant trong tập đánh giá. Một số protocol dùng \(R\) làm mẫu số thay vì \(\min(K,R)\); dù chọn quy ước nào cũng không nên dùng số hit tìm được làm mẫu số. Nguyên tắc AP/MAP là relevant không truy hồi được không biến mất khỏi cách chuẩn hóa. [Tài liệu Information Retrieval của Stanford](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html).

Phản ví dụ đã chạy: có ít nhất 10 relevant, Top-10 chỉ đúng ở hạng 1, vector `[1,0,0,0,0,0,0,0,0,0]`. Code trả **AP@10 = 1,0**. Theo quy ước mẫu số `min(K,R)`, giá trị phải là **0,1**.

Tên `map@10` ở bảng từng profile cũng nên là `ap@10`; chỉ sau khi lấy trung bình qua profile mới gọi là MAP.

### 6.6. NDCG@K đang dùng ideal chỉ trong tập đã lấy về

`ndcg_at_k()` lấy gains của Top-K do mô hình trả, rồi sort chính gains này để tạo IDCG. Nó chủ yếu đo thứ tự của các item đã tìm được và bỏ qua item relevant tốt hơn chưa được tìm thấy.

Cách tính đúng theo tập ứng viên đánh giá đã định nghĩa:

\[
DCG@K=\sum_{r=1}^{K}\frac{g(rel_r)}{\log_2(r+1)},\qquad
NDCG@K=\frac{DCG@K}{IDCG@K}.
\]

`IDCG@K` phải lấy từ Top-K gains lý tưởng của **toàn tập được đánh giá**, không phải chỉ các item mô hình đã trả. Cần công bố gain nhị phân, gain trực tiếp hoặc `2^rel−1` rồi dùng nhất quán. [Định nghĩa NDCG trong scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html).

Với phản ví dụ chỉ có một hit ở hạng 1 và có ít nhất 10 relevant bằng nhau, code trả **NDCG@10 = 1,0**. IDCG đúng gồm 10 relevant nên kết quả chỉ khoảng **0,2201**.

Đối chiếu thực tế bằng profile Nha Trang tiếng Việt ở phần Examples, giữ nguyên ranking và oracle, chỉ thay cách tạo IDCG:

| Mô hình diagnostic | NDCG cũ | NDCG với ideal toàn catalog |
|---|---:|---:|
| `popularity_baseline` | 0,939004 | 0,550499 |
| `distance_baseline` | 0,967755 | 0,833916 |
| `equal_weight_baseline` | 0,999805 | 0,999158 |
| `fuzzy_ahp` | 0,999536 | 0,997685 |

Đây là một profile riêng, không phải bảng trung bình 4 `EVAL_PROFILES`. Sửa mẫu số vẫn chưa giải quyết việc oracle là nhãn tự sinh.

### 6.7. Các chỉ số khác cần giải thích đúng

- `HitRate@K` và `Recall@K` ở chronological bằng nhau là hợp lý khi mỗi user chỉ có một positive test. Không nên coi chúng là hai bằng chứng độc lập.
- `_mrr()` và `_ndcg()` của chronological có công thức phù hợp với một positive; lỗi NDCG ở mục trên thuộc hàm weak evaluation, không phải mọi hàm NDCG trong dự án.
- `type_diversity = số type khác nhau / số kết quả` chỉ là đa dạng nhãn. Với nhiều `Unknown`, chỉ số dễ bị méo; nó cũng không đo đa dạng trải nghiệm hoặc khoảng cách ngữ nghĩa.
- Catalog coverage phụ thuộc số user/profile. Với 4 profile và K=10, cận trên chỉ là `40/8186 ≈ 0,4886%`, ngay cả khi không có item nào trùng giữa các profile. Không so trực tiếp với coverage trên 120 user.
- `precision_at_k()` chia theo số phần tử thực tế, không cố định K khi danh sách ngắn. Hiện full catalog đủ dài nên không làm sai bảng đang đo, nhưng cần thống nhất quy ước khi có hard filter hoặc thiếu ứng viên.
- Khi nhiều item hòa điểm 0, nên dùng tie-break ổn định và baseline random theo seed; tránh để thứ tự catalog trở thành mô hình ngầm.

Với catalog hơn 8.000 item và chỉ một đáp án mỗi user, một bộ chọn ngẫu nhiên 10 item chỉ có xác suất hit khoảng 0,12%/user nếu giả sử phân phối đều. Với 120 user, số hit kỳ vọng chỉ khoảng 0,15. Đây chỉ là phép tính minh họa theo giả định đều, nhưng cho thấy “0 hit” trên mẫu nhỏ không đủ chứng minh một phương pháp vô dụng.

## 7. Review mã nguồn, kiến trúc và web

### 7.1. Những điểm làm tốt

- Chia notebook thành các phần preprocessing, behavior, content, hybrid, ranking và evaluation, giúp theo dõi mục đích từng bước.
- Có baseline và xuất điểm trung gian; dễ truy nguyên vì sao một POI đứng cao.
- Tách tác vụ scraping khỏi notebook, tránh mạng trở thành điều kiện bắt buộc mỗi lần thử mô hình.
- Scraper chỉ điền ô thiếu, có lưu tiến độ; script sửa vị trí có backup và dry-run.
- Có lọc bounding box và dedup trong notebook; xử lý polygon có chuẩn bị geometry để giảm chi phí lặp.
- Web sử dụng cấu trúc đơn giản, dễ chạy cục bộ; có empty/error state, lazy loading ảnh, aria-label ở nhiều điều khiển và attribution OSM.
- Item-CF tránh dựng similarity toàn bộ N×N; đây là lựa chọn phù hợp hơn với catalog hiện tại.

Các điểm này cho thấy project đã vượt mức tập hợp công thức rời rạc. Vấn đề là sự liên kết giữa các phần chưa đủ chặt để coi toàn hệ thống đã được kiểm chứng.

### 7.2. So sánh notebook với web

| Thành phần | Notebook | Web hiện tại |
|---|---|---|
| Catalog | 8.186 POI, bbox + dedup | 7.695 POI, exporter kiểm tra polygon; còn 5 dòng trùng chính xác tên/tọa độ |
| Content | TF-IDF + cosine | Token overlap `shared/max(token counts)` |
| Văn bản content | Tên, result name, mô tả, keyword | Cả tên, result name, type, location, mô tả, keyword |
| Behavior | Action popularity + association + item-CF | Personal/global counts và độ giống với POI gần nhất trong lịch sử |
| Khoảng cách | Haversine nếu có tọa độ user | `distanceScore = 1` cho mọi item |
| Trọng số | Fuzzy weights từ ma trận so sánh cặp | `[0.30, 0.20, 0.15, 0.20, 0.15]` cố định |
| Fuzzy evaluation | Có | Không có |
| Candidate pool | Theo K, mặc định tối thiểu 100 | 80 |
| Top-K giao diện | Hàm Python nhận K | 8 |
| Loại lịch sử | Chưa thống nhất ở API gợi ý | Có loại các ID trong lịch sử user |
| Missing rating | Bù theo type/global median | Dùng rating 0 trong quality nếu thiếu |

Ghép theo `STT`/`id` của cùng POI, có **681 dòng lệch quality hơn 0,001** giữa notebook và web, liên quan các bản ghi thiếu rating. Các POI này cũng nằm trong nhóm web hiển thị chưa có rating.

Vì thế, cần công bố web là bản demo heuristic riêng, hoặc cho web dùng chung mô hình/backend. Không dùng chất lượng giao diện web làm bằng chứng đã triển khai Fuzzy AHP của notebook.

### 7.3. Lỗi nghiệp vụ và trạng thái giao diện đã tái hiện

**Bộ lọc không áp dụng cho gợi ý.** `filterPois()` tạo `state.filtered`, nhưng `recommendationRows()` vẫn đọc `state.pois`. Trong mô phỏng DOM/Leaflet, chọn tỉnh **Đà Nẵng** cho 230 POI trong danh sách lọc, nhưng 8 gợi ý giữ nguyên và thuộc Hồ Chí Minh, Lâm Đồng, Ninh Bình, Tuyên Quang, Quảng Trị, Cà Mau, Sơn La. Người dùng dễ hiểu nhầm bộ lọc là yêu cầu chung của hệ thống.

**Nút lưu trên chi tiết mặc định không ghi sự kiện.** `render()` hiển thị POI đầu tiên khi chưa chọn, nhưng không gán `state.selectedId`. Handler lưu lại tìm item bằng `selectedId`. Phép thử bấm lưu trên panel ban đầu ghi 0 event; sau `selectPoi()` thì ghi được 1 event. Cần đồng bộ POI đang hiển thị và POI mục tiêu của thao tác.

**Thu thập hành vi chưa bao phủ hành vi chính.** Chế độ `new` không ghi interaction; bấm card/marker chủ yếu chọn POI, còn click event được ghi ở recommendation item. Các action `view` và `like` tồn tại trong weights nhưng chưa có luồng UI đầy đủ tương ứng. Nếu mở rộng thành log thật, dataset sẽ bị lệch theo nơi gắn event.

**Personal count chưa tạo tác dụng như tên gọi gợi ý.** Web cộng điểm trực tiếp cho POI trong lịch sử, nhưng các POI đó lại bị loại khỏi tập gợi ý. Tác động cá nhân hóa còn lại chủ yếu đến độ giống với item cuối lịch sử và các hiệu ứng chuẩn hóa, không phải collaborative filtering được huấn luyện.

### 7.4. An toàn khi render dữ liệu

`imageMarkup()` ở `web/app.js:74` chèn `poi.image` trực tiếp vào thuộc tính `src` trong chuỗi HTML. Trong khi tên và nhiều nội dung khác dùng `escapeHtml`, URL ảnh chưa được xử lý tương tự.

Đã thử một chuỗi fixture vô hại có dấu nháy và `data-audit`: thuộc tính mới xuất hiện trong HTML được sinh. Đây là bằng chứng có thể thoát khỏi thuộc tính `src`; **chưa thực thi payload tấn công trong trình duyệt và không kết luận dữ liệu hiện tại đang chứa mã độc**.

`href` Google Maps đã escape HTML nhưng chưa kiểm tra scheme. Escape không thay thế được kiểm tra URL. Nên tạo DOM bằng thuộc tính phù hợp, kiểm tra URL chỉ theo scheme/host được chấp nhận, và hạn chế inline event handler. [Hướng dẫn OWASP về output encoding và URL context](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html).

Mức độ ưu tiên tăng rõ nếu cho người khác nhập/chỉnh sửa dữ liệu hoặc triển khai công khai. Đây là lỗi code cần sửa, dù bản demo hiện chạy cục bộ.

### 7.5. Khả năng bảo trì và tái lập

Các vấn đề đáng chú ý:

- Logic preprocessing, parser, quality và ID được lặp ở notebook/exporter/web và đã lệch nhau.
- Các hàm dùng global `df`, `interactions`, vectorizer và mutable `FUZZY_AHP_INFO`; không có model object hoặc artifact được truyền rõ ràng.
- `fuzzy_ahp_scores()` và `fuzzy_ahp_topsis()` cùng cập nhật thông tin global nhưng theo hai bộ tiêu chí. `weights_table` cũng phụ thuộc hàm đã chạy trước đó, làm tăng nguy cơ notebook bị chạy sai thứ tự.
- `warnings.filterwarnings('ignore')` tắt toàn bộ cảnh báo, có thể che phép chia 0 hoặc cảnh báo thư viện cần điều tra.
- `requirements.txt` không pin version; không có lockfile và cấu hình môi trường tái lập. Hướng dẫn mở notebook chưa chỉ rõ dependency cho notebook frontend/kernel nếu môi trường chưa có sẵn.
- Không thấy bộ test/CI được theo dõi trong Git. Các helper kiểm tra trong `.venv` là công cụ cục bộ, không phải test suite có thể tái lập từ checkout sạch.
- Output Excel lớn và backup nằm trong Git nhưng chưa có manifest phiên bản dữ liệu. Thời gian sửa file không đủ xác nhận output được tạo từ input nào.
- Tên cột `Đánh giá ` có khoảng trắng cuối và schema dựa trên văn bản tiếng Việt gây coupling; nên giữ tên hiển thị nhưng có schema nội bộ ổn định.
- `export_web_data.py` có bắt lỗi boundary rồi tiếp tục. Nếu tải/import boundary thất bại, chính sách lọc thay đổi; cần đưa trạng thái này vào artifact hoặc dừng xuất theo chế độ strict.
- Một số `.get(column, [])` rồi `zip` trong exporter không bảo đảm độ dài đúng khi thiếu cột; cần validate schema trước khi duyệt bảng.
- Scraper ghi Excel trực tiếp, không atomic; checkpoint giúp giảm mất dữ liệu nhưng không bảo vệ hoàn toàn khi tiến trình dừng giữa lúc ghi. Vòng lỗi thường bỏ chi tiết nguyên nhân; không có audit trail để sửa dữ liệu đã ghép nhầm.

Không có backend, tài khoản hay database chưa phải lỗi cho một demo local. Chỉ trở thành khoảng trống bắt buộc khi phạm vi chuyển sang nhiều người dùng hoặc vận hành thật.

### 7.6. Hiệu năng và trải nghiệm

Với khoảng 8.000 POI, xử lý trên máy cá nhân còn khả thi. Tuy nhiên:

- Web tải toàn bộ JSON khoảng 6,42 MiB và tính lại nhiều chuỗi/search score trên main thread.
- Danh sách chỉ render 120 item, map chỉ render 650 marker, nhưng thống kê vẫn nói về toàn bộ tập lọc; chưa có phân trang/load more để tiếp cận các item còn lại.
- Gõ filter có thể dựng lại marker và fit map liên tục; recommendation query cũng tính ngay mỗi lần nhập, chưa có debounce.
- CSS dành sidebar `56vh` trên màn hình nhỏ trong khi có header, bộ lọc và panel gợi ý; cần kiểm tra bằng trình duyệt thật để biết phần danh sách còn đủ diện tích hay không. Đây là rủi ro đọc từ CSS, chưa phải lỗi hiển thị đã xác minh.
- Behavioral scoring ở Python dựng pivot/mine rules lặp lại. Trong final path, behavior/content/criteria còn được tính nhiều lần; nên tách fit, retrieval và inference, cache các thành phần dùng chung.

Chưa đo p50/p95, mức RAM đỉnh, số request đồng thời hoặc hiệu năng điện thoại. Không nên suy SLA từ việc notebook chạy xong trên một máy.

## 8. Đánh giá công tâm như một sản phẩm/project

| Khía cạnh | Đánh giá | Cơ sở |
|---|---|---|
| Ý nghĩa bài toán | Có giá trị | Nhu cầu chọn POI theo ngữ cảnh và nhiều tiêu chí là rõ ràng |
| Giá trị học tập | Tốt | Có dữ liệu, preprocessing, baseline, recommendation, MCDA và giao diện |
| Tính mới thuật toán | Chưa được chứng minh | Chủ yếu tích hợp phương pháp đã biết; chưa có giả thuyết hoặc thực nghiệm tách đóng góp mới |
| Dữ liệu | Nhiều nhưng độ tin cậy không đồng đều | Thiếu loại/review, ghép thực thể đáng ngờ, mất provenance, tọa độ bất thường |
| Tính đúng của công thức | Có phần đúng, có lỗi quan trọng | AHP/TOPSIS tính được; AP/NDCG weak evaluation sai chuẩn hóa; fuzzy conversion phụ thuộc thứ tự |
| Cá nhân hóa | Mức mô phỏng | Chưa có log thật hoặc simulator có sở thích riêng |
| Bằng chứng hiệu quả | Chưa đạt | Leakage, oracle vòng tròn, không đánh giá final ranker |
| Trải nghiệm demo | Có nền tảng | Bản đồ, bộ lọc, gợi ý, chi tiết; còn lỗi filter và selection state |
| Khả năng giải thích | Có tiềm năng | Điểm trung gian rõ, nhưng chưa chuyển thành lý do có ích cho người dùng |
| Sẵn sàng vận hành | Chưa đạt | Dữ liệu/model contract, test, versioning và deployment chưa hoàn chỉnh |

Không nên đánh đồng “chưa đủ bằng chứng” với “thuật toán chắc chắn không hiệu quả”. Dự án có thể được cải thiện đáng kể mà không phải thay toàn bộ kiến trúc hoặc bỏ Fuzzy AHP. Nhưng cũng không nên bảo vệ độ phức tạp hiện tại bằng kết quả 100% đang có.

Nếu đánh giá như đồ án DSS, phần ra quyết định có thể là trọng tâm học thuật hợp lý. Muốn thuyết phục, cần cho thấy người dùng/chuyên gia thực sự cung cấp ưu tiên, mô hình tuân thủ ràng buộc và kết luận được kiểm tra độc lập.

## 9. Danh sách vấn đề theo mức ưu tiên

Quy ước: **P0** cần xử lý trước khi dùng kết quả để khẳng định chất lượng; **P1** cần xử lý trước pilot đáng tin cậy; **P2** tối ưu/mở rộng sau khi nền tảng ổn định. Đây là mức ưu tiên của project, không phải thang phân loại sự cố sản xuất.

| ID | Mức | Vấn đề và bằng chứng | Hướng sửa | Điều kiện nghiệm thu |
|---|---|---|---|---|
| R01 | P0 | Query test chứa nội dung đáp án, cell 37 | Chỉ dùng thông tin có trước dự đoán | Thay metadata POI test không được làm thay query đầu vào |
| R02 | P0 | Evaluator không gọi final ranker | Đánh giá đúng `recommend_pois` với model fit trên train | Báo cáo có kết quả cùng protocol cho final model và baseline |
| R03 | P0 | AP/NDCG weak-label sai mẫu số/ideal | Định nghĩa metric chuẩn, fixtures độc lập | Phản ví dụ một hit không trả AP=NDCG=1 khi còn nhiều relevant |
| R04 | P0 | Tọa độ/ghép thực thể đáng ngờ | Dừng dùng viewport như place, audit matching, khôi phục provenance | Có tập đối soát và precision ghép thực thể được đo thủ công |
| R05 | P0 | ID notebook/web lệch, artifact cũ | ID bền vững, một catalog chuẩn, manifest | Một ID luôn ánh xạ cùng thực thể qua export/retrain |
| R06 | P1 | Một pairwise matrix mang hai bộ tiêu chí | Ma trận có nhãn và version riêng | Tên hàng/cột phải khớp model schema |
| R07 | P1 | CR không chặn, thiếu matrix validation | Validate input và công bố fallback | Reject/fallback có chủ đích với CR cao, NaN, không reciprocal |
| R08 | P1 | Fuzzy weights phụ thuộc hoán vị | Mapping fuzzy reciprocal nhất quán | Test hoán vị trả cùng trọng số sau ánh xạ ngược |
| R09 | P1 | Candidate bỏ qua ràng buộc và query rỗng | Multi-source retrieval, hard filter, fallback | Không trả POI vi phạm yêu cầu bắt buộc; đo candidate recall |
| R10 | P1 | Web không dùng filter cho gợi ý | Dùng cùng request/profile cho list và recommendation | Chọn tỉnh thì gợi ý tuân thủ phạm vi hoặc UI giải thích rõ ngoại lệ |
| R11 | P1 | Save trên detail mặc định không ghi | Đồng bộ selected/displayed POI | Test thao tác ban đầu và sau lọc đều ghi đúng ID |
| R12 | P1 | URL ảnh chưa encode/validate | DOM API và URL allowlist | Fixture dấu nháy không sinh thuộc tính ngoài ý muốn |
| R13 | P1 | Hơn nửa type thiếu, review bỏ sót | Schema nguồn, parser, ontology, kiểm duyệt | Đo completeness và correctness riêng, không chỉ lấp ô trống |
| R14 | P1 | Split có dữ liệu tương lai | Global time split hoặc replay | Mọi input train đều có trước cutoff tương ứng |
| R15 | P1 | Quyền phân phối dữ liệu chưa rõ | Manifest giấy phép và tách nguồn | Dataset công bố có nguồn/quyền sử dụng truy vết được |
| R16 | P2 | Lặp tính toán, dense pivot, UI tải cả catalog | Fit/cache, sparse/top-neighbor, pagination/debounce | Benchmark theo tải và thiết bị mục tiêu |
| R17 | P2 | Điểm phần trăm dễ hiểu sai | Điểm ưu tiên tương đối + lời giải thích | Không tuyên bố score là xác suất khi chưa hiệu chuẩn |
| R18 | P2 | Dependency/test/artifact chưa tái lập | Khóa môi trường, tests/CI, versioned build | Checkout sạch có thể tạo cùng artifact và báo cáo kiểm thử |

## 10. Hướng cải thiện khả thi, theo chi phí và lợi ích

### 10.1. Phương án ít chi phí: làm đúng một DSS đơn giản

Giữ TF-IDF, các utility rõ ràng và một mô hình tổng trọng số/AHP crisp làm baseline sản phẩm. Tập trung:

1. Chọn một vùng thử nghiệm, kiểm tra các POI sẽ xuất hiện trong demo.
2. Tạo catalog chuẩn có ID bền vững, nguồn và cờ xác minh.
3. Chuẩn hóa tỉnh/type bằng taxonomy và alias; không phụ thuộc fuzzy text cho định danh.
4. Hard filter theo vị trí, trạng thái, yêu cầu người dùng.
5. Query rỗng thì dùng POI hợp lệ gần vị trí và có thông tin đáng tin cậy; có thể hỏi thêm sở thích.
6. Chia sẻ cùng một scoring implementation giữa kiểm thử và giao diện.
7. Sửa evaluation, đo baseline và final model trên cùng tập.
8. Hiển thị lý do: gần bao nhiêu km, khớp nhu cầu nào, dữ liệu nào còn chưa xác nhận.

**Lợi ích:** giảm sai sót có thể nhìn thấy ngay; dễ giải thích, dễ bảo vệ đồ án. **Đánh đổi:** chưa khai thác ngữ nghĩa sâu hay hành vi quy mô lớn. Với dữ liệu hiện tại, đây là phương án có tỷ lệ lợi ích/công sức tốt nhất theo nhận định review.

### 10.2. Phương án chi phí vừa: giữ Fuzzy AHP và chứng minh nó hữu ích

Thay vì bỏ Fuzzy AHP, làm rõ câu hỏi nghiên cứu: “Khi đánh giá ưu tiên hoặc dữ liệu POI có bất định, Fuzzy AHP có làm danh sách ổn định và phù hợp hơn không?”.

Các bước:

- Thu thập pairwise judgments từ người dùng/chuyên gia theo một bộ tiêu chí thống nhất; lưu số người tham gia và bối cảnh đánh giá.
- Nếu dùng nhiều người, công bố cách tổng hợp và cách xử lý bất đồng; không chỉ ghi nhãn `EXPERT` cho ma trận ví dụ.
- Sửa fuzzification phụ thuộc thứ tự; gắn uncertainty vào nguồn có nghĩa.
- Chạy ablation `crisp weighted sum`, `crisp AHP + TOPSIS`, `fuzzy aggregation`, `fuzzy AHP + TOPSIS` trên cùng candidate pool.
- Đo stability khi thay đổi judgment, spread, candidate pool; report cả trường hợp không tốt hơn.
- Bổ sung mức tin cậy của dữ liệu và test trạng thái thiếu dữ liệu, mọi điểm bằng nhau, chỉ một ứng viên.

**Lợi ích:** tạo đóng góp nghiên cứu rõ hơn và phù hợp đồ án DSS. **Đánh đổi:** cần thiết kế khảo sát/nhãn độc lập; mô hình sẽ không được coi là tốt hơn nếu ablation không chứng minh lợi ích.

### 10.3. Phương án chi phí cao hơn: hệ gợi ý học từ dữ liệu thật

Khi có tương tác đủ chất lượng, bổ sung retrieval ngữ nghĩa và learning-to-rank/implicit feedback. Tuy nhiên, cần làm trước schema log, exposure, thời gian, ID và thí nghiệm; tăng độ phức tạp mô hình không thể sửa nhãn bị rò rỉ hoặc tọa độ sai.

| Hướng | Có thể giải quyết | Chi phí/giới hạn | Điều kiện nên làm |
|---|---|---|---|
| Alias/taxonomy Việt–Anh | Khác ngôn ngữ type, tên địa phương | Công biên tập nhưng vận hành nhẹ | Có thể làm sớm |
| Embedding đa ngôn ngữ | Đồng nghĩa và truy vấn không trùng từ | Cần tài nguyên inference/index và bộ test retrieval; có thể sai ngữ nghĩa địa danh | TF-IDF đã có benchmark đáng tin |
| Sparse item-CF/implicit model | Khai thác hành vi cộng đồng | Cold-start, exposure bias, cần đủ interaction | Có log thật và dữ liệu thời gian đúng |
| Learning-to-rank | Học phối hợp feature thay vì đặt nhiều hệ số | Dễ học bias từ vị trí hiển thị/nhãn yếu | Có impression và outcome phù hợp |
| LLM hỗ trợ hỏi đáp/giải thích | Hiểu yêu cầu dài, hỏi lại ràng buộc | Chi phí, latency, nguy cơ bịa thông tin POI | Chỉ sinh trên nguồn kiểm chứng và quyết định từ hệ thống |

Các hướng này là đề xuất kỹ thuật, chưa có thử nghiệm trong repository chứng minh hiệu quả hoặc mức tăng metric.

### 10.4. Kiến trúc tối thiểu nên hướng tới

Một cấu trúc hợp lý là:

`raw sources → canonical POI catalog → validated features/model artifacts → một hàm/dịch vụ recommendation → web + evaluator`.

Nên tách các trách nhiệm:

- **Ingestion:** lưu raw fields, nguồn, ID nhà cung cấp và thời điểm.
- **Entity resolution:** ghép POI và bảo tồn bằng chứng, không ghi đè thông tin mơ hồ.
- **Catalog:** một ID chuẩn, schema nội bộ thống nhất, cờ chất lượng.
- **Feature/model build:** fit TF-IDF, behavioral models và trọng số theo version.
- **Inference:** nhận profile, lịch sử/cutoff, filters; trả danh sách và giải thích.
- **Evaluation:** gọi cùng inference với model chỉ fit trên train.
- **Presentation:** hiển thị kết quả và ghi event đúng ID.

Không cần microservices cho quy mô hiện tại. Một package Python có module rõ ràng, artifact theo phiên bản và một dịch vụ nhỏ hoặc cơ chế export thống nhất là đủ. Khi log đa người dùng xuất hiện, bổ sung nơi lưu trữ có schema và truy vấn phù hợp; quyết định hệ quản trị theo tải thực đo.

## 11. Thiết kế đánh giá tốt hơn

### 11.1. Định nghĩa nhiệm vụ trước khi chọn metric

Tách ba benchmark:

1. **Tìm kiếm:** user nhập truy vấn, đánh giá các địa điểm đáp ứng truy vấn đó.
2. **Gợi ý theo ngữ cảnh:** user cung cấp vị trí, thời gian, sở thích; đánh giá độ phù hợp và khả thi.
3. **Gợi ý từ lịch sử:** tại thời điểm t, dùng lịch sử trước t để dự đoán lựa chọn sau t.

Không lấy nội dung đáp án làm query cho nhiệm vụ 3. Với nhiệm vụ 1/2, query phải do người dùng/annotator tạo độc lập, hoặc từ một bộ kịch bản được xác định trước khi xem kết quả mô hình.

### 11.2. Tạo nhãn độc lập theo ngân sách

Một pilot có thể bắt đầu bằng vài chục kịch bản đa dạng trong một vùng, cho người đánh giá xếp mức phù hợp 0–3 trên pool ứng viên trộn từ nhiều baseline. Quy mô chính xác phụ thuộc nguồn lực; đây là đề xuất thiết kế, chưa phải dữ liệu đã thu thập.

Nên bao phủ:

- Người mới và người có lịch sử.
- Truy vấn tiếng Việt có dấu, không dấu, tiếng Anh, lỗi chính tả và truy vấn rỗng.
- Cặp nhu cầu xung đột: gần nhưng rating thấp; nổi tiếng nhưng đông/xa; điểm phù hợp nhưng thiếu giờ mở cửa.
- POI có loại rõ/thiếu loại, nội dung dài/ngắn, ít/nhiều review.
- Bối cảnh gia đình, văn hóa, thiên nhiên, thời gian ít, ngân sách hạn chế.

Người đánh giá không nên biết kết quả đến từ mô hình nào. Có một phần mẫu nhiều người cùng chấm để đo bất đồng. Dành riêng test, không chỉnh hyperparameter theo kết quả test.

### 11.3. Thu thập hành vi thật có ích cho evaluation

Schema event tối thiểu nên có:

`event_id, anonymous_user_id, session_id, poi_id, timestamp, action, request_id, model_version, dataset_version`.

Với impression, cần thêm `rank`, danh sách đã hiển thị, query/profile và ràng buộc lúc đó theo mức dữ liệu người dùng đồng ý cung cấp. Phải phân biệt không chọn một POI vì không thích với việc chưa từng được nhìn thấy.

Không dùng riêng click như sự thật tuyệt đối. Có thể theo dõi save, mở chỉ đường, chọn vào lịch trình, bỏ gợi ý, sửa bộ lọc và phản hồi trực tiếp. Tách dữ liệu demo khỏi dữ liệu thật, có kiểm soát xóa/lưu giữ và cơ chế chống ghi trùng action.

### 11.4. So sánh công bằng

Các mô hình nên được so sánh với cùng thông tin có sẵn và cùng tập hợp lệ:

- Random có ràng buộc và seed rõ.
- Nearby baseline.
- Popularity/quality baseline.
- TF-IDF.
- Content + địa lý + quality bằng tổng trọng số đơn giản.
- Crisp AHP.
- Crisp AHP + TOPSIS.
- Fuzzy aggregation.
- Fuzzy AHP + TOPSIS cuối cùng.
- Behavioral models/hybrid chỉ khi lịch sử thích hợp tồn tại.

Đánh giá thành hai tầng: chất lượng truy xuất candidate trên toàn tập hợp lệ, rồi chất lượng rerank trên cùng candidate pool. Sau đó đánh giá end-to-end đúng pipeline sản phẩm. Điều này giúp xác định cải tiến đến từ retrieval hay từ Fuzzy/TOPSIS.

### 11.5. Metric nên có

| Nhóm | Metric/kiểm tra | Mục đích |
|---|---|---|
| Dữ liệu | Precision ghép thực thể, tỷ lệ tọa độ xác minh, missing theo nguồn | Xác nhận đầu vào đủ đáng tin |
| Retrieval | CandidateRecall@M | Biết đáp án đã bị loại ở tầng nào |
| Ranking | NDCG@K, Recall@K, MRR@K; AP@K khi nhiều positive | Đo phù hợp và thứ tự |
| Ràng buộc | Tỷ lệ vi phạm khoảng cách/thời gian/ngân sách | Đo tính khả thi thực tế |
| Danh sách | Coverage, intra-list diversity, phân bố type/vùng | Đo đa dạng, tránh lệch catalog |
| Ổn định | Top-K overlap/Kendall theo nhiễu weights, data, pool | Kiểm tra độ nhạy của DSS |
| Người dùng | Tỷ lệ chọn/save, thời gian ra quyết định, đánh giá phù hợp | Đo giá trị sử dụng |
| Vận hành | p50/p95 latency, RAM, lỗi, dữ liệu cũ | Xác định khả năng phục vụ |

Mọi metric phải có cỡ mẫu, protocol, số seed nếu có mô phỏng và khoảng bất định phù hợp. Không kết luận tốt hơn chỉ từ một số trung bình nhỉnh hơn trên vài profile.

### 11.6. Các test đáng bổ sung

Ưu tiên test theo rủi ro, không viết test chỉ lặp lại implementation:

- ID giữ nguyên khi thêm/xóa/sắp thứ tự dữ liệu.
- Tọa độ viewport không được tự nâng thành tọa độ thực thể.
- Điểm nằm trong polygon, ngoài polygon, trên biên và trong hole; so sánh engine fallback.
- Parser review ở nhiều locale/hậu tố; missing khác 0.
- AHP reciprocal/positive/finite, CR cao và tính bất biến theo hoán vị.
- TOPSIS một ứng viên, cột hằng, toàn điểm bằng nhau, thay đổi pool.
- AP/NDCG có relevant không được truy hồi; đối chiếu implementation độc lập.
- Inference không nhìn được nhãn test hoặc event tương lai.
- Web filter/selection/save dùng cùng POI/profile.
- HTML/URL fixture không tạo thuộc tính hoặc scheme ngoài ý muốn.

## 12. Mở rộng bài toán và giải pháp

### 12.1. Từ xếp hạng POI sang lịch trình khả thi

Top-K địa điểm tốt riêng lẻ không chắc tạo thành chuyến đi tốt. Nếu mở rộng sang lịch trình, cần mô hình hóa thời gian di chuyển, thời gian tham quan, giờ mở cửa, ngân sách, điểm xuất phát/kết thúc và khả năng bỏ bớt điểm.

Một mô hình khái quát:

\[
\max_{y,x}\sum_i U_i y_i-\lambda\sum_{i,j}t_{ij}x_{ij},
\]

với \(y_i\) chỉ việc chọn POI, \(x_{ij}\) chỉ cạnh di chuyển, \(t_{ij}\) là thời gian di chuyển. Cần thêm ràng buộc dòng tuyến, thời gian đến/giờ mở cửa, tổng ngân sách thời gian và loại chu trình con. Biểu thức trên chỉ minh họa mục tiêu, chưa phải một mô hình tối ưu đầy đủ.

**Giải pháp ít chi phí:** xếp hạng có ràng buộc + greedy chèn điểm vào lịch trình, người dùng sửa được. **Giải pháp phức tạp hơn:** tối ưu tuyến có time windows và lựa chọn POI. Cả hai đều cần dữ liệu thời gian tốt; chỉ thay Haversine bằng tên thuật toán tối ưu chưa đủ.

### 12.2. Đa dạng và khám phá

Danh sách chỉ toàn một loại hoặc các POI gần như trùng nội dung có thể làm giảm giá trị lựa chọn. Có thể thêm rerank đa dạng:

\[
\operatorname{next}(S)=\arg\max_{i\notin S}
\left[\lambda S_i-(1-\lambda)\max_{j\in S}\operatorname{sim}(i,j)\right].
\]

Đây là một lựa chọn thiết kế cần thử nghiệm. Không ép đa dạng trái nhu cầu: nếu người dùng chỉ muốn bảo tàng, tăng số loại bằng cách thêm chợ/nhà thờ không chắc tốt hơn. Có thể đa dạng theo chủ đề, khu vực hoặc thời lượng trong phạm vi sở thích.

### 12.3. Gợi ý cho nhóm

Du lịch nhóm có nhiều người với sở thích xung đột. Có thể thử tổng utility, tối đa hóa mức hài lòng thấp nhất hoặc giới hạn chênh lệch utility giữa thành viên. AHP có thể hữu ích trong việc trình bày đánh đổi, nhưng cần người dùng hiểu và chỉnh được ưu tiên.

Chi phí tăng ở việc thu thập sở thích và tạo quy trình thỏa thuận; chưa cần mô hình học sâu để triển khai một prototype nhóm.

### 12.4. Gợi ý nhận biết độ tin cậy

Thay vì coi mọi dữ liệu như chắc chắn, trả lời đồng thời:

- Vì sao POI phù hợp?
- Thông tin nào đã kiểm tra?
- Thông tin nào thiếu hoặc cũ?
- Nếu người dùng yêu cầu chắc chắn mở cửa/đúng ngân sách, có ứng viên nào đủ dữ liệu không?

Đây là hướng đặc biệt phù hợp với chất lượng dữ liệu hiện tại và với bản chất DSS. Chấp nhận trả ít gợi ý hơn nhưng đáng tin có thể hợp lý hơn lấp đủ Top-K bằng các điểm không rõ.

### 12.5. Giới hạn thiên lệch phổ biến

Review/popularity xuất hiện ở quality, dữ liệu mô phỏng và behavioral score, nên POI nổi tiếng dễ được ưu tiên nhiều lần. Có thể đánh giá riêng head/tail, tạo quota khám phá có kiểm soát và đo tính phù hợp của POI ít review. Không tự đặt mục tiêu phân phối đều toàn catalog nếu điều đó làm giảm nhu cầu thực của người dùng.

## 13. Lộ trình đề xuất và điều kiện hoàn thành

Các mốc dưới đây là thứ tự triển khai, không phải cam kết thời gian hoặc chi phí đã đo.

| Mốc | Kết quả cần tạo | Điều kiện chuyển bước |
|---|---|---|
| A — Khôi phục tính đúng | Sửa leakage/metric, kiểm tra matching và tọa độ, ID chuẩn, manifest | Các số liệu có thể tái lập và truy nguồn; không còn sử dụng input chứa đáp án |
| B — Đồng bộ sản phẩm | Một catalog và scoring contract, filter đúng, save đúng ID, xử lý URL an toàn | Web/evaluator chạy cùng đường suy luận hoặc bản demo được phân biệt rõ |
| C — Chứng minh giá trị | Tập query/nhãn độc lập, baseline, final model, ablation fuzzy/TOPSIS | Có bằng chứng mô hình cuối cải thiện mục tiêu đã chọn hoặc có quyết định đơn giản hóa |
| D — Pilot nhỏ | Log thật có impression/cutoff/version, feedback và đo latency | Chất lượng dữ liệu, tính khả thi và trải nghiệm đạt tiêu chí pilot đã đặt trước |
| E — Mở rộng | Embedding, learned ranking, itinerary hoặc group recommendation | Có dữ liệu và vấn đề cụ thể mà giải pháp đơn giản chưa đáp ứng |

Nếu nguồn lực hạn chế, nên hoàn thành A–C và công bố giới hạn rõ. Một project nhất quán, có phản chứng và benchmark đáng tin sẽ thuyết phục hơn một hệ nhiều lớp chưa biết lớp nào tạo lợi ích.

## 14. Phạm vi kiểm chứng và cách tái hiện

### 14.1. Các kiểm tra đã thực hiện

`PASS` trong bảng chỉ nói thao tác kiểm tra chạy thành công; không tự có nghĩa sản phẩm đã đúng. Khi kiểm tra tái hiện một lỗi, kết quả ghi rõ “xác nhận lỗi”.

| Kiểm tra | Kết quả | Giới hạn |
|---|---|---|
| Đọc mã nguồn/tài liệu được theo dõi trong Git | PASS | Phát hiện theo snapshot `43c4161` |
| Compile 3 script Python, 22 code cell notebook | PASS | Chỉ cú pháp |
| `node --check web/app.js` | PASS | Chỉ cú pháp JS |
| Chạy 21 code cell không xuất dữ liệu, gồm ví dụ và evaluation | PASS | Cell 37 chạy định nghĩa trước, rồi gọi nguyên evaluator trên cùng interaction; display bị tắt để gọn log |
| Chạy chronological trên 120 user mô phỏng | PASS, xác nhận leakage | Không phải benchmark hành vi thật |
| Query content chỉ từ train history | PASS, 0/120 hit | Phép thử chẩn đoán, chưa tối ưu mô hình |
| Phản ví dụ AP/NDCG | PASS, xác nhận lỗi | Đo chính các helper hiện tại |
| Matrix CR cao/không reciprocal | PASS, xác nhận vẫn nhận input | Fixture số học, không phán đoán chuyên gia thật |
| Hoán vị tiêu chí fuzzy | PASS, xác nhận lệch trọng số | Chưa đo tác động thứ hạng trên mọi profile |
| Profile Nha Trang/Đà Nẵng, rỗng, chỉ vị trí | PASS, có gợi ý vượt bán kính ưu tiên | Chưa xác nhận nhu cầu bằng người dùng thực |
| Fixture user đã ghé một POI | PASS, POI đó được gợi ý lại | Chứng minh thiếu chính sách exclude nhất quán |
| Kiểm kê workbook, JSON, ID, tọa độ | PASS | Missing/khớp polygon không đồng nghĩa chất lượng thực địa |
| Đối chiếu nhóm 202 tọa độ trùng với backup 15/09 | PASS, 201 dòng đổi tọa độ; tên/STT khớp | Chưa xác nhận thực địa hoặc xác định thao tác gây thay đổi |
| Chạy exporter ra file tạm | PASS, JSON khớp artifact web | Không ghi đè JSON chính |
| Mô phỏng DOM/Leaflet với JSON thật | PASS; xác nhận filter không chi phối gợi ý và save mặc định không ghi | Không thay thế kiểm thử trình duyệt thật |
| Fixture dấu nháy trong URL ảnh | PASS, xác nhận chèn được thuộc tính HTML | Không thực thi tấn công trong trình duyệt |
| Scraping Google Maps trực tiếp | NOT RUN | Không đo selector live, match precision hay tốc độ thu thập hiện tại |
| Ghi output Excel của cell 39 | NOT RUN | Chủ động giữ nguyên artifact để review sự không đồng bộ |
| Kiểm tra ảnh/link/giờ mở cửa trực tuyến toàn catalog | NOT RUN | Chưa có tỷ lệ URL sống hoặc POI còn hoạt động |
| Browser thật, mobile, accessibility đầy đủ | NOT RUN | Chưa kết luận hiển thị responsive đạt yêu cầu |
| Đánh giá người dùng, A/B test, tải đồng thời | NOT RUN | Chưa có bằng chứng production |

Môi trường thực thi: Python **3.13.15**, pandas **3.0.5**, NumPy **2.5.3**, scikit-learn **1.9.1**, openpyxl **3.1.5**, RapidFuzz **3.14.6**, matplotlib **3.11.2**, Node **24.19.0**. Đây là môi trường kiểm tra hiện tại; requirements của repository chưa đảm bảo người khác cài được đúng các phiên bản này.

### 14.2. Mốc nhận dạng dữ liệu

SHA-256 của các đầu vào quan trọng trong đợt review:

```text
poi_recommendation_system.ipynb
7673c223bb44d6092dbac4f3ae93a782604564a9ea9cda118f150dfa1ffcd191

data/vietnam_destinations_google_maps_browser_hotosm.xlsx
9ac0a4e69d99d3da7d1ffb45cf3100d0385539c3c6317e3faa6124ecf2940744

web/data/pois.json
5dec3a36dffab2ec071438e03acd7ddce12f386a1d1eceb6ecd3b919dc6b5b91
```

Nếu input/code đổi, các số đếm, recommendation, ID và metric trong báo cáo phải được tính lại. Báo cáo không dựa vào số liệu cleanup của lần làm việc trước để xác nhận snapshot hiện tại.

### 14.3. Tái chạy phần tính toán mà không ghi đè output

Tại thư mục gốc repository, chạy đoạn Python sau bằng môi trường đã cài dependencies. Mã này thực thi notebook hiện tại trong bộ nhớ, bỏ cell xuất file và tắt phần display. Nó chỉ phù hợp khi notebook vẫn là phiên bản đã review; phải đọc lại các cell ghi dữ liệu nếu notebook thay đổi.

```python
import contextlib
import io
import json
from pathlib import Path

nb = json.loads(Path("poi_recommendation_system.ipynb").read_text(encoding="utf-8"))
scope = {}
for index, cell in enumerate(nb["cells"]):
    if cell["cell_type"] != "code" or index == 39:
        continue
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile("".join(cell["source"]), f"cell_{index}", "exec"), scope)
        scope["display"] = lambda *args, **kwargs: None

print("Raw:", scope["df_raw"].shape)
print("Clean:", scope["df"].shape)
print(scope["chronological_summary"].to_string(index=False))
print("AP counterexample:", scope["average_precision_at_k"]([1] + [0] * 9, 10))
print("NDCG counterexample:", scope["ndcg_at_k"]([1] + [0] * 9, [1] + [0] * 9, 10))
print(scope["recommend_pois"](scope["user_profile"], top_k=10)[
    ["poi_id", "Tên địa điểm", "location", "distance_km", "final_score"]
].to_string(index=False))
```

Các script chẩn đoán của đợt review nằm trong `.venv/review_audit.py`, `.venv/review_supplement.py`, `.venv/review_web.cjs`; kết quả chi tiết tương ứng ở các file JSON cùng thư mục. Chúng là công cụ tạm cục bộ, không phải dependency của báo cáo hay một test suite được đưa vào Git. Các kết quả quan trọng đã được chép vào báo cáo để tài liệu tự đủ nội dung.

## 15. Cách trình bày project trung thực và thuyết phục

Có thể mô tả sản phẩm hiện tại như sau:

> Where2Go DSS là nguyên mẫu hệ hỗ trợ lựa chọn địa điểm tại Việt Nam, kết hợp truy xuất nội dung, tín hiệu hành vi mô phỏng và ra quyết định đa tiêu chí. Dự án đã triển khai pipeline xử lý dữ liệu và giao diện khám phá bản đồ. Chất lượng gợi ý đối với người dùng thực, lợi ích riêng của Fuzzy AHP/TOPSIS và độ chính xác của dữ liệu làm giàu đang cần được kiểm chứng bằng benchmark độc lập.

Những tuyên bố đã có căn cứ: có implementation, có dữ liệu nhiều nguồn, có bản đồ và gợi ý, có thể chạy lại phần tính toán. Những tuyên bố chưa có căn cứ: độ chính xác gợi ý 100%, chất lượng nguồn đã xác minh toàn bộ, Fuzzy AHP/TOPSIS vượt baseline, web tương đương notebook, hoặc sẵn sàng vận hành quy mô lớn.

Hướng phát triển đáng ưu tiên là biến project thành một hệ thống **có thể giải thích, có ràng buộc rõ và có dữ liệu truy vết được**. Khi ba yếu tố này vững, việc lựa chọn giữ Fuzzy AHP, dùng mô hình đơn giản hơn hay thêm mô hình học từ dữ liệu sẽ dựa trên bằng chứng cụ thể.
