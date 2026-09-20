# Demo Đà Nẵng: 2 kịch bản chính và 1 kịch bản dự phòng đã chạy thật

**Nên trình diễn K1 và K2; dùng K3 nếu còn thời gian hoặc cần giải thích ô Loại hình ưu tiên.** Mỗi bước chỉ thay một nhóm đầu vào, rồi đối chiếu POI xuất hiện, biến mất và đổi thứ hạng. Đây là các tình huống được chọn sau thử nghiệm để minh họa khả năng phản hồi theo yêu cầu; không phải mẫu ngẫu nhiên để suy ra độ chính xác toàn hệ thống.

**Bằng chứng phiên 21/09/2026:** 113 lượt gọi API sàng lọc, **111 cấu hình khác nhau**, 796 cặp so sánh chỉ khác một trường đầu vào. Sau đó chạy **11 bước trên Chromium** ở ba kịch bản và gửi lại bước cuối mỗi kịch bản thêm một lần: cả ba giữ nguyên thứ tự. Tổng cộng **127 lượt gợi ý**, không tính gọi health. Các bước trên web khớp request dự kiến, danh sách API và danh sách hiển thị; không có lỗi JavaScript. Kết quả của 113 lượt sàng lọc có 112 lượt có POI, một lượt rỗng; tọa độ của mọi POI trả về đều được kiểm tra thuộc vùng `danang` theo đa giác dự án.

**Phiên bản:** catalog `v2-c3ad315d02c5356a`; chính sách `poi-recommendation-1.1`; routing `1e1d2ec5e5a86240`; Chromium `151.0.7922.34`. Không chỉnh thuật toán, trọng số, dữ liệu hay phản hồi API trong phiên chọn kịch bản này.

## 1. Chọn kịch bản theo thời lượng

| Kịch bản | Nên dùng | Thay đổi mạnh nhất quan sát được | Điều chứng minh được |
| --- | --- | --- | --- |
| **K1 — Sở thích và mức ưu tiên** | Chính, khoảng 4–5 phút | Thiên nhiên → lịch sử/văn hóa: **thay cả 10 POI**; Cân bằng → Đi gần: thay 3 POI, khoảng cách trung bình 4,64 → 2,65 km | Sở thích làm đổi nội dung gợi ý; mức ưu tiên làm đổi đánh đổi giữa nội dung và khoảng cách |
| **K2 — Điểm xuất phát và bán kính** | Chính, khoảng 4–5 phút | Trung tâm → gần Mỹ Khê: **6 POI mới**; 3 km → 1 km: từ 10 xuống **4 kết quả** | Vị trí làm đổi tập ứng viên; bán kính là điều kiện giới hạn thật |
| **K3 — Từ khóa và loại hình** | Dự phòng, khoảng 2 phút | Giữ từ khóa biển, thêm Bãi biển: **4 POI mới**; bỏ lựa chọn thì trở lại đúng danh sách ban đầu | Từ khóa và ưu tiên loại hình có tác dụng khác nhau; kết quả không bị giữ nhầm từ yêu cầu trước |

Thời lượng trên là ước lượng để tập trình bày, không phải thời gian đã đo với người thuyết trình.

Nếu chỉ có 5 phút: làm **K1-A → K1-B**, sau đó **K2-A → K2-B → K2-C**. Nếu đủ 8–10 phút, làm thêm K1-C/K1-D và K2-D. K2-D minh họa giới hạn phạm vi, không dùng để khẳng định tất cả kết quả đều hợp sở thích.

## 2. Chuẩn bị để kết quả tái lập

1. Chạy API theo [hướng dẫn chạy](huong_dan_chay.md), mở **http://127.0.0.1:8000/**. Kiểm tra `http://127.0.0.1:8000/api/health`: catalog/routing phải sẵn sàng và đúng phiên bản trên. Riêng K2 cần đường đi OSRM như lần thử; nếu web chuyển sang đường chim bay, phải ghi nhận lại kết quả thay vì đọc số phút trong tài liệu.
2. Dùng một phiên trình duyệt mới để không mang theo nháp cũ; danh sách chuyến đi phải có **0 địa điểm**. Không thêm địa điểm vào chuyến trong ba kịch bản này, vì POI đã chọn bị loại khỏi lần gợi ý sau.
3. Đặt **Địa phương = Đà Nẵng**; **Phạm vi = Đà Nẵng – Hội An – Cù Lao Chàm**; **Nhóm địa điểm = Tham quan và ngoài trời**; **Ngày dự định đi = 21/09/2026**. Giữ ngày cố định: đổi ngày có thể đổi điều kiện mở cửa.
4. Mở **Loại hình và điểm xuất phát**. Nhập số bằng dấu chấm thập phân. Không bấm GPS trong lúc demo đã chuẩn bị: GPS sẽ làm tọa độ khác và kết quả khác.
5. Các nút **Điều bạn quan tâm** là **chọn nhiều**: bấm lại nút đang chọn để bỏ. Muốn chuyển sang sở thích khác phải bỏ sở thích cũ. Ô **Nhu cầu của bạn** bổ sung vào các chủ đề, không thay thế chúng.
6. Ô **Loại hình ưu tiên** cũng chọn nhiều. Khi cần để trống, giữ **Ctrl** và bấm từng dòng đang được chọn để bỏ chọn. Khi thiết lập ban đầu, bảo đảm không còn loại hình từ phiên trước.
7. Sau mỗi lần sửa, danh sách cũ biến mất và hiện “Nhu cầu đã thay đổi. Bấm Nhận gợi ý để cập nhật.” Đây là hành vi đúng. Bấm **Nhận gợi ý**, chờ nút hoạt động lại rồi mới đối chiếu kết quả.

