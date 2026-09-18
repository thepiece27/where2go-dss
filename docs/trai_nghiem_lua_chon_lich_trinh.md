# Where2Go — hỗ trợ lựa chọn lịch trình

Bàn giao ngày 18/09/2026. Luồng mới đã triển khai trên FastAPI, SQLite và Leaflet hiện có. Catalog đang dùng: `v2-ae66988a1053d0de`; routing: `1e1d2ec5e5a86240`. Đợt này không crawl/rebuild catalog hay sửa workbook nguồn.

## 1. Trải nghiệm đã triển khai

Người dùng chọn địa phương lập lịch, ngày, khung giờ và điểm xuất phát; thêm nơi muốn ghé; đánh dấu nơi nhất định phải ghé; so sánh lịch rồi chọn và chỉnh lại. Chuyến ô tô trong ngày hỗ trợ Hà Nội/Đà Nẵng, khám phá vẫn toàn quốc.

- Có mẫu sáng 08:00–12:00, chiều 13:00–18:00, cả ngày 08:00–18:00 và giờ tùy chọn.
- Chọn xuất phát bằng ghim bản đồ, vị trí trình duyệt, chi tiết POI hoặc tọa độ trong phần tùy chọn thêm. Tâm thành phố được ghi là điểm mẫu. Nhấp bản đồ chỉ đổi xuất phát khi bật chế độ ghim.
- Mỗi địa điểm có thao tác thêm/bỏ và checkbox “Nhất định phải ghé”. Giới hạn 12 điểm, nhà hàng/cà phê được chọn như các POI khác.
- Có nhóm landmark đã liên kết canonical ID, nhóm gợi ý theo chuyến đi và tìm tên/bí danh không dấu. Đổi bộ lọc khám phá không đổi địa phương lập lịch hay làm mất lựa chọn.
- Thiếu rating không ngăn lựa chọn thủ công. Giờ chưa biết được ghi chú, không giả là mở cửa cả ngày. POI đã đóng cửa bị chặn chọn.
- Các hồ sơ “Thuận đường”, “Ghé nhiều hơn”, “Thư thả” dùng thời lượng thường/ngắn/dài. Trả tối đa ba phương án khác nhau; không nhân bản khi chỉ có một/hai.
- Thẻ phương án có độ phủ điểm đã chọn/bắt buộc, giờ đi/về, lái xe, thời gian còn dư, các điểm chưa xếp cùng lý do, điều chỉnh yêu cầu và thông tin cần kiểm tra.
- “Xem chi tiết” để xem trước; “Chọn lịch này” để dùng. Phương án đổi giờ hoặc thiếu điểm bắt buộc mở hộp xác nhận nêu đúng thay đổi. Hủy xác nhận giữ lịch đã chọn trước đó.
- Timeline có chặng xe, tiếp cận nếu nguồn có thời gian, chờ mở cửa, ghé điểm, ăn/nghỉ tự túc nếu xếp được và quay về. Chỉnh lên/xuống, thời lượng, giờ đi; thêm/bỏ POI. Thứ tự chỉnh tay được giữ khi tính lại; có nút trở về thứ tự do ứng dụng xếp.
- Lịch đã chọn được giữ khi tính lại. Kết quả mới là đề xuất, cần chọn để cập nhật; không tự chấp nhận phương án đổi giờ/bỏ điểm bắt buộc. `AbortController` và số phiên yêu cầu ngăn phản hồi cũ ghi đè.
- Desktop giữ danh sách/bản đồ song song. Mobile có Khám phá–Đã chọn–Lịch trình–Bản đồ; checkbox có nhãn, nút lên/xuống thao tác bằng bàn phím được.
- Nháp theo địa phương: `where2go-trip-v1:<địa phương>`. Địa phương gần nhất: `where2go-trip-city-v1`. Nháp gồm thiết lập, lựa chọn, thứ tự, thời lượng, kết quả và lịch đã chọn; độc lập với `where2go-saved-v2`. Lưu lỗi sẽ hiện thông báo. Không có tài khoản/đồng bộ thiết bị.
- Thông tin dataset chuyển sang `/dataset.html`; không còn AHP, trọng số hay CR trong form lập lịch.

Ảnh có tải lười và thay thế khi lỗi. Bản đồ ban đầu toàn Việt Nam, giữ nền online FOSSGIS và lớp dự phòng từ đợt trước. Tuyến của phương án đang xem dùng màu cam, các điểm trong tuyến được đánh số độc lập với bộ lọc khám phá.

