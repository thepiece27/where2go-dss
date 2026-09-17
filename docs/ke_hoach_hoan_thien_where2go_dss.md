# Prompt triển khai Where2Go DSS: dữ liệu trọng tâm và lịch trình trong ngày

**Căn cứ:** [Báo cáo review dự án](bao_cao_review_du_an_where2go_dss.md)  
**Trọng tâm dữ liệu:** Hà Nội và Đà Nẵng mới, bao gồm địa bàn Quảng Nam trước sáp nhập theo phạm vi đã thống nhất  
**Mốc dự kiến:** 7 ngày làm việc; nghiệm thu theo kết quả thực tế

## 1. Nhiệm vụ và cách thực hiện

Hãy cải tiến dự án Where2Go DSS hiện có thành hệ hỗ trợ lựa chọn POI và gợi ý lịch trình tham quan trong ngày. Đọc báo cáo review, kiểm tra lại mã nguồn và dữ liệu trong checkout hiện tại, sau đó thực hiện các hạng mục dưới đây theo thứ tự phụ thuộc.

- Tái sử dụng phần còn phù hợp của dự án; sửa các lỗi có bằng chứng trong báo cáo trước khi dùng kết quả để khẳng định chất lượng.
- Giữ Fuzzy AHP + TOPSIS làm lớp xếp hạng POI, bổ sung lớp lập lịch trình riêng.
- Ưu tiên độ đúng và độ đầy đủ của dữ liệu ở hai thành phố trọng tâm, khả năng chạy đầu cuối và bằng chứng kiểm thử.
- Giữ nguyên dữ liệu nguồn, backup và thay đổi sẵn có của người dùng. Mọi dữ liệu làm sạch phải có đầu ra riêng, truy vết được.
- Thực hiện và kiểm chứng từng phần; báo rõ phần hoàn thành, phần chưa chạy và trở ngại thực tế. Mốc 7 ngày không thay thế điều kiện nghiệm thu.

Tài liệu này mô tả công việc cần triển khai, không xác nhận các tính năng hoặc dữ liệu đã hoàn thành.

## 2. Phạm vi sản phẩm

Người dùng chọn điểm xuất phát trên bản đồ, ngày, giờ bắt đầu/kết thúc, sở thích và loại hình muốn ghé. Hệ thống đề xuất 2–5 POI, thứ tự tham quan, giờ đến/rời, thời gian di chuyển và chặng quay về điểm xuất phát.

### Phạm vi địa lý và dữ liệu

- **Hà Nội:** tập trung thu thập, chuẩn hóa và kiểm chứng dữ liệu phục vụ lịch trình trong ngày.
- **Đà Nẵng mới:** xử lý cả địa bàn Đà Nẵng cũ và Quảng Nam cũ. Giữ tên địa phương nguồn, ánh xạ sang đơn vị hiện hành và lưu phiên bản/nguồn địa giới. Không chỉ đổi chuỗi tên hoặc giới hạn dữ liệu ở trung tâm Đà Nẵng cũ.
- Hai thành phố cần được kiểm kê theo cụm tham quan và loại hình, để phát hiện khu vực còn thiếu dữ liệu. Một lịch trình chỉ ghép các điểm đi được trong khung giờ; cùng thành phố không đồng nghĩa gần nhau.
- Các địa phương khác giữ catalog nền và được phép tạo lịch trình nếu đủ điều kiện. Ngoài hai thành phố trọng tâm không phải là lý do tự động từ chối.
- Tối thiểu 25 POI được đối soát tại mỗi thành phố là **mẫu nghiệm thu dữ liệu**, không phải giới hạn thu thập. Tiếp tục nhập và kiểm tra toàn bộ POI phù hợp từ nguồn đã chọn trong hai thành phố; ghi lại các khoảng trống chưa xử lý.

### Giới hạn phiên bản đầu

- Một ngày, ô tô, múi giờ `Asia/Ho_Chi_Minh`, xuất phát và quay về cùng vị trí.
- Kiểm tra giờ mở cửa và ngân sách thời gian bằng heuristic chèn điểm; chưa giải bài toán tối ưu tuyến toàn cục.
- Chưa triển khai nhiều ngày, nhiều phương tiện, ngân sách tiền, gợi ý cho nhóm hoặc học hành vi người dùng thực.
- Cho phép POI chưa biết giờ mở cửa nếu cảnh báo rõ; không gọi lịch trình đó là đã xác minh khả thi hoàn toàn.