Phạm vi mặc định có cả Hội An; nhãn “Đà Nẵng” một mình không bảo đảm giới hạn Đà Nẵng cũ. Trong các cấu hình cụ thể dưới đây, toàn bộ tọa độ kết quả đã được kiểm tra thuộc `danang`. Không mở bán kính lên 30 km rồi vẫn đọc kết luận địa lý của bộ này.

## 3. K1 — Từ muốn ngắm cảnh sang muốn tìm hiểu văn hóa

**Bối cảnh nói với người xem:** “Tôi đang ở trung tâm Đà Nẵng. Lúc đầu tôi muốn đi ngắm cảnh, sau đó đổi sang tìm hiểu lịch sử và văn hóa. Khi có ít thời gian hơn, tôi muốn ưu tiên các địa điểm gần.”

### K1-A. Thiết lập yêu cầu ban đầu

| Ô trên web | Giá trị |
| --- | --- |
| Ngày / địa phương / phạm vi / nhóm | Theo mục 2 |
| Bán kính | **15 km** |
| Bạn ưu tiên điều gì? | **Cân bằng các yếu tố** |
| Điều bạn quan tâm | Chỉ **thiên nhiên** |
| Nhu cầu của bạn | Để trống |
| Loại hình ưu tiên | Không chọn gì |
| Vĩ độ / Kinh độ | **16.0544 / 108.2022** |

Bấm **Nhận gợi ý**. Web hiển thị **10 gợi ý từ 78 ứng viên trong 87 POI đáp ứng điều kiện**. Ba kết quả đầu:

1. **Bãi Biển Thiên Đường** — 2,17 km.
2. **Đường hoa Bạch Đằng** — 2,46 km.
3. **Công viên Nam Dương** — 1,79 km.

Khoảng cách ở K1 là **đường chim bay**. Theo nhãn catalog, danh sách gồm 8 công viên và 2 bãi biển. Tên và nhãn được giữ đúng như hệ thống trả về; không tự coi nhãn là một lần xác minh thực địa mới.

Mở **Vì sao được gợi ý?** ở thẻ đầu. Điểm **Khớp sở thích** xấp xỉ **0,78**. Có thể nói:

> “Với cùng vị trí xuất phát và bán kính, tôi đang khai báo nhu cầu thiên nhiên. Hệ thống đưa các điểm có nội dung hoặc nhóm trải nghiệm liên quan lên đầu, đồng thời cân nhắc khoảng cách và chất lượng tham khảo.”

### K1-B. Chỉ đổi Điều bạn quan tâm

**Thao tác:** bấm **thiên nhiên** để bỏ; bật **lịch sử** và **văn hóa**; giữ nguyên tất cả ô khác; bấm **Nhận gợi ý**.

Kết quả: **10 gợi ý từ 75 ứng viên trong 87 POI đáp ứng điều kiện**. Ba kết quả đầu trở thành:

1. **Bảo tàng Mỹ thuật Đà Nẵng** — 2,51 km.
2. **Bảo tàng Đà Nẵng** — 3,26 km.
3. **Bảo tàng Điêu khắc Chăm Đà Nẵng** — 2,32 km.

**Không có POI nào trùng giữa Top-10 của K1-A và K1-B.** Đây là đoạn rõ nhất để chứng minh sở thích làm thay đổi danh sách. Cùng 87 POI đủ điều kiện không có nghĩa tập xếp hạng giống nhau: bước lấy ứng viên theo độ liên quan cũng thay đổi, nên số ứng viên là 78 → 75.

**Giải thích:** các nhóm bảo tàng/di tích có thẻ lịch sử và văn hóa; khi đổi sở thích, điểm phù hợp nội dung được tính lại. Không đổi vị trí, ngày, bán kính hay mức ưu tiên nên không gán thay đổi này cho khoảng cách hoặc thời tiết.

Lời nói gợi ý:

> “Tôi chỉ đổi sở thích từ thiên nhiên sang lịch sử và văn hóa. Các điều kiện còn lại giữ nguyên. Ba vị trí đầu giờ là các bảo tàng, và trong lần chạy này toàn bộ Top-10 đã thay đổi. Hệ thống đang xếp lại theo yêu cầu mới, chứ không giữ một danh sách cố định.”

**Không nói:** “Hệ thống hiểu mọi ý định tự nhiên” hoặc “mọi kết quả đều là bảo tàng”. Danh sách đầy đủ còn chợ, điểm tham quan và di tích; đây là nhu cầu văn hóa rộng, không phải bộ lọc chỉ bảo tàng.

### K1-C. Giữ sở thích, chỉ đổi mức ưu tiên sang Đi gần

**Thao tác:** giữ cả **lịch sử** và **văn hóa**; đổi **Bạn ưu tiên điều gì?** từ **Cân bằng các yếu tố** sang **Đi gần**; bấm **Nhận gợi ý**.

Ba kết quả đầu:

1. **Bảo tàng Điêu khắc Chăm Đà Nẵng** — từ hạng **3 lên 1**, vẫn cách 2,32 km.
2. **Bảo tàng Mỹ thuật Đà Nẵng** — từ hạng **1 xuống 2**, vẫn cách 2,51 km.
3. **Bảo tàng Đà Nẵng** — từ hạng **2 xuống 3**, vẫn cách 3,26 km.

**Có 3 POI mới vào Top-10**, giữ lại 7. Ba điểm rời Top-10 là Động Vân Thông (8,64 km), Bảo tàng Phật giáo (8,29 km), Dong Dinh Museum (9,39 km). Ba điểm vào là Chợ Cồn Hùng Vương (1,97 km), Chợ Kỳ Đồng (2,35 km), NICKY KIDS - Khu Vui Chơi Dành Cho Bé (2,16 km).

Khoảng cách trung bình của **10 kết quả hiển thị** giảm **4,64 → 2,65 km**. Đây là trung bình khoảng cách từ điểm xuất phát đến từng POI, **không phải độ dài một lịch trình**. Số đủ điều kiện và ứng viên giữ nguyên **87 / 75**; đây là phép thử trọng số, không phải thu hẹp bán kính.

| Tiêu chí | Cân bằng | Đi gần |
| --- | ---: | ---: |
| Khớp sở thích | 40% | 30% |
| Chất lượng tham khảo | 30% | 20% |
| Chi phí di chuyển | 20% | 40% |
| Bằng chứng dữ liệu | 10% | 10% |

**Giải thích chính xác:** đổi mẫu ưu tiên làm đổi cả bộ trọng số. Mức ảnh hưởng của khoảng cách tăng; điểm sở thích, chất lượng và vị trí của riêng Bảo tàng Chăm không đổi. Thẻ bảo tàng này vẫn có điểm khớp khoảng **0,72**, chất lượng khoảng **0,84**, khoảng cách **2,32 km**, bằng chứng **0,50**. Thứ hạng đổi do cách tổng hợp các tiêu chí.

Lời nói gợi ý:

> “Tôi vẫn muốn trải nghiệm lịch sử và văn hóa, nhưng giờ muốn đi gần hơn. Bảo tàng Chăm chuyển từ vị trí thứ ba lên đầu. Cả danh sách cũng gần hơn xét theo khoảng cách trung bình trong lần thử này. Đây là sự đánh đổi giữa mức phù hợp, chất lượng và chi phí di chuyển.”

**Giới hạn cần nhận đúng:** việc NICKY KIDS vào danh sách cho thấy thẻ nội dung hoặc phân loại rộng có thể kéo vào kết quả chưa thật sát ý định văn hóa của người dùng. Không giới thiệu nó là một di tích hay tự bịa giá trị lịch sử để giải thích. Bước này chứng minh tác động của trọng số, không chứng minh mọi POI mới có chất lượng ngữ nghĩa tốt hơn.

### K1-D. Kiểm chứng lại nhu cầu tâm linh

**Thao tác:** giữ **Đi gần**; bỏ **lịch sử** và **văn hóa**; bật duy nhất **tâm linh**; bấm **Nhận gợi ý**.

Web có **10 gợi ý từ 77 ứng viên trong 93 POI đủ điều kiện**. Sáu kết quả đầu đều thuộc nhóm nơi thờ tự:

1. Chùa Thuận Thành.
2. Thánh thất Cao Đài.
3. Tượng Phật Quan Âm - Chùa Mỹ Khê.
4. Chùa Trung Lương.
5. Chùa Giác Hoàng Viên.
6. Chùa Linh Ứng Sơn Trà.

So với K1-C, có **8 POI mới**, giữ 2. Web cũng thông báo đã xét thêm đền/chùa theo sở thích. Tập đủ điều kiện tăng **87 → 93** vì yêu cầu tâm linh cho phép 6 nơi thờ tự đi qua bộ lọc nhóm mặc định trong điều kiện này.

Lời nói gợi ý:

> “Khi chuyển sang tâm linh, hệ thống đưa các nơi thờ tự lên sáu vị trí đầu. Chọn sở thích này vừa ảnh hưởng việc lấy ứng viên, vừa ảnh hưởng xếp hạng; điều kiện vị trí, ngày và bán kính vẫn được giữ.”

Bốn vị trí cuối là hai công viên và hai chợ, có điểm khớp tâm linh **0**. Chúng **không phải bốn điểm tâm linh khác**. Nếu mục tiêu là “chỉ được trả nơi thờ tự”, phiên bản hiện tại chưa đáp ứng yêu cầu đó bằng nút sở thích: đây vẫn là ưu tiên mềm. Có thể kết thúc phần demo ở việc quan sát nhóm dẫn đầu, nhưng không khẳng định cả 10 đều đáp ứng tâm linh.

## 4. K2 — Giữ nhu cầu biển, đổi điểm xuất phát và phạm vi

**Bối cảnh:** “Tôi muốn ra khu vực biển. Ban đầu tôi xuất phát từ trung tâm, sau đó đổi sang điểm lưu trú gần Mỹ Khê. Cuối cùng tôi muốn giới hạn việc đi lại quanh chỗ ở.”

### K2-A. Thiết lập lại các ô trước khi bắt đầu