## 2. Tách xếp hạng địa điểm và xếp lịch

| Quyết định | Hàm/chính sách | Ý nghĩa |
|---|---|---|
| Khám phá | `explorable` | Danh tính và vị trí đủ điều kiện hiển thị |
| Người dùng chủ động chọn | `manual_trip_quality` | Khám phá được, đúng địa phương hỗ trợ, không báo đã đóng cửa; không đòi rating/giờ |
| Đề xuất tự động theo dữ liệu | `recommendation_eligible` | Qua điều kiện thủ công và bằng chứng phục vụ hiện hành |
| Landmark | `curated_focus_ids` + điều kiện thủ công + ngày mở cửa | Danh sách biên tập có canonical ID; không suy danh tiếng từ rating ít review |

Fuzzy AHP/TOPSIS tiếp tục dùng bốn tiêu chí `preference_match`, `place_quality`, `drive_time`, `data_confidence`, trọng số thiết kế 0,40/0,30/0,20/0,10. Trọng số không phải kết quả khảo sát người dùng. Chính sách mới có phiên bản `trip-choice-1.0`.

API đề xuất lấy tối đa 30 ứng viên gần vị trí đã chọn/điểm xuất phát và phù hợp chủ đề. Nếu snapshot khớp và có OSRM, xếp hạng bằng lõi Fuzzy AHP/TOPSIS dùng thời gian lái xe thật. Khi routing thiếu, dùng gần theo vị trí và ghi rõ chưa xác nhận thời gian lái; không thay khoảng cách thẳng vào tiêu chí thời gian OSRM. Landmark giữ thứ tự biên tập riêng. Đây chưa phải tối ưu mức đường vòng cho toàn bộ tuyến.

Sau khi người dùng chọn, **điểm TOPSIS không tham gia loại POI hay quyết định thứ tự ghé**. Bài toán xếp lịch ưu tiên số điểm bắt buộc, số điểm người dùng chọn, sau đó thời gian lái và chờ. Vì vậy planner cũ không tìm được lịch không chứng minh AHP/TOPSIS sai.

## 3. Thuật toán lịch nhiều phương án

1. Xác thực tối đa 12 canonical ID không lặp; tập bắt buộc là tập con; thời lượng 5–720 phút nguyên; thứ tự chỉnh tay chứa đúng tập đã chọn. Chỉ nhận khung giờ cùng ngày, độ chính xác phút.
2. Kiểm tra địa phương, danh tính/tọa độ, trạng thái hoạt động và ngày đóng cửa đã biết. Giữ lý do từ chối riêng từng POI; không sửa quan sát nguồn.
3. Dùng điểm tiếp cận ưu tiên hiện hành; nếu thiếu thì dùng vị trí thực thể và ghi rõ chưa xác minh lối vào. Snap tối đa 300 m. Giữ chi phí tiếp cận vào/ra nếu nguồn có. Không giả một điểm tiếp cận chưa xác minh là cổng đã kiểm tra.
4. Tạo **một ma trận Table chung cho các hồ sơ/thời gian**. Kiểm tra đồ thị có đường đi và quay về; có thể đi qua một điểm khác để quay về khi cạnh trực tiếp thiếu. Không biến cạnh null thành 0. Tùy chọn tự bổ sung có thể gọi thêm ma trận riêng cho bước đề xuất trước khi tạo ma trận chuyến đi.
5. Với từng hồ sơ thời lượng, beam search giữ tối đa 64 trạng thái mỗi vòng, mở rộng các thứ tự ghé thay vì chỉ ba điểm đầu. Không áp ngưỡng tối thiểu hai điểm, giới hạn 3/4/5 hoặc quota loại hình. Giữ trạng thái theo tập đã ghé/điểm cuối; ưu tiên điểm bắt buộc và thời gian hoàn thành sớm. Đây là heuristic có giới hạn, không chứng minh tối ưu hay vô nghiệm.
6. Thứ tự chỉnh tay chỉ cho phép các chuỗi con giữ nguyên thứ tự đó. Thời lượng nhập tay giống nhau ở mọi hồ sơ. Quan hệ khu lớn–điểm con/điểm cùng khu chỉ được xếp thành các chặng xe độc lập khi có hai điểm tiếp cận đã xác minh, cách nhau ít nhất 100 m; nếu chưa có, đưa lý do `related_access` để người dùng chọn cách xử lý.
7. Xác nhận ứng viên bằng Route; mô phỏng lại theo đúng chặng Route đó. Không sửa chung ma trận để làm sai phương án khác. Nếu Route làm trễ giờ đóng cửa/về, thử ứng viên khác hoặc bớt điểm; mọi phương án trả ra đều qua mô phỏng cuối. Hình học, chặng và tổng lái thuộc cùng Route.
8. Ăn/nghỉ là tùy chọn. Địa điểm ăn người dùng chọn vào đúng khung bữa ăn được tính vào bữa đó, không chèn thêm bữa trùng. Nếu thiếu địa điểm ăn, có thể chèn 45 phút tự túc tại điểm dừng hoặc 20 phút nghỉ; ghi rõ chưa chọn dịch vụ. Không đủ thời gian thì cảnh báo khối chưa xếp, không xóa toàn bộ lịch.
9. Khi chưa đủ điểm, thử các mẫu sáng/chiều/cả ngày, giữ giờ đi và mở rộng giờ về, rồi thử đi sớm hơn. Giới hạn cùng ngày; phạm vi rộng cuối là 06:00–23:59. Giữ chỗ cho một phương án điều chỉnh nếu giữ được nhiều điểm/điểm bắt buộc hơn. “Thử khung giờ khác” chủ động chạy nhóm này ngay cả khi lịch gốc đã đủ.
10. Khử trùng theo nội dung lịch thực, trả tối đa ba lựa chọn. Phương án thiếu điểm mong muốn vẫn liệt kê cụ thể; thiếu điểm bắt buộc hoặc đổi thời gian đặt `requires_confirmation=true`.