## 3. Kiến trúc và luồng xử lý thống nhất

Dùng một lõi Python cho API, notebook và chương trình đánh giá. Web tiếp tục sử dụng giao diện/bản đồ hiện có và gọi API; bỏ đường xếp hạng độc lập bằng JavaScript khi đã chuyển đổi.

Luồng xử lý bắt buộc:

1. Nhập nguồn và audit → catalog chuẩn + manifest + hàng kiểm duyệt.
2. Nhận yêu cầu → kiểm tra đầu vào → lọc cứng → lấy danh sách ứng viên.
3. OSRM → ma trận thời gian đường bộ và thông tin khả năng tiếp cận.
4. Cố định pool hợp lệ → tính tiêu chí → Fuzzy AHP + TOPSIS.
5. Chèn POI vào lịch trình → kiểm tra toàn bộ thời gian và chặng quay về.
6. API trả kết quả → web hiển thị lịch trình, tuyến và cảnh báo.

Báo cáo độ phủ được sinh từ catalog chuẩn. Notebook gọi lõi chung để minh họa công thức và đánh giá, không duy trì một bản thuật toán sản phẩm khác.

## 4. Dữ liệu: thu thập, làm sạch và kiểm chứng

### 4.1. Nguồn và khả năng tái lập

- Giữ workbook/backup hiện có làm nguồn legacy bất biến; không cập nhật trực tiếp.
- Nhập dữ liệu mở từ bản chụp OSM Việt Nam của [Geofabrik](https://download.geofabrik.de/asia/vietnam.html). Lưu URL, ngày dữ liệu, ngày tải và SHA-256; giữ OSM object ID. Dùng cùng snapshot để dựng OSRM.
- Ưu tiên lọc, đối soát và làm giàu POI ở Hà Nội và Đà Nẵng mới. Bổ sung giờ mở cửa, điểm vào tham quan và loại hình từ website của địa điểm/cơ quan quản lý hoặc nguồn được phép sử dụng.
- Công cụ nhập/làm giàu phải chạy lại được, có log lỗi và tiếp tục phần chưa hoàn thành; không tạo bản ghi trùng khi chạy lại.
- Không tiếp tục crawl hàng loạt Google Maps. Tách các trường legacy chưa rõ nguồn hoặc quyền sử dụng khỏi catalog công bố mặc định; không suy nguồn chỉ từ tiền tố `maps_*`.
- Ghi nguồn/giấy phép ở manifest và attribution trên sản phẩm theo [OSM](https://www.openstreetmap.org/copyright); tham chiếu [điều khoản Google Maps](https://maps.google.com/help/terms_maps/) khi rà soát dữ liệu legacy.

### 4.2. Catalog chuẩn

Dùng SQLite làm catalog phục vụ Python; xuất CSV phục vụ audit và JSON cho manifest. Export là sản phẩm của cùng pipeline, không có quy tắc làm sạch riêng.

| Nhóm | Thông tin tối thiểu |
|---|---|
| Định danh | `poi_id`, tên gốc/chuẩn hóa, các ID nguồn liên kết |
| Không gian | Tọa độ, bằng chứng tọa độ, địa phương gốc/hiện hành, nguồn và phiên bản địa giới |
| Nội dung | Mô tả nếu có, loại hình gốc/chuẩn hóa, bằng chứng phân loại |
| Thời gian | Giờ gốc, các khoảng mở cửa, trạng thái giờ, thời lượng tham quan và nguồn/giả định |
| Kiểm duyệt | `data_status`, lý do, các trường đã kiểm tra, thời điểm và người/công cụ kiểm tra |
| Nguồn | Provenance từng trường: nguồn, URL/ID bằng chứng, ngày thu thập, ngày xác minh nếu có, giấy phép |

- Dùng `legacy:<STT>` cho ID legacy hợp lệ và `osm:<type>:<id>` cho POI OSM mới. Kiểm tra khóa nguồn trước khi cấp ID; không dùng chỉ số dòng sau lọc.
- Khi ghép nhiều nguồn thành một POI, giữ ID canonical đã cấp và bảng ánh xạ ID nguồn. Không đổi ID theo thứ tự import.
- `data_status`: `usable` là đủ điều kiện dữ liệu cơ bản; `needs_review` là còn mơ hồ; `excluded` là không dùng trong gợi ý. Hai trạng thái sau vẫn được giữ trong audit.
- `usable` không đồng nghĩa chắc chắn có tuyến hoặc đang mở cửa; các điều kiện này được kiểm tra theo request.
- Thông tin chưa biết để trống và có trạng thái tương ứng. Ngày import không được ghi thành ngày xác minh; kiểm tra tự động không được ghi thành kiểm duyệt thủ công.

### 4.3. Kiểm tra và sửa dữ liệu

- Chạy audit toàn catalog; dành công sức sửa và bổ sung cho hai thành phố trọng tâm. Báo cáo số lượng trước/sau xử lý theo thành phố, cụm tham quan, loại hình và nguồn.
- Kiểm tra lại cụm 202 POI chung tọa độ nêu trong báo cáo. Đưa bản ghi đáng ngờ vào hàng kiểm duyệt; chỉ khôi phục từ backup khi có bằng chứng đối chiếu, không chép đè cả bảng.
- Không coi tọa độ viewport `@lat,lng` là tọa độ POI. Không coi trùng tọa độ hoặc nằm ngoài polygon là đủ bằng chứng để xóa địa điểm.
- Đối sánh thực thể dựa trên ID nguồn hoặc tổ hợp tên, địa phương và bằng chứng tọa độ. Tọa độ legacy đang nghi sai không được dùng làm bằng chứng ghép tự động.
- Chuẩn hóa taxonomy và địa danh cũ, xử lý POI trùng giữa nguồn. Trường hợp không rõ được đưa vào hàng kiểm duyệt với lý do cụ thể.
- Với công viên/khu tham quan rộng, ưu tiên tọa độ lối vào có bằng chứng. Ghi khoảng cách OSRM snap tới đường; kiểm tra các trường hợp snap quá xa, không coi tâm polygon là lối vào.
- Không tạo rating/review hoặc mô tả trải nghiệm giả để lấp ô trống.

### 4.4. Giờ mở cửa, thời lượng và độ đầy đủ

- `hours_status` gồm `known` và `unknown`. Chỉ dùng `known` khi giải được lịch cho ngày yêu cầu; giữ nguyên nguồn và chuỗi gốc. Giờ phân tích được chưa đồng nghĩa đã được xác minh thực địa.
- Không parse được, thiếu lịch theo ngày hoặc không giải được ngoại lệ ngày lễ thì dùng `unknown` cho request và cảnh báo.
- Thời lượng tham quan mặc định theo loại hình được lưu ở cấu hình, ghi là `estimated` và hiển thị cho người dùng. Không trình bày như số đo thực tế.
- Đối soát tối thiểu 25 POI mỗi thành phố: danh tính, tọa độ/điểm tiếp cận, loại hình, bằng chứng nguồn, khả năng định tuyến; ghi rõ giờ biết/chưa biết và thời lượng có nguồn/ước lượng. Đà Nẵng phải có mẫu từ cả Đà Nẵng cũ và Quảng Nam cũ.
- Lập hàng ưu tiên bổ sung theo trường thiếu và cụm chưa đủ ứng viên để lên lịch. Không dừng thu thập chỉ vì đủ mẫu 25 POI.
- Công bố riêng số trường đã có, đã phân tích, đã đối soát và còn thiếu; không dùng tỷ lệ ô có dữ liệu thay cho độ chính xác.

## 5. Fuzzy AHP + TOPSIS và tập ứng viên

### 5.1. Tiêu chí thống nhất

| Tiêu chí | Ý nghĩa | Chiều ưu tiên |
|---|---|---|
| `preference_match` | Mức phù hợp nội dung và sở thích của request | Cao hơn tốt hơn |
| `drive_time` | Thời gian đường bộ từ điểm xuất phát, lấy từ OSRM | Thấp hơn tốt hơn |
| `data_confidence` | Điểm quy tắc theo bằng chứng và trạng thái dữ liệu | Cao hơn tốt hơn |

Tên và thứ tự tiêu chí phải thống nhất trong API, ma trận AHP, code và báo cáo. Công thức tạo `preference_match` và `data_confidence` phải có cấu hình/phiên bản và được giải thích; `data_confidence` không phải xác suất dữ liệu đúng hoặc chất lượng trải nghiệm.

Không đưa hành vi mô phỏng vào điểm sản phẩm. Dữ liệu mô phỏng chỉ dùng cho fixture và diagnostic có nhãn rõ ràng.

### 5.2. Trọng số và toán học

- Nhận ba phán đoán cặp, mặc định bằng 1. Gọi đây là mặc định bằng nhau; không gán danh nghĩa chuyên gia.
- Kiểm tra ma trận 3×3: hữu hạn, dương, đường chéo 1, reciprocal và `CR <= 0.1`. Đầu vào sai trả lỗi có chỉ dẫn sửa.
- Fuzzification ngoài đường chéo dùng `(a/gamma, a, a*gamma)`, `gamma > 1` lưu trong cấu hình; đường chéo là `(1,1,1)`. Các cặp đối xứng phải thỏa reciprocal và cùng quy tắc với đánh giá bằng nhau.
- Tính trọng số bằng geometric mean, chuẩn hóa số mờ, giải mờ và chuẩn hóa tổng bằng 1; ghi rõ công thức/biến thể sử dụng. Test hoán vị tiêu chí và ánh xạ ngược phải cho cùng kết quả.
- TOPSIS chuẩn hóa vector trên pool cố định. Với `drive_time`, chọn ideal best là min và worst là max; không vừa đảo giá trị vừa áp dụng lại quy tắc cost.
- Xử lý cột hằng, cột toàn 0 và các ứng viên bằng điểm mà không sinh NaN; tie-break bằng ID. Điểm TOPSIS là điểm tương đối trong pool.
- Không mặc định biến thể fuzzy tốt hơn crisp AHP. Ablation phải kiểm tra cả trường hợp trọng số/thứ hạng không thay đổi.

### 5.3. Tạo ứng viên

Lọc cứng theo yêu cầu địa lý, loại hình, trạng thái dữ liệu và tọa độ. Sau đó hợp nhất ứng viên theo nội dung và vị trí, loại trùng và giới hạn pool bằng cấu hình.

Haversine chỉ dùng để lấy danh sách ngắn. Sau khi có ma trận OSRM, loại ứng viên không thể đi từ điểm xuất phát và quay về; cố định pool còn lại trước TOPSIS. Không thay đổi pool theo số điểm đang chèn hoặc số lượng kết quả muốn hiển thị.

Ghi số lượng và lý do loại ở từng bước để phân biệt lỗi retrieval, dữ liệu, routing và xếp hạng.

## 6. Lịch trình và hợp đồng API

### 6.1. API tối thiểu

- `GET /api/pois`: catalog và bộ lọc, dùng ID canonical.
- `GET /api/coverage`: độ phủ và khoảng trống dữ liệu.
- `GET /api/health`: trạng thái catalog/OSRM cho kiểm tra vận hành.
- `POST /api/itineraries`: lập lịch trình bằng lõi Python chung.

Ví dụ request:

```json
{
  "start": {"latitude": 16.0544, "longitude": 108.2022},
  "date": "2026-09-20",
  "start_time": "08:00",
  "end_time": "18:00",
  "interests": ["văn hóa", "lịch sử"],
  "categories": ["museum", "attraction"],
  "pairwise_preferences": {
    "preference_over_drive_time": 1,
    "preference_over_data_confidence": 1,
    "drive_time_over_data_confidence": 1
  }
}
```

Tọa độ, ngày, khung giờ và phán đoán không hợp lệ trả HTTP 422; không gộp vào lỗi thiếu dữ liệu. Phản hồi lịch trình chứa trạng thái, lý do, phiên bản dataset/model/routing, điểm dừng và điểm tiêu chí, giờ đến/bắt đầu tham quan/rời, thời gian chờ/di chuyển/tham quan, chặng quay về, tuyến bản đồ, cảnh báo và lý do bỏ ứng viên.

| Trạng thái | Điều kiện |
|---|---|
| `ready` | Có 2–5 điểm thỏa ràng buộc đã kiểm tra; lịch mở cửa của các điểm giải được cho ngày yêu cầu |
| `provisional` | Có 2–5 điểm nhưng ít nhất một điểm chưa xác định được giờ mở cửa/ngoại lệ của ngày yêu cầu |
| `insufficient_data` | Không tạo được ít nhất 2 điểm trong điều kiện yêu cầu; nêu rõ thiếu POI, không có tuyến phù hợp hoặc không đủ thời gian |
| `routing_unavailable` | Dịch vụ routing lỗi/không truy cập được hoặc không trả dữ liệu hợp lệ cần thiết |

`ready` chỉ có nghĩa khả thi theo dữ liệu và mô hình thời gian đang dùng. Cả `ready` và `provisional` vẫn hiển thị thời lượng ước lượng và giới hạn thời gian đường bộ.

### 6.2. Thuật toán chèn điểm

1. Khởi tạo tuyến rỗng từ điểm xuất phát quay về điểm xuất phát.
2. Duyệt POI theo điểm TOPSIS giảm dần, bằng điểm thì theo `poi_id`.
3. Với mỗi POI, thử mọi vị trí chèn và mô phỏng lại toàn tuyến. Chỉ giữ vị trí không vi phạm điều kiện dưới đây.
4. Chọn vị trí hợp lệ làm tăng thời gian di chuyển ít nhất; nếu hòa, chọn thời điểm về sớm nhất rồi vị trí chèn nhỏ nhất.
5. Sau mỗi lần chèn thành công, duyệt lại các điểm chưa chọn; dừng khi đủ 5 điểm hoặc một lượt không thêm được điểm nào. Nếu cuối cùng ít hơn 2 điểm, trả trạng thái không tạo được lịch trình.

Điều kiện mô phỏng:

- Tính thời gian theo từng chặng có hướng, thời lượng tham quan và chặng quay về; không giả định thời gian đi bằng thời gian về.
- Nếu đến trước giờ mở cửa, cho phép chờ và tính thời gian chờ vào tổng lịch trình. Toàn lượt tham quan phải nằm trong một khoảng mở cửa phù hợp.
- Giờ chưa biết được phép vào lịch trình kèm `provisional`; không tự gán thành mở 24 giờ.
- Không chèn POI khi một chặng cần dùng có duration `null`, hoặc giờ quay về vượt `end_time`. Một cặp POI không có tuyến không làm loại mọi tuyến khác còn hợp lệ.
- Không lặp POI, không tự kéo dài khung giờ và không buộc chọn POI hạng cao nhất nếu không khả thi.

### 6.3. OSRM

Tự chạy OSRM theo [hướng dẫn dự án](https://github.com/Project-OSRM/osrm-backend); pin phiên bản container và ghi phiên bản profile/mạng đường. Dùng pipeline MLD `extract → partition → customize → routed`.

Dùng [Table](https://project-osrm.org/docs/v5.24.0/api/#table-service) cho duration/distance và Route cho hình học tuyến. Kiểm tra đơn vị giây/mét, thứ tự lon/lat, lỗi dịch vụ và dữ liệu snap. Cache phải gắn với tọa độ, profile và phiên bản mạng đường.

Không thay duration thiếu bằng Haversine hoặc dùng dữ liệu mock làm route thật. Nếu chưa có môi trường OSRM chạy được, tiếp tục phần code và test với fixture có nhãn; ghi rõ nghiệm thu routing thực tế còn chưa đạt.

## 7. Web và đánh giá

### Giao diện

- Form điểm xuất phát, ngày, khung giờ, sở thích/category và ba phán đoán AHP trong phần tùy chỉnh ưu tiên.
- Timeline và bản đồ hiển thị giờ đến/rời, thời gian chờ/di chuyển/tham quan, đường về và cảnh báo dễ hiểu.
- Bộ lọc được gửi nhất quán tới API cho danh sách và lịch trình. Save lưu đúng ID đang mở, kể cả trạng thái ban đầu và sau lọc.
- Render dữ liệu qua DOM API, kiểm tra URL ảnh để tránh chèn HTML ngoài ý muốn.
- Hiển thị độ phủ hai thành phố trọng tâm và giải thích thiếu dữ liệu ở khu vực khác; không gây hiểu nhầm catalog nền đã được kiểm chứng.

### Kiểm thử bắt buộc

- **Dữ liệu:** ID qua các lần import/export, ghép nguồn không trùng, tọa độ viewport/cụm nghi vấn, alias Quảng Nam cũ, provenance và giờ thiếu.
- **Toán học:** ma trận AHP sai/CR cao, reciprocal, hoán vị tiêu chí, TOPSIS cost/cột hằng/toàn 0/bằng điểm.
- **Lập lịch:** chờ mở cửa, nghỉ giữa ngày, vượt giờ đóng cửa, giờ chưa biết, route một chiều, chặng quay về không có tuyến, thiếu thời gian, giới hạn 2–5 điểm.
- **API/web:** lỗi đầu vào, bốn trạng thái kết quả, cùng catalog/model, bộ lọc, save và URL ảnh bất thường.
- Fixture không cần mạng dùng cho regression; kiểm thử OSRM thực được ghi riêng. Ca `unknown` dùng fixture nếu dữ liệu demo đã đầy đủ, không cố ý làm thiếu dữ liệu thật để có cảnh báo.

### Đánh giá chất lượng

- Evaluator gọi đúng lõi sản phẩm. Query không được sinh từ POI đáp án; nhãn test không được tham gia tạo query, trọng số hoặc chọn tham số.
- Với diagnostic có tương tác thời gian, loại dữ liệu tương lai khỏi train. Không dùng tương tác mô phỏng làm bằng chứng hành vi thực.
- Sửa AP@K theo tổng relevant của tập đánh giá và IDCG@K từ toàn tập được gán nhãn, không chỉ các kết quả đã tìm được.
- So sánh nearby, weighted sum đều, crisp AHP + TOPSIS và Fuzzy AHP + TOPSIS trên cùng pool; dùng cùng planner nếu so chất lượng lịch trình.
- Kịch bản và nhãn phải được tạo độc lập với đầu ra. Ghi người/cách tạo nhãn và tránh cho người chấm biết tên mô hình. Nếu chưa có nhãn độc lập, bàn giao test/case study và ghi đánh giá người dùng là chưa thực hiện.
- Đo riêng chất lượng dữ liệu, khả năng truy xuất ứng viên, xếp hạng và tuân thủ ràng buộc; không gom thành một con số “accuracy”.

## 8. Thứ tự thực hiện và nghiệm thu

| Giai đoạn dự kiến | Công việc chính | Đầu ra kiểm chứng |
|---|---|---|
| Ngày 1 | Đọc repo/review, kiểm tra trạng thái hiện tại, audit đầu vào, khởi động tải snapshot và kiểm tra OSRM | Baseline, hợp đồng dữ liệu, kết quả preflight |
| Ngày 2–3 | Import, chuẩn hóa/ghép nguồn, làm sạch hai thành phố, đối soát mẫu và bổ sung trường thiếu | Catalog, manifest, hàng kiểm duyệt, báo cáo độ phủ và bằng chứng |
| Ngày 4 | Lõi tiêu chí/AHP/TOPSIS dùng chung, sửa evaluator | Kiểm thử toán học, schema và metric |
| Ngày 5 | Routing, planner và API | Test lịch trình, trạng thái lỗi, tuyến thực nếu môi trường sẵn sàng |
| Ngày 6 | Tích hợp web và sửa lỗi P1 liên quan | Kiểm thử đầu cuối và demo hai thành phố |
| Ngày 7 | Đánh giá, sửa lỗi còn lại, đóng băng kết quả, hướng dẫn chạy và báo cáo | Bộ bàn giao tái lập được |

Điều kiện nghiệm thu:

- Pipeline nguồn → catalog → API/web/evaluator thống nhất ID, dữ liệu và thuật toán; có lệnh tái tạo, dependency/version cố định và manifest.
- Mỗi thành phố có tối thiểu 25 POI được đối soát với bằng chứng; dữ liệu nhập không bị giới hạn ở mẫu này. Báo cáo chỉ rõ coverage và các trường/khu vực còn thiếu.
- Mỗi thành phố có ít nhất hai lịch trình demo 2–5 POI dùng route thực, có chặng về và thời gian/cảnh báo đúng. Hai demo Đà Nẵng bao phủ một cụm thuộc Đà Nẵng cũ và một cụm thuộc Quảng Nam cũ; không bắt buộc ghép hai cụm xa nhau trong cùng ngày.
- Các lỗi P0 liên quan dữ liệu, ID, leakage, metric và các lỗi P1 của lõi/web thuộc phạm vi này có kết quả xử lý. Giữ bảng đối chiếu mã lỗi trong báo cáo review với trạng thái thực tế.
- Bàn giao mã nguồn, cấu hình, pipeline dữ liệu, kiểm thử, README, kịch bản demo và báo cáo tiếng Việt về phương pháp, kết quả, nguồn và giới hạn.
- Ghi `PASS`, `FAIL`, `NOT RUN` dựa trên bằng chứng. Không gọi phần routing, đối soát dữ liệu hoặc đánh giá người dùng là hoàn thành nếu mới có code/fixture.

Khi có trở ngại, ghi nguyên nhân và phần bị ảnh hưởng, tiếp tục các công việc độc lập. Không mở rộng sang các tính năng ngoài phạm vi để thay thế những điều kiện nghiệm thu chưa đạt.