| Ô trên web | Giá trị |
| --- | --- |
| Ngày / địa phương / phạm vi / nhóm | Theo mục 2 |
| Bán kính | **5 km** |
| Bạn ưu tiên điều gì? | **Đi gần** |
| Điều bạn quan tâm | **Bỏ hết các chủ đề** |
| Nhu cầu của bạn | Gõ đúng **biển** |
| Loại hình ưu tiên | Không chọn gì |
| Vĩ độ / Kinh độ | **16.0544 / 108.2022** |

Bấm **Nhận gợi ý**. Có **10 kết quả từ 46 ứng viên / 46 POI đủ điều kiện**. Ba kết quả đầu: **Bãi Biển Thiên Đường**, **Biển Thanh Bình**, **Bãi Tắm Biển Mỹ Khê**.

Trong K2, **bán kính vẫn đo theo đường chim bay**, còn tiêu chí di chuyển để xếp hạng là **phút lái xe OSRM**. Cả bốn bước được kiểm chứng cùng cách đo này. Thời gian là ước tính từ dữ liệu đường đi, không có giao thông trực tiếp và không phải thời gian đã chạy xe thực tế.

### K2-B. Chỉ thay tọa độ điểm xuất phát

**Thao tác:** đổi **Vĩ độ = 16.0630**, **Kinh độ = 108.2450**. Đây là một cặp tọa độ xuất phát gần Mỹ Khê; không phải vị trí mới của POI. Giữ từ khóa biển, Đi gần và bán kính 5 km. Bấm **Nhận gợi ý**.

Kết quả: **10 gợi ý từ 55 ứng viên / 55 POI đủ điều kiện**. Ba vị trí đầu:

1. **Bãi biển Mỹ Khê** — 1,42 km theo tọa độ.
2. **Bãi Tắm Biển Mỹ Khê** — 0,76 km.
3. **Công viên biển Mân Thái** — 2,88 km.

**6 POI mới**, giữ 4 từ bước trước. Khoảng cách đường chim bay trung bình của Top-10 giảm **3,07 → 1,74 km**. Thời gian OSRM trung bình từ điểm xuất phát đến từng POI giảm **5,01 → 3,59 phút**; không cộng các giá trị này để gọi là một lịch trình tối ưu.

Lời nói gợi ý:

> “Tôi chưa đổi sở thích. Tôi chỉ chuyển điểm xuất phát sang gần Mỹ Khê. Khi tâm tìm kiếm thay đổi, những nơi nằm trong vòng 5 km và chi phí đi đến từng nơi cũng thay đổi. Danh sách vì thế chuyển về nhóm điểm gần khu vực tôi vừa chọn.”

Không nói rằng chỉ khoảng cách thay đổi: **tập đủ điều kiện cũng đổi 46 → 55**. Hai giá trị vĩ độ/kinh độ là một thay đổi về điểm xuất phát; không tách riêng chúng thành hai nguyên nhân độc lập.

### K2-C. Giữ nguyên tọa độ, chỉ thu bán kính từ 5 xuống 3 km

**Thao tác:** chỉ đổi **Bán kính = 3**; bấm **Nhận gợi ý**.

Web còn **39 ứng viên / 39 POI đủ điều kiện**, vẫn hiển thị 10 kết quả. **Biển Thanh Bình rời danh sách** vì cách điểm xuất phát mới **4,53 km**, vượt giới hạn 3 km. **Bãi tắm Mân Thái**, cách **2,93 km**, vào Top-10. Giữ 9/10 POI từ K2-B; hai vị trí đầu đổi chỗ thành Bãi Tắm Biển Mỹ Khê rồi Bãi biển Mỹ Khê.

Lời nói gợi ý:

> “Đây là tác động của giới hạn khoảng cách. Biển Thanh Bình nằm ngoài vòng 3 km nên bị loại. Bãi tắm Mân Thái vẫn trong phạm vi và được đưa vào phần kết quả hiển thị. Tôi chưa đổi sở thích hay mức ưu tiên.”

Thu bán kính có thể làm thứ hạng các POI còn lại đổi vì tập ứng viên và phép chuẩn hóa xếp hạng thay đổi. Không nói rằng dữ liệu chất lượng của các điểm tự thay đổi.

### K2-D. Minh họa giới hạn chặt: chỉ 1 km

**Thao tác:** chỉ đổi **Bán kính = 1**; bấm **Nhận gợi ý**.

Kết quả đúng **4 POI**, không đủ 10:

| Hạng | POI | Đường chim bay | Lái xe theo OSRM |
| ---: | --- | ---: | ---: |
| 1 | Công viên Biển Đông | 0,82 km | 1,37 phút |
| 2 | Bãi Tắm Biển Mỹ Khê | 0,76 km | 2,29 phút |
| 3 | Công viên Bãi biển Mỹ Khê | 0,16 km | 3,57 phút |
| 4 | Chợ Phước Mỹ | 0,49 km | 1,70 phút |

**Bãi biển Mỹ Khê** ở K2-C cách 1,42 km nên không còn ở đây; **Bãi Tắm Biển Mỹ Khê** cách 0,76 km vẫn còn. Đây là hai **bản ghi POI có ID/tọa độ khác nhau** trong catalog. Không khẳng định chúng là hai bãi biển vật lý độc lập chỉ từ tên gần giống; khả năng trùng hoặc chồng lấn thực thể vẫn cần đối soát dữ liệu.