Giới hạn thực thi: tối đa 18 thứ tự Route khác nhau trong một yêu cầu, tối đa tám lần thử ứng viên cho một hồ sơ/cửa sổ. Bước tìm kiếm dừng mở rộng sau ngân sách 12 giây; một lệnh HTTP OSRM đang chạy có timeout 20 giây nên **12 giây không phải SLA phản hồi**. Có trường `search.budget_reached`; kết quả rỗng vẫn có hành động sửa. Không có dịch vụ routing thì không trả timeline/geometry giả.

`reserve_minutes` là phần thời gian còn dư từ lúc về đến mốc giờ về của phương án, không phải khối đệm đã tiêu thụ trong timeline. Đệm khuyến nghị 10% thời gian lái, chặn 15–45 phút; thiếu đệm sinh “Lịch khá sát”. Phương án đề xuất về muộn ghi rõ giờ thực tế và không tự cộng nhiều giờ rảnh của cửa sổ tìm kiếm thành đệm.

## 4. Hợp đồng API

### `POST /api/v2/trip-recommendations`

Nhận `start`, `date`, `location`, `selected_poi_ids`, `interests`, `preferred_categories`. Trả `featured`, `contextual`, lý do/thời lượng/cảnh báo trên mỗi thẻ; cùng `routing_status`, thông tin xếp hạng khi có, phiên bản dữ liệu và chính sách. Không tự thêm vào danh sách người dùng.

### `POST /api/v2/trip-suggestions`

Ví dụ chọn hai bãi biển:

```json
{
  "start": {"latitude": 16.0544, "longitude": 108.2022},
  "date": "2026-09-20",
  "location": "Đà Nẵng",
  "start_time": "08:00",
  "end_time": "18:00",
  "selected_poi_ids": ["osm:relation:19000664", "poi-google:9f6b613e52c6d0f34461666b"],
  "must_visit_poi_ids": ["poi-google:9f6b613e52c6d0f34461666b"],
  "duration_overrides": {},
  "manual_order": null,
  "include_meals": true,
  "include_coffee_break": false,
  "auto_add": false,
  "try_other_windows": false,
  "interests": [],
  "preferred_categories": []
}
```

Để cố định thứ tự ghé theo chỉnh sửa của người dùng, gửi `manual_order` bằng toàn bộ `selected_poi_ids` theo thứ tự mong muốn; đặt `auto_add=false`. Đây không phải khóa giờ hẹn từng điểm. Bật `auto_add` chỉ thêm tối đa ba đề xuất, tổng không quá 12; phản hồi có `auto_added_poi_ids` và mỗi phương án có `auto_added` nêu tên.