Lời nói gợi ý:

> “Khi giới hạn còn 1 km, dữ liệu hiện có chỉ cho bốn địa điểm đủ điều kiện. Hệ thống giữ đúng bán kính, không tự mở rộng ra ngoài để điền đủ mười kết quả. Danh sách ngắn hơn là kết quả của điều kiện tôi vừa siết.”

**Tách hai đánh giá:** giới hạn tọa độ được thực hiện đúng, nhưng mức hợp sở thích chưa hoàn hảo. Chợ Phước Mỹ có điểm khớp biển **0**; không mô tả nó là bãi biển hoặc lấy lý do “đa dạng hóa” để biện minh, vì thuật toán không có quy tắc đa dạng hóa như vậy. Sở thích là ưu tiên mềm, trong khi bán kính là điều kiện bắt buộc.

Công viên Biển Đông từ hạng 5 ở K2-B lên hạng 1 ở K2-D dù tiêu chí riêng không đổi: điểm khớp khoảng 0,069; chất lượng 0,919; 82,2 giây lái xe; bằng chứng 0,50. Điều đổi là tập so sánh. Không so hai điểm TOPSIS 0,709 và 0,849 để nói địa điểm đã “tốt lên”.

## 5. K3 dự phòng — Giữ từ khóa, thêm rồi bỏ loại hình ưu tiên

**Dùng khi cần giải thích hai ô Nhu cầu và Loại hình.** Điểm mạnh là thao tác rất ít và quay lại được kết quả ban đầu. Điểm yếu là catalog có nhiều tên gần giống ở khu Mỹ Khê; đây không phải kịch bản để chứng minh chất lượng khử trùng lặp.

### K3-A. Tìm bằng từ khóa

Thiết lập: ngày/địa phương/phạm vi/nhóm như mục 2; tâm **16.0544 / 108.2022**; **15 km**; mẫu **Hợp sở thích**; bỏ hết chủ đề; ô Nhu cầu nhập **biển**; Loại hình để trống.

Bấm Nhận gợi ý. Ba kết quả đầu: **Biển Thanh Bình**, **Bãi biển Mỹ Khê**, **Công viên biển Mân Thái**. Có 10 kết quả từ **77 ứng viên / 87 POI đủ điều kiện**. Bãi Biển Thiên Đường đang hạng **4**, điểm khớp khoảng **0,093**.

### K3-B. Chỉ thêm Loại hình ưu tiên = Bãi biển

Giữ nguyên từ khóa và mọi ô khác; chọn dòng **Bãi biển**, rồi bấm Nhận gợi ý.

Ba kết quả đầu: **Bãi Biển Thiên Đường**, **Biển Thanh Bình**, **Bãi Tắm Biển Mỹ Khê**. **4 POI mới**, giữ 6. Nhãn của 10 bản ghi trả về đều là `beach`; đây là nhãn catalog, không phải xác nhận thực địa vừa thực hiện. Số ứng viên đổi **77 → 76**, đủ điều kiện vẫn **87**.

Mở Vì sao được gợi ý? ở Bãi Biển Thiên Đường: hạng **4 → 1**, điểm khớp **0,093 → 0,893**, trong khi vị trí và chất lượng tham khảo của chính POI không đổi. Lý do hiện **“Thuộc loại hình bạn ưu tiên.”**

Lời nói gợi ý:

> “Từ khóa biển giúp so khớp nội dung. Khi tôi chọn thêm loại hình Bãi biển, hệ thống nhận một tín hiệu cấu trúc rõ hơn. Nó làm tăng mức phù hợp cho những bản ghi thuộc loại hình đó, nên có điểm đổi hạng và có điểm khác vào Top-10.”

Không nói ô Loại hình là bộ lọc độc quyền: thiết kế hiện tại vẫn là **ưu tiên**. Cũng không nói điểm 0,893 là 89,3% xác suất người dùng thích địa điểm; đó là điểm tương thích nội dung của công thức hiện có.

### K3-C. Bỏ lựa chọn loại hình

Giữ Ctrl và bấm dòng **Bãi biển** đang chọn để bỏ, vẫn giữ từ khóa biển; bấm Nhận gợi ý. Toàn bộ ID và thứ tự Top-10 trở lại đúng K3-A. Việc quay về cùng kết quả khi đầu vào giống nhau là tính lặp lại mong muốn, không phải bằng chứng lỗi cache.

## 6. Cách giải thích hệ thống, đủ chính xác để trả lời câu hỏi

| Câu hỏi có thể gặp | Câu trả lời phù hợp với bằng chứng |
| --- | --- |
| Vì sao sửa ô mà danh sách tạm trống? | Kết quả cũ bị xóa để tránh dùng nhầm. Bấm Nhận gợi ý để tính lại với cấu hình mới. |
| Vì sao không phải lần nào cũng thay cả 10 POI? | Có thay đổi chỉ ảnh hưởng thứ tự, có thay đổi tác động tập ứng viên. Cần so ID lẫn hạng, không chỉ nhìn tên thẻ đầu. |
| Đi gần có nghĩa điểm gần nhất luôn đứng đầu? | Không. Khoảng cách có trọng số lớn hơn nhưng sở thích, chất lượng và bằng chứng vẫn tham gia. K1 dùng km theo tọa độ; K2 dùng thời gian đường đi. |
| Vì sao 0,16 km lại đi ô tô lâu hơn 0,82 km? | Bán kính đo đường chim bay; OSRM tính trên mạng đường và điểm tiếp cận. Hai phép đo có thể cho thứ tự khác nhau. Không tự suy ra một tuyến đường cụ thể nếu chưa xem tuyến. |
| Điểm TOPSIS là phần trăm chính xác? | Không. Đó là điểm tương đối trong tập ứng viên của lượt tính; không phải xác suất hài lòng và không nên so chéo lượt như thước chất lượng tuyệt đối. |
| Chọn tâm linh nhưng còn công viên/chợ? | Thuật toán dùng sở thích như ưu tiên mềm và vẫn trả thêm phương án theo tiêu chí khác. Các POI cuối có điểm khớp 0 là hạn chế, không có chứng cứ để gọi chúng là điểm tâm linh. |
| Vì sao cùng Mỹ Khê có nhiều tên? | Catalog có nhiều bản ghi/điểm tọa độ. Chưa thể bảo đảm chúng đại diện cho những nơi vật lý độc lập; không cộng chúng thành số thắng cảnh riêng đã được xác minh. |
| K20 được nhóm như bảo tàng, NICKY KIDS được gợi ý văn hóa có đúng không? | Đây là phân loại/thẻ nội dung hiện có. Bộ thử cho thấy chúng tác động đến gợi ý; tính chính xác ngữ nghĩa của các bản ghi còn cần rà soát. Không tạo câu chuyện văn hóa không có bằng chứng. |
| Vì sao ảnh trống? | Có POI chưa có ảnh hoặc ảnh nguồn tải lỗi; web có ô dự phòng. Ảnh không nằm trong bốn tiêu chí xếp hạng này. Không nói ảnh trống là do nơi đó chưa mở cửa. |
| Có hiểu “không thích biển” không? | Chưa đáng tin cậy: thử trực tiếp cho cùng Top-10 như nhập biển. Không trình bày ô nhập là hệ thống hiểu đầy đủ câu phủ định. |
| Đã chứng minh hệ thống tốt với mọi người chưa? | Chưa. Đây là bộ demo có chọn lọc và kiểm tra kỹ thuật. Chưa có chấm mức hài lòng độc lập để suy ra độ chính xác ngoài thực tế. |

Không cần đọc toàn bộ bảng giới hạn khi mở đầu. Chỉ trình bày đúng phạm vi các thao tác đang chứng minh; nếu được hỏi, trả lời bằng dữ liệu tương ứng. Không dùng lời giải thích trái thuật toán để làm một kết quả chưa phù hợp nghe thành đúng.

## 7. Vì sao chọn ba kịch bản này sau khi thử nhiều

Tiêu chí sàng lọc: thay đổi đầu vào dễ thao tác; quy được tác động về một trường/nhóm đầu vào; đổi POI hoặc thứ hạng đủ rõ; tất cả tọa độ ở Đà Nẵng; phép đo chi phí nhất quán trong cặp so sánh; tái lập trên UI thật. Danh sách ứng viên được giữ trong bằng chứng kể cả các ca không phù hợp để trình diễn.

| Nhóm đã thử | Số lượt | Nhận xét dùng để chọn |
| --- | ---: | --- |
| Không khai báo sở thích | 1 | Dùng làm đối chứng; không đủ để chứng minh cá nhân hóa |
| 10 nhóm chủ đề × 4 mẫu ưu tiên | 40 | Tìm được chuyển thiên nhiên → lịch sử/văn hóa thay toàn bộ Top-10; đổi mức ưu tiên có thay đổi rõ về hạng và khoảng cách |
| 6 cấu hình nhập từ khóa × 4 mẫu ưu tiên | 24 | Từ khóa biển dùng được cho K2/K3; ca phủ định biển được giữ như ca chưa đạt |
| 6 loại hình × 2 mẫu ưu tiên | 12 | Phân biệt ưu tiên loại hình với chủ đề; tránh tuyên bố loại hình là bộ lọc cứng |
| 3 tọa độ × 5 bán kính × 2 nhu cầu | 30 | Chọn cặp trung tâm/gần Mỹ Khê 5 km vì thay 6/10 POI và cả hai dùng thời gian OSRM |
| Thêm loại hình Bãi biển vào hai nhu cầu | 2 | Thêm Bãi biển vào từ khóa biển thay 4/10 POI; phù hợp làm dự phòng |
| Đổi ngày sang 22/09 và 27/09 | 2 | Có thêm Ho Chi Minh Museum so với ngày 21/09; không chọn làm kịch bản chính vì mục tiêu ưu tiên thay sở thích/vị trí và cần giải thích lịch mở cửa theo nguồn |
| Tâm linh 1 km và vùng núi 1 km | 2 | Một ca chỉ có công viên dù muốn tâm linh; một ca rỗng. Không dùng để quảng bá độ phù hợp, vẫn giữ để đánh giá giới hạn |
| **Tổng** | **113** | **111 request khác nhau; hai cấu hình lặp do giao nhau giữa ma trận chủ đề/tọa độ** |