| Trường kết quả | Nội dung |
|---|---|
| `status` | `choose_places`, `suggestions`, `adjustment_needed`, `routing_unavailable` |
| `options` | 0–3 phương án đã kiểm tra Route |
| `issues` | ID, tên, mã/lý do: không có POI, sai địa phương, đóng cửa, thiếu tin cậy, snap quá xa, thiếu đường |
| `actions` | Chọn điểm, đổi ngày/khung giờ, sửa lựa chọn, sửa xuất phát, thay điểm, thử lại routing, giữ điểm cho chuyến khác |
| `selected_poi_ids` | Danh sách người dùng gửi, không xóa các điểm chưa xếp |
| `search` | Beam, giới hạn kiểm tra Route, có chạm ngân sách hay không; không tuyên bố tối ưu toàn cục |
| `elapsed_ms` | Thời gian xử lý service, không gồm tải frontend/mạng trình duyệt |

Mỗi phương án có `option_id`, `profile`, `label`, `date`, `location`, `start`, `window`, `scheduled_poi_ids`, `unscheduled`, `missing_must_visit_poi_ids`, `coverage`, `all_must_visits`, `requires_confirmation`, `changes`, `warnings`, `timeline`, `stops`, `legs`, `geometry` và tổng thời gian. Các block timeline có giây chính xác và nhãn `HH:MM` làm tròn lên phút để hiển thị; kiểm tra chồng lấn dùng giây.

`ready`/`provisional` mô tả bằng chứng dữ liệu, **khác** với đáp ứng yêu cầu; phải đọc `coverage`, `changes` và `requires_confirmation`. Endpoint cũ `/api/v2/itineraries`, canonical ID, provenance và dữ liệu nguồn giữ nguyên. Giao diện thông thường không gửi `ahp`; payload có trường ngoài hợp đồng bị từ chối 422.

## 5. Kiểm tra đã chạy

| Kiểm tra | Trạng thái | Bằng chứng/phạm vi |
|---|---|---|
| Toàn bộ pytest | PASS | 107 tests: 74 cũ và 33 trường hợp mới (kể cả tham số hóa) |
| JS syntax | PASS | `app.js`, `map.js`, `dataset.js` |
| Môi trường Python | PASS | `pip check` không phát hiện dependency hỏng |
| Luồng desktop với API/OSRM thật | PASS | Chọn Mỹ Khê/Phạm Văn Đồng, bắt buộc, so sánh, chọn, sửa thời lượng, đổi thứ tự, reload, đổi thành phố, xác nhận/hủy điều chỉnh |
| Mobile, chặn mạng ngoài | PASS | 390×844, chọn điểm/tạo lịch, local basemap Đà Nẵng và 34 địa giới, không tràn ngang |
| Phản hồi cũ | PASS | Probe trình duyệt chủ động trả hai response ngược thứ tự; response cũ không ghi đè. Đây là thử nghiệm có kiểm soát |
| Lỗi ảnh | PASS | URL bị chặn thay bằng “Chưa có ảnh” |
| Khám phá toàn quốc online/offline | PASS | Tile online tải được, 250 hàng đầu và phân trang, marker độc lập, hai bãi biển có ảnh, đổi tỉnh giữ địa phương lập lịch |
| Đánh giá trực tiếp với end user | NOT RUN | Chưa có người dùng độc lập đánh giá độ dễ dùng hay chất lượng lịch |
| Độ đúng thực địa/giao thông trực tiếp | NOT RUN | OSRM không cung cấp traffic live; không xem smoke là xác minh địa điểm/giờ/cổng |

Test backend gồm thiếu rating/giờ; ba điểm đầu đóng nhưng điểm sau vẫn xếp được; nhóm bắt buộc cần đảo thứ tự; 12 điểm cùng loại; một điểm/food-only; thời lượng chỉnh tay; giảm thời lượng theo hồ sơ; khử trùng một/hai phương án; thiếu điểm bắt buộc/đổi giờ; bữa ăn không trùng; đồ thị một chiều; Table/Route khác nhau; snapshot sai; Route lỗi; snap quá xa; POI khác tỉnh; quan hệ khu lớn–điểm con; catalog không bị sửa; ID phương án xác định lại ổn định.

Artifacts: `artifacts/trip-choices/smoke.json`, `desktop-timeline.png`, `mobile-timeline.png`, `mobile-map-offline.png`; smoke khám phá ở `artifacts/enrichment-web/`. Artifacts là đầu ra sinh lại, không phải tài liệu nguồn.

## 6. Đối chiếu trước/sau