796 là số cặp so sánh được tính từ các lượt trên, **không phải 796 lượt test độc lập**. 127 lượt gợi ý không tương đương 127 người tham gia. Các thang “đẹp”, “đúng ý” ở đây là nhận xét chọn tình huống minh họa, không phải Precision/NDCG hay tỷ lệ hài lòng được đo.

## 8. Bằng chứng, chạy lại và các tài liệu liên quan

- [Bảng 113 lượt sàng lọc](../data/reports/demo_danang_selection/screening.csv): request, phân bố loại hình, số kết quả, thứ tự ID/tên.
- [Kết quả được chọn và so sánh từng bước](../data/reports/demo_danang_selection/selected_results.json): có tiêu chí, lý do, khoảng cách, phiên bản và kiểm tra UI.
- [Toàn bộ phản hồi sàng lọc cục bộ](../artifacts/demo_selection_20260921/screening.json), [bản ghi trình duyệt](../artifacts/demo_selection_20260921/browser_report.json), [796 cặp so sánh](../artifacts/demo_selection_20260921/comparisons.csv).
- Ảnh chụp màn hình các bước: [K1-A](../artifacts/demo_selection_20260921/browser/K1_so_thich_va_uu_tien/01.png), [K1-B](../artifacts/demo_selection_20260921/browser/K1_so_thich_va_uu_tien/02.png), [K1-C](../artifacts/demo_selection_20260921/browser/K1_so_thich_va_uu_tien/03.png), [K1-D](../artifacts/demo_selection_20260921/browser/K1_so_thich_va_uu_tien/04.png); [K2-A](../artifacts/demo_selection_20260921/browser/K2_vi_tri_va_ban_kinh/01.png), [K2-B](../artifacts/demo_selection_20260921/browser/K2_vi_tri_va_ban_kinh/02.png), [K2-C](../artifacts/demo_selection_20260921/browser/K2_vi_tri_va_ban_kinh/03.png), [K2-D](../artifacts/demo_selection_20260921/browser/K2_vi_tri_va_ban_kinh/04.png); [K3-A](../artifacts/demo_selection_20260921/browser/K3_nhu_cau_va_loai_hinh/01.png), [K3-B](../artifacts/demo_selection_20260921/browser/K3_nhu_cau_va_loai_hinh/02.png).
- Bối cảnh các lần trước: [29 ca demo lịch sử](demo_da_nang_thuc_nghiem.md) và [kiểm thử sau sửa sở thích](kiem_thu_cap_nhat_so_thich.md). Phiên sửa trước đã ghi nhận 134 test Python PASS; phiên viết tài liệu này kiểm chứng bằng API/trình duyệt, không chạy lại rồi gán mới con số đó.

Ảnh chụp có thể bắt đúng lúc ảnh từ nguồn ngoài đang tải; bản ghi không dùng ảnh làm tiêu chuẩn PASS cho thuật toán. Tệp trong `artifacts/` là bằng chứng cục bộ và bị Git bỏ qua; CSV/JSON rút gọn ở `data/reports/demo_danang_selection/` giữ kết quả để đọc lại khi không có artifact.

Chạy lại từ thư mục gốc, khi API đã hoạt động:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\select_demo_danang.py sweep
.venv\Scripts\python.exe -X utf8 scripts\select_demo_danang.py browser
.venv\Scripts\python.exe -X utf8 scripts\export_demo_danang_selection.py
```

Lệnh đầu lấy dữ liệu thật hiện đang phục vụ; lệnh sau so UI với lần sàng lọc vừa chạy. Nếu đổi catalog, routing hoặc ngày demo, phải xem lại số liệu trước khi dùng lời thoại. Kế hoạch replay nằm trong [demo_danang_selected_plan.json](../scripts/demo_danang_selected_plan.json).

<!-- GENERATED_RESULTS_START -->

## 9. Phụ lục: toàn bộ POI hiển thị, không lược các kết quả yếu

Các bảng dưới được xuất từ phản hồi đã đối chiếu với UI. Tên giống hoặc gần nhau vẫn được giữ; số thay đổi ở phần chính so theo **ID**, không so chuỗi tên. Ký hiệu ‘—’ là không còn kết quả ở hạng đó.

### K1: thứ tự đầy đủ

| Hạng | K1-A | K1-B | K1-C | K1-D |
| ---: | --- | --- | --- | --- |
| 1 | Bãi Biển Thiên Đường | Bảo tàng Mỹ thuật Đà Nẵng | Bảo tàng Điêu khắc Chăm Đà Nẵng | Chùa Thuận Thành |
| 2 | Đường hoa Bạch Đằng | Bảo tàng Đà Nẵng | Bảo tàng Mỹ thuật Đà Nẵng | Thánh thất Cao Đài |
| 3 | Công viên Nam Dương | Bảo tàng Điêu khắc Chăm Đà Nẵng | Bảo tàng Đà Nẵng | Tượng Phật Quan Âm - Chùa Mỹ Khê |
| 4 | Công viên 29 tháng 3 | Khu Căn cứ Cách mạng K20 | Khu Căn cứ Cách mạng K20 | Chùa Trung Lương |
| 5 | Quảng trường Bạch Đằng | Động Vân Thông | Chợ Cồn | Chùa Giác Hoàng Viên |
| 6 | Công viên APEC | Bảo tàng Phật giáo | Lang Bich hoa Da Nang | Chùa Linh Ứng Sơn Trà |
| 7 | Công viên Cung Thiếu nhi Đà Nẵng | Dong Dinh Museum | Chợ Cồn Hùng Vương | Công viên 29 tháng 3 |
| 8 | Funny Games Vincom Đà Nẵng | Chợ Cồn | Danang Riverwalk | Công viên Nam Dương |
| 9 | Công viên Thanh Niên | Danang Riverwalk | Chợ Kỳ Đồng | Chợ Cồn |
| 10 | Biển Thanh Bình | Lang Bich hoa Da Nang | NICKY KIDS - Khu Vui Chơi Dành Cho Bé | Chợ Cồn Hùng Vương |

| Bước | Đủ điều kiện / ứng viên | Kết quả | POI khớp sở thích bằng 0 | Cách đo chi phí |
| --- | ---: | ---: | ---: | --- |
| K1-A | 87 / 78 | 10 | 0 | Khoảng cách đường chim bay |
| K1-B | 87 / 75 | 10 | 0 | Khoảng cách đường chim bay |
| K1-C | 87 / 75 | 10 | 0 | Khoảng cách đường chim bay |
| K1-D | 93 / 77 | 10 | 4 | Khoảng cách đường chim bay |

### K2: thứ tự đầy đủ

| Hạng | K2-A | K2-B | K2-C | K2-D |
| ---: | --- | --- | --- | --- |
| 1 | Bãi Biển Thiên Đường | Bãi biển Mỹ Khê | Bãi Tắm Biển Mỹ Khê | Công viên Biển Đông |
| 2 | Biển Thanh Bình | Bãi Tắm Biển Mỹ Khê | Bãi biển Mỹ Khê | Bãi Tắm Biển Mỹ Khê |
| 3 | Bãi Tắm Biển Mỹ Khê | Công viên biển Mân Thái | Công viên biển Mân Thái | Công viên Bãi biển Mỹ Khê |
| 4 | Bãi biển Nguyễn Tất Thành | Công viên Bãi biển Mỹ Khê | Công viên Bãi biển Mỹ Khê | Chợ Phước Mỹ |
| 5 | Công viên Bãi biển Mỹ Khê | Công viên Biển Đông | Công viên Biển Đông | — |
| 6 | Công viên Biển Đông | Công viên Sao Biển | Công viên Sao Biển | — |
| 7 | Công viên 29 tháng 3 | Biển Thanh Bình | Bãi tắm Phạm Văn Đồng | — |
| 8 | Công viên Nam Dương | Bãi tắm Phạm Văn Đồng | Bãi tắm Mỹ Khê | — |
| 9 | Lang Bich hoa Da Nang | Bãi tắm Mỹ Khê | My Khe Beach | — |
| 10 | Bảo tàng Điêu khắc Chăm Đà Nẵng | My Khe Beach | Bãi tắm Mân Thái | — |

| Bước | Đủ điều kiện / ứng viên | Kết quả | POI khớp sở thích bằng 0 | Cách đo chi phí |
| --- | ---: | ---: | ---: | --- |
| K2-A | 46 / 46 | 10 | 4 | Thời gian OSRM |
| K2-B | 55 / 55 | 10 | 0 | Thời gian OSRM |
| K2-C | 39 / 39 | 10 | 0 | Thời gian OSRM |
| K2-D | 4 / 4 | 4 | 1 | Thời gian OSRM |

### K3: thứ tự đầy đủ

| Hạng | K3-A | K3-B | K3-C |
| ---: | --- | --- | --- |
| 1 | Biển Thanh Bình | Bãi Biển Thiên Đường | Biển Thanh Bình |
| 2 | Bãi biển Mỹ Khê | Biển Thanh Bình | Bãi biển Mỹ Khê |
| 3 | Công viên biển Mân Thái | Bãi Tắm Biển Mỹ Khê | Công viên biển Mân Thái |
| 4 | Bãi Biển Thiên Đường | Bãi biển Nguyễn Tất Thành | Bãi Biển Thiên Đường |
| 5 | Công viên Bãi biển Mỹ Khê | Công viên Bãi biển Mỹ Khê | Công viên Bãi biển Mỹ Khê |
| 6 | Bãi Tắm Biển Mỹ Khê | My Khe Beach | Bãi Tắm Biển Mỹ Khê |
| 7 | Bãi biển Tiên Sa | Công viên biển Mân Thái | Bãi biển Tiên Sa |
| 8 | Bãi biển Nguyễn Tất Thành | Bãi tắm Mỹ Khê | Bãi biển Nguyễn Tất Thành |
| 9 | Bãi biển Non Nước | Bãi tắm T20 | Bãi biển Non Nước |
| 10 | Công viên Sao Biển | Bãi tắm Phạm Văn Đồng | Công viên Sao Biển |

| Bước | Đủ điều kiện / ứng viên | Kết quả | POI khớp sở thích bằng 0 | Cách đo chi phí |
| --- | ---: | ---: | ---: | --- |
| K3-A | 87 / 77 | 10 | 0 | Khoảng cách đường chim bay |
| K3-B | 87 / 76 | 10 | 0 | Khoảng cách đường chim bay |
| K3-C | 87 / 77 | 10 | 0 | Khoảng cách đường chim bay |

<!-- GENERATED_RESULTS_END -->