Chạy `scripts/evaluate_trip_choices.py` với cùng catalog và OSRM trên bảy kịch bản có chủ đích: một Phạm Văn Đồng, hai bãi biển, khung giờ Đà Nẵng quá ngắn, một nhà thờ Hà Nội, nhóm văn hóa Hà Nội, bảo tàng buổi chiều, chuyến chỉ có nhà hàng. Cả hai nhận cùng xuất phát/ngày/giờ/danh sách bắt buộc; planner cũ có thể thêm các POI khác theo hành vi cũ, còn mới mặc định không tự thêm. Do khác mục tiêu sản phẩm, đây không phải thí nghiệm cô lập chất lượng xếp hạng.

| Chỉ số trong bảy kịch bản | Planner cũ | Luồng mới |
|---|---:|---:|
| Có lịch trả về | 2/7 | 7/7 |
| Đủ điểm bắt buộc trong khung gốc | 2/7 | 5/7 |
| Đủ điểm bắt buộc khi cho phương án đổi giờ | Không có luồng so sánh | 7/7 |
| Có lịch hoặc hành động tiếp theo | Không đo theo hợp đồng mới | 7/7 |
| Trung vị thời gian service | 20,5 ms | 488,3 ms |
| Lớn nhất, luồng mới | — | 1.377,3 ms |

Thời gian planner cũ thấp một phần do nhiều trường hợp bị loại sớm; cache OSRM có thể nóng và các kiểm tra chạy trên máy phát triển. Không suy số liệu này thành SLA hay tỷ lệ thành công toàn hệ thống. Hai phương án cần đổi giờ có cờ xác nhận. Báo cáo máy đọc được cùng thay đổi giờ từng phương án nằm tại [`data/reports/v2/trip_choices_evaluation.json`](../data/reports/v2/trip_choices_evaluation.json).

## 7. Chạy và bàn giao

```powershell
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\evaluate_trip_choices.py
.venv\Scripts\python.exe scripts\smoke_web.py
.venv\Scripts\python.exe scripts\smoke_explore_v2.py
```

OSRM cần chạy tại URL cấu hình (`127.0.0.1:5001` mặc định), cùng SHA256 PBF với catalog. Cập nhật Python cần restart uvicorn; cập nhật frontend cần tải lại trang. `smoke_web.py` là entry point tương thích gọi `smoke_trip_choices.py`.

| Thành phần | File |
|---|---|
| Hợp đồng và validation | `where2go/v2/trip_models.py` |
| Đề xuất/xếp lịch/mô phỏng | `where2go/v2/trips.py` |
| Điều kiện dữ liệu | `where2go/v2/quality.py` |
| Service/API | `where2go/v2/service.py`, `where2go/api.py` |
| Form/chọn/so sánh/timeline/lưu nháp | `web/index.html`, `web/app.js`, `web/styles.css` |
| Bản đồ và điểm xuất phát | `web/map.js` |
| Thông tin dữ liệu riêng | `web/dataset.html`, `web/dataset.js` |
| Hồi quy backend/API | `tests/test_trip_suggestions.py` |
| Smoke và đối chiếu | `scripts/smoke_trip_choices.py`, `scripts/smoke_explore_v2.py`, `scripts/evaluate_trip_choices.py` |

## 8. Giới hạn và bước tiếp theo

- Chưa có khóa giờ hẹn từng điểm, chuyến nhiều ngày, phương tiện ngoài ô tô, tài khoản hay đồng bộ thiết bị; đúng phạm vi bản đầu.
- Luôn đưa bước tiếp theo cho yêu cầu hợp lệ khi service/catalog sẵn sàng. Lỗi cấu trúc yêu cầu vẫn là 422; không cam kết lịch khả thi cho mọi lựa chọn hoặc khi hạ tầng không sẵn sàng.
- Gợi ý ăn tự túc chưa bảo đảm có dịch vụ tại điểm dừng. Độ tin cậy giờ/đường vào phụ thuộc bằng chứng nguồn; cần kiểm tra trước khi đi.
- Nhóm đề xuất dùng shortlist theo địa lý/chủ đề và ranking theo đường từ xuất phát. Đánh giá đường vòng theo toàn tuyến, nhãn giờ đẹp để tham quan và giao thông thực chưa được triển khai.
- Cần thử nghiệm với người dùng: tỷ lệ hoàn thành bốn bước, thời gian chọn lịch, tỷ lệ chấp nhận điều chỉnh, đánh giá chất lượng lịch. “Có kết quả” không phải thước đo chất lượng chuyến đi.
