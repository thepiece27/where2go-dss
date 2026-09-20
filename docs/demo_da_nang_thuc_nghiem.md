# Demo Đà Nẵng: 29 kịch bản đã chạy thật và đánh giá kết quả

**Lần chạy chính:** 2026-09-19T23:11:36.727402+07:00 → 2026-09-19T23:13:23.430191+07:00. **Web:** http://127.0.0.1:8000. **Dataset:** `v2-c3ad315d02c5356a`; **routing:** `1e1d2ec5e5a86240`; **Chromium:** `151.0.7922.34`.

## 1. Kết luận để dùng khi demo

Hệ thống có thể demo việc đổi sở thích, ưu tiên, tọa độ, ngày đi và ràng buộc lịch trình bằng kết quả thật. Khả năng hiểu ý định còn hạn chế: không hiểu phủ định “không thích biển”, dễ trả loại hình không mong muốn khi bộ lọc xung đột, vẫn điền POI có mức khớp sở thích bằng 0. Trang Lịch trình tạo được tuyến và hộp xác nhận nhưng có lỗi JavaScript ở phần tải POI bản đồ. Vì vậy chưa thể nói toàn bộ trải nghiệm đã tốt hoặc mọi gợi ý đều phù hợp.

Bộ chính gồm **18 ca gợi ý và 10 ca lịch trình chỉ trả điểm trong vùng Đà Nẵng**; thêm **R19 là ca kiểm tra vượt phạm vi** khi người dùng vẫn chọn Đà Nẵng nhưng mở bán kính 30 km. Hội An xuất hiện ở ca âm này là phát hiện không đáp ứng ý định, không phải đưa Hội An vào lịch demo.

Đây là **agent mô phỏng thao tác của người dùng bằng Chromium**: nhập form, chọn dropdown, bấm chủ đề, tìm địa điểm, thêm vào chuyến, sửa thời lượng, đảo thứ tự, chọn/hủy/xác nhận phương án. Không có người tham gia nghiên cứu độc lập; không gọi đây là khảo sát người thật. Không mock phản hồi API, không thay thuật toán/dữ liệu để làm kết quả đẹp. Đánh giá “hợp lý/chưa tốt” bên dưới là nhận xét theo ý định từng ca và bằng chứng quan sát, không phải Precision/NDCG hay tỷ lệ hài lòng.

### Kết quả kiểm tra kỹ thuật

| Mục kiểm tra | Kết quả thực tế |
| --- | --- |
| Hoàn thành hành trình và nhận HTTP 200 | 29/29 ca; không có ca dừng do lỗi công cụ trong lần chạy chính |
| Ràng buộc và kiểm tra tự động | 221/232 điều kiện PASS; 11 FAIL = lỗi JavaScript ở 10 ca lịch + vùng Hội An ở R19 |
| Gợi ý đúng bán kính và đúng danh sách hiển thị | 19/19 ca; R09 là danh sách rỗng đúng điều kiện |
| Tuyến lịch trình | 27 phương án từ 10 ca; có geometry OSRM, đã chọn phương án đầu mỗi ca và kiểm tra lớp tuyến trên bản đồ |
| Địa lý bộ demo chính | 18/18 ca gợi ý và 10/10 ca lịch ở region=danang theo đa giác hiện có của dự án |
| Thay đổi thời lượng do người dùng nhập | Giữ 10 hoặc 360 phút ở các điểm được xếp; so số thực có dung sai |
| Xác nhận điều chỉnh | Các phương án thiếu điểm bắt buộc/đổi giờ có yêu cầu xác nhận; đã thực hiện hủy rồi chấp nhận thẻ đầu ở các ca cần xác nhận |
| Snapshot trong suốt lần chạy | Version health trước/sau giống nhau; dùng cùng catalog đang phục vụ |
| Chất lượng người dùng độc lập | NOT GRADED; không có nhãn độc lập để tính độ chính xác |

232 là số điều kiện kiểm tra, không phải 232 người dùng hoặc 232 kịch bản độc lập. R12/R13 có thể PASS kỹ thuật nhưng vẫn CHƯA TỐT về nhu cầu. Script kết thúc mã 1 vì giữ nguyên những FAIL quan sát được.

## 2. Chuẩn bị và quy ước thao tác

Mở cửa sổ trình duyệt riêng, chưa có nháp chuyến đi. Mỗi ca tự động dùng context mới để tránh ảnh hưởng lựa chọn cũ; nếu demo tay, bỏ hết điểm đã chọn và đặt lại form trước khi đổi sang ca độc lập. Riêng cặp đối chiếu giữ nguyên các trường khác theo bảng.

Mặc định trang Gợi ý: **Phạm vi = Theo địa phương đã chọn; Địa phương = Đà Nẵng; Nhóm địa điểm = Tham quan và ngoài trời; ngày = 20/09/2026; bán kính = 15 km; ưu tiên = Cân bằng các yếu tố; không chọn loại hình, không nhập nhu cầu nếu ca không yêu cầu.** Ngày 20/09 là Chủ nhật, 21/09 là thứ Hai; đây là ngày demo cố định.

Ba tọa độ sử dụng: tâm mẫu `(16.0544, 108.2022)`; điểm mẫu gần Mỹ Khê `(16.0630, 108.2450)`; điểm mẫu sườn núi `(16.1500, 108.0500)`. Đây là tọa độ nhập thử, không phải GPS đã đo của khách sạn hay điểm đỗ xe được xác nhận.

Bán kính 15 km chỉ là cấu hình để bộ demo này không vươn tới Hội An. Việc xác nhận phạm vi dựa trên `region_for(latitude, longitude)` và đa giác của dự án; không chỉ kiểm tra chuỗi `location`. R19 chứng minh bộ chọn hiện tại chưa thể diễn đạt hoàn toàn “Đà Nẵng nhưng không Hội An”. Không suy rộng rằng mọi tâm và mọi bán kính 15 km đều loại được Hội An.

Mỗi ca có: ý định và thao tác, kỳ vọng trước khi chạy, đầu ra cụ thể, so sánh, giải thích và đánh giá. Điểm TOPSIS thuộc [0,1] là **điểm tương đối trong pool**, không phải xác suất thích. Các bảng luôn tách km đường chim bay khỏi phút OSRM.

## 3. Các thay đổi đáng trình diễn nhất

| So sánh | Kết quả | Ý nghĩa |
| --- | --- | --- |
| R02 → R03: Cân bằng → Đi gần | Công viên 29 tháng 3 từ #4 → #1; cùng 10 POI | Ưu tiên gần thay thứ tự, không nhất thiết giảm khoảng cách trung bình |
| R02 → R05: thiên nhiên → lịch sử/văn hóa | Top-10 không giao nhau | Sở thích khai báo tác động rõ tới truy hồi/xếp hạng |
| R06 → R07: đổi tọa độ | Khoảng cách trung bình 2,475 → 1,413 km; giao 2/10 POI | Cá nhân hóa theo điểm xuất phát, đồng thời đổi pool |
| R07 → R08: 15 km → 1 km | 10 → 4 POI; dùng road_time | Không tự nới điều kiện; routing đầy đủ phụ thuộc pool |
| R11 → R12: biển → không thích biển | Cùng 10 POI và cùng thứ tự, 9/10 beach | Không hiểu phủ định |
| R13 → R14: mở Tất cả loại hình | 0/10 → 10/10 cafe | Bộ lọc cứng có thể lấn át nhu cầu mềm |
| R05 → R15: Chủ nhật → thứ Hai | Ho Chi Minh Museum bị loại | Loại ngày biết đóng; ngày không biết giờ vẫn có cảnh báo |
| T01 → T05: đổi tọa độ | Lái xe 17,17 → 7,86 phút | Tuyến thật thay theo điểm xuất phát |
| T01 → T02: về 18:00 → 09:00 | Phương án 08:00–10:43 yêu cầu xác nhận | Đề xuất đổi điều kiện, chưa đáp ứng giờ ban đầu |
| T03 → T10: bỏ một điểm bắt buộc | Cùng phương án về 08:44: từ cần xác nhận → không cần | Phân biệt bắt buộc và tùy chọn |

## 4. Nhóm gợi ý: thao tác và đầu ra từng ca

### R01 — Lần đầu đến Đà Nẵng, chưa biết chọn gì

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **(để trống)**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Có gợi ý theo vị trí; không tự nhận đã biết sở thích.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 77 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **2.096 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Chợ Cồn | Chợ | 0.901 | 2.016 | 2.016 |
| 2 | Bãi Biển Thiên Đường | Bãi biển | 0.897 | 2.175 | 2.175 |
| 3 | Đường hoa Bạch Đằng | Công viên | 0.895 | 2.458 | 2.458 |
| 4 | Semicircle Bridge | Cầu tham quan | 0.891 | 2.372 | 2.372 |
| 5 | Bảo tàng Mỹ thuật Đà Nẵng | Bảo tàng | 0.886 | 2.509 | 2.509 |
| 6 | Công viên 29 tháng 3 | Công viên | 0.880 | 0.936 | 0.936 |
| 7 | Bảo tàng Điêu khắc Chăm Đà Nẵng | Bảo tàng | 0.877 | 2.320 | 2.320 |
| 8 | Chợ Kỳ Đồng | Chợ | 0.869 | 2.347 | 2.347 |
| 9 | Công viên Nam Dương | Công viên | 0.867 | 1.793 | 1.793 |
| 10 | Lang Bich hoa Da Nang | Điểm tham quan | 0.864 | 2.030 | 2.030 |

**Vì sao thẻ đầu có điểm đó:** sở thích 1.0000; chất lượng hiệu chỉnh 0.8600; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Cách điểm xuất phát 2.0 km theo vị trí (đường chim bay). Nguồn ghi 4.3/5 từ 23025 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**Đánh giá: HỢP LÝ.** Không khai báo sở thích thì API trả personalized=false. Các tiêu chí vị trí, chất lượng và bằng chứng quyết định thứ hạng; không có cơ sở nói hệ thống đã học sở thích cá nhân. Danh sách pha trộn nhiều loại hình là hợp lý cho bước khám phá ban đầu.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R01.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R01.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R01.json)

### R02 — Muốn thiên nhiên và thư giãn

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Tăng ưu tiên công viên, biển, cảnh quan so với yêu cầu văn hóa.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 79 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **2.475 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Bãi Biển Thiên Đường | Bãi biển | 0.928 | 2.175 | 2.175 |
| 2 | Đường hoa Bạch Đằng | Công viên | 0.921 | 2.458 | 2.458 |
| 3 | Công viên Nam Dương | Công viên | 0.903 | 1.793 | 1.793 |
| 4 | Công viên 29 tháng 3 | Công viên | 0.902 | 0.936 | 0.936 |
| 5 | Quảng trường Bạch Đằng | Công viên | 0.896 | 2.306 | 2.306 |
| 6 | Công viên APEC | Công viên | 0.889 | 2.286 | 2.286 |
| 7 | Công viên Cung Thiếu nhi Đà Nẵng | Công viên | 0.872 | 2.905 | 2.905 |
| 8 | Funny Games Vincom Đà Nẵng | Công viên | 0.868 | 3.537 | 3.537 |
| 9 | Công viên Thanh Niên | Công viên | 0.868 | 3.361 | 3.361 |
| 10 | Biển Thanh Bình | Bãi biển | 0.860 | 2.989 | 2.989 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7818; chất lượng hiệu chỉnh 0.8708; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Cách điểm xuất phát 2.2 km theo vị trí (đường chim bay). Nguồn ghi 4.3/5 từ 60 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**Đánh giá: ĐẠT MỘT PHẦN.** Công viên và biển chiếm danh sách, phù hợp mong muốn thiên nhiên. Tuy nhiên Funny Games Vincom Đà Nẵng cũng xuất hiện: dữ liệu gán category=park và các tag thiên nhiên/ngoài trời. Đây là dấu hiệu cần kiểm duyệt loại hình, không nên dùng điểm thuật toán để bảo đảm nơi đó thực sự phù hợp đi thiên nhiên. Chưa xác minh thực địa địa điểm này.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R02.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R02.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R02.json)

### R03 — Giữ sở thích thiên nhiên, chuyển sang Đi gần

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Đi gần**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Quan sát khoảng cách và thứ tự; không yêu cầu mọi POI đều gần hơn.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 79 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **2.475 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Công viên 29 tháng 3 | Công viên | 0.934 | 0.936 | 0.936 |
| 2 | Bãi Biển Thiên Đường | Bãi biển | 0.917 | 2.175 | 2.175 |
| 3 | Công viên Nam Dương | Công viên | 0.917 | 1.793 | 1.793 |
| 4 | Đường hoa Bạch Đằng | Công viên | 0.900 | 2.458 | 2.458 |
| 5 | Quảng trường Bạch Đằng | Công viên | 0.893 | 2.306 | 2.306 |
| 6 | Công viên APEC | Công viên | 0.893 | 2.286 | 2.286 |
| 7 | Công viên Cung Thiếu nhi Đà Nẵng | Công viên | 0.859 | 2.905 | 2.905 |
| 8 | Biển Thanh Bình | Bãi biển | 0.852 | 2.989 | 2.989 |
| 9 | Công viên Thanh Niên | Công viên | 0.836 | 3.361 | 3.361 |
| 10 | Funny Games Vincom Đà Nẵng | Công viên | 0.831 | 3.537 | 3.537 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7553; chất lượng hiệu chỉnh 0.8815; bằng chứng 0.25. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.3, 0.2, 0.4, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Cách điểm xuất phát 0.9 km theo vị trí (đường chim bay). Nguồn ghi 4.4/5 từ 368 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Chưa có giờ mở cửa cho ngày đã chọn; cần kiểm tra trước khi đi. Điểm tiếp cận ô tô chưa được xác minh.

**So với R02:** các trường đổi = `preset`; giao nhau 10 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ.** Công viên 29 tháng 3, cách 0,936 km, từ hạng 4 lên hạng 1. Trọng số di chuyển tăng từ 0,20 lên 0,40. Cả tập 10 địa điểm vẫn giống R02 nên khoảng cách trung bình không giảm; điều cải thiện quan sát được là vị trí của điểm gần ở đầu danh sách, không phải mọi thống kê đều tốt hơn.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R03.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R03.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R03.json)

### R04 — Giữ sở thích thiên nhiên, ưu tiên đánh giá

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Đánh giá địa điểm**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Tăng ảnh hưởng chất lượng đã hiệu chỉnh theo số lượt đánh giá.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 79 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **2.554 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Đường hoa Bạch Đằng | Công viên | 0.911 | 2.458 | 2.458 |
| 2 | Bãi Biển Thiên Đường | Bãi biển | 0.903 | 2.175 | 2.175 |
| 3 | Công viên 29 tháng 3 | Công viên | 0.886 | 0.936 | 0.936 |
| 4 | Công viên Nam Dương | Công viên | 0.884 | 1.793 | 1.793 |
| 5 | Quảng trường Bạch Đằng | Công viên | 0.880 | 2.306 | 2.306 |
| 6 | Công viên APEC | Công viên | 0.866 | 2.286 | 2.286 |
| 7 | Công viên Cung Thiếu nhi Đà Nẵng | Công viên | 0.853 | 2.905 | 2.905 |
| 8 | Công viên Thanh Niên | Công viên | 0.844 | 3.361 | 3.361 |
| 9 | Funny Games Vincom Đà Nẵng | Công viên | 0.837 | 3.537 | 3.537 |
| 10 | Bãi biển Nguyễn Tất Thành | Bãi biển | 0.815 | 3.782 | 3.782 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7684; chất lượng hiệu chỉnh 0.9249; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.25, 0.45, 0.2, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Cách điểm xuất phát 2.5 km theo vị trí (đường chim bay). Nguồn ghi 4.7/5 từ 106 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R02:** các trường đổi = `preset`; giao nhau 9 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ.** Đường hoa Bạch Đằng lên đầu vì chất lượng hiệu chỉnh 0,9249 cao hơn Bãi Biển Thiên Đường 0,8708; trọng số chất lượng tăng từ 0,30 lên 0,45. Chất lượng trung bình tăng nhẹ nhưng đi xa hơn một chút. Đây là đánh đổi đúng với mẫu ưu tiên, không phải chứng minh điểm đó tốt nhất ngoài đời.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R04.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R04.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R04.json)

### R05 — Muốn tìm hiểu lịch sử, văn hóa

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **lịch sử, văn hóa**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Danh sách chuyển về bảo tàng, di tích và loại hình văn hóa.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 75 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **4.608 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Ho Chi Minh Museum | Bảo tàng | 0.922 | 1.762 | 1.762 |
| 2 | Bảo tàng Mỹ thuật Đà Nẵng | Bảo tàng | 0.916 | 2.509 | 2.509 |
| 3 | Bảo tàng Điêu khắc Chăm Đà Nẵng | Bảo tàng | 0.900 | 2.320 | 2.320 |
| 4 | Bảo tàng Đà Nẵng | Bảo tàng | 0.900 | 3.263 | 3.263 |
| 5 | Khu Căn cứ Cách mạng K20 | Bảo tàng | 0.838 | 5.593 | 5.593 |
| 6 | Động Vân Thông | Di tích | 0.782 | 8.642 | 8.642 |
| 7 | Bảo tàng Phật giáo | Bảo tàng | 0.781 | 8.289 | 8.289 |
| 8 | Dong Dinh Museum | Bảo tàng | 0.761 | 9.389 | 9.389 |
| 9 | Chợ Cồn | Chợ | 0.557 | 2.016 | 2.016 |
| 10 | Danang Riverwalk | Điểm tham quan | 0.557 | 2.298 | 2.298 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7594; chất lượng hiệu chỉnh 0.8597; bằng chứng 0.25. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Khớp sở thích: lịch sử, văn hóa. Cách điểm xuất phát 1.8 km theo vị trí (đường chim bay). Nguồn ghi 4.3/5 từ 1604 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Chưa có giờ mở cửa cho ngày đã chọn; cần kiểm tra trước khi đi. Điểm tiếp cận ô tô chưa được xác minh.

**So với R02:** các trường đổi = `interests`; giao nhau 0 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ.** Top đầu chuyển sang bảo tàng, Top-10 không còn điểm chung với R02. Đây là tín hiệu cá nhân hóa theo sở thích khai báo có tác dụng. Các vị trí cuối như chợ và đường dạo là kết quả ưu tiên mềm, không phải lọc chỉ bảo tàng. Ho Chi Minh Museum thiếu thông tin giờ Chủ nhật nên cần kiểm tra giờ trước khi đi.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R05.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R05.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R05.json)

### R06 — Muốn ra biển, chọn rõ loại hình Bãi biển

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **Bãi biển**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Biển được ưu tiên; loại hình là ưu tiên mềm, kiểm tra mức pha trộn.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 79 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **2.475 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Bãi Biển Thiên Đường | Bãi biển | 0.957 | 2.175 | 2.175 |
| 2 | Đường hoa Bạch Đằng | Công viên | 0.954 | 2.458 | 2.458 |
| 3 | Công viên Nam Dương | Công viên | 0.927 | 1.793 | 1.793 |
| 4 | Quảng trường Bạch Đằng | Công viên | 0.922 | 2.306 | 2.306 |
| 5 | Công viên 29 tháng 3 | Công viên | 0.920 | 0.936 | 0.936 |
| 6 | Công viên APEC | Công viên | 0.918 | 2.286 | 2.286 |
| 7 | Funny Games Vincom Đà Nẵng | Công viên | 0.912 | 3.537 | 3.537 |
| 8 | Công viên Thanh Niên | Công viên | 0.906 | 3.361 | 3.361 |
| 9 | Biển Thanh Bình | Bãi biển | 0.904 | 2.989 | 2.989 |
| 10 | Công viên Cung Thiếu nhi Đà Nẵng | Công viên | 0.902 | 2.905 | 2.905 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.8234; chất lượng hiệu chỉnh 0.8708; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Thuộc loại hình bạn ưu tiên. Cách điểm xuất phát 2.2 km theo vị trí (đường chim bay). Nguồn ghi 4.3/5 từ 60 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R02:** các trường đổi = `preferred_categories, preset`; giao nhau 10 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: ĐẠT MỘT PHẦN.** Chỉ 2/10 kết quả thuộc beach dù đã chọn Bãi biển. Muốn cô lập tác động chọn loại hình, đối chiếu R18: cùng thiên nhiên, Hợp sở thích và bán kính 15 km; chỉ thêm preferred_categories=beach. Công viên đã khớp toàn bộ tag thiên nhiên nên taxonomy cũng đạt 1; chọn beach không tạo thưởng độc quyền vượt mức 1. Người thật muốn chuyên biển có thể thất vọng. Dùng ô Nhu cầu nhập biển như R11 phù hợp hơn trong ca đã thử.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R06.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R06.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R06.json)

### R07 — Cùng nhu cầu ra biển nhưng xuất phát gần Mỹ Khê

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **Bãi biển**, tọa độ **(16.063, 108.245)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Chi phí di chuyển thay đổi theo tọa độ, có thể đổi thứ hạng.

**Web trả thực tế:** 10 POI; 89 qua điều kiện, 69 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **1.413 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Công viên Biển Đông | Công viên | 0.973 | 0.819 | 0.819 |
| 2 | Bãi Tắm Biển Mỹ Khê | Bãi biển | 0.962 | 0.764 | 0.764 |
| 3 | Công viên Hồ Nghinh | Công viên | 0.950 | 1.494 | 1.494 |
| 4 | Công viên Sao Biển | Công viên | 0.935 | 1.932 | 1.932 |
| 5 | Công viên cá voi | Công viên | 0.935 | 1.865 | 1.865 |
| 6 | Đường hoa Bạch Đằng | Công viên | 0.930 | 2.227 | 2.227 |
| 7 | Funny Games Vincom Đà Nẵng | Công viên | 0.925 | 1.849 | 1.849 |
| 8 | Công viên Bãi biển Mỹ Khê | Bãi biển | 0.923 | 0.165 | 0.165 |
| 9 | Bãi tắm Phạm Văn Đồng | Bãi biển | 0.916 | 1.160 | 1.160 |
| 10 | My Khe Beach | Bãi biển | 0.910 | 1.858 | 1.858 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.8222; chất lượng hiệu chỉnh 0.9195; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Cách điểm xuất phát 0.8 km theo vị trí (đường chim bay). Nguồn ghi 4.6/5 từ 2577 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R06:** các trường đổi = `start`; giao nhau 2 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ.** Chỉ đổi tọa độ so với R06, các điểm ven biển phía đông lên đầu. Khoảng cách trung bình của danh sách mới giảm rõ. Bán kính cũng được tính lại quanh tâm mới, làm tập ứng viên thay đổi; vì vậy không quy mọi thay đổi điểm TOPSIS chỉ cho quãng đường.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R07.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R07.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R07.json)

### R08 — Chỉ muốn đi trong bán kính 1 km từ gần Mỹ Khê

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **1 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **Bãi biển**, tọa độ **(16.063, 108.245)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Mọi POI phải trong 1 km đường chim bay; được phép ít hơn 10 kết quả.

**Web trả thực tế:** 4 POI; 4 qua điều kiện, 4 trong pool xếp hạng. Thước đo: **phút lái xe OSRM (API lưu giây)**. Khoảng cách đường chim bay trung bình: **0.560 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Phút OSRM |
| --- | --- | --- | --- | --- | --- |
| 1 | Công viên Biển Đông | Công viên | 0.997 | 0.819 | 1.370 |
| 2 | Bãi Tắm Biển Mỹ Khê | Bãi biển | 0.915 | 0.764 | 2.295 |
| 3 | Công viên Bãi biển Mỹ Khê | Bãi biển | 0.810 | 0.165 | 3.570 |
| 4 | Chợ Phước Mỹ | Chợ | 0.166 | 0.491 | 1.702 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.8222; chất lượng hiệu chỉnh 0.9195; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Khoảng 1 phút lái xe từ điểm xuất phát theo OSRM. Nguồn ghi 4.6/5 từ 2577 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R07:** các trường đổi = `radius_km`; giao nhau 3 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: ĐẠT MỘT PHẦN.** Lọc bán kính đúng: chỉ còn 4 kết quả, đều không quá 1 km; không lấy điểm xa để đủ 10. OSRM có dữ liệu đầy đủ cho pool nhỏ nên chuyển từ km đường chim bay sang giây lái xe. Tuy nhiên Chợ Phước Mỹ có preference_match=0 vẫn được điền vào danh sách: hệ thống chưa có ngưỡng loại gợi ý không hợp sở thích. Công viên gần nhất theo tọa độ không nhất thiết có thời gian ô tô thấp nhất do điểm tiếp cận/mạng đường.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R08.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R08.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R08.json)

### R09 — Gia đình tìm điểm ở sườn núi, bán kính quá hẹp

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **1 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **gia đình**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.15, 108.05)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Nếu không có dữ liệu phù hợp phải báo rỗng, không tự mở rộng bán kính.

**Web trả thực tế:** 0 POI; 0 qua điều kiện, 0 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **— km**.

**Thông báo nguyên văn:** Chưa có POI đáp ứng điều kiện. Hãy đổi vị trí, ngày hoặc mở rộng bán kính; hệ thống không tự nới điều kiện.

**Đánh giá: HỢP LÝ.** Không tìm được ứng viên và web giải thích cần đổi vị trí, ngày hoặc bán kính. Đây là hành vi đúng trong ca không có dữ liệu đáp ứng. Không suy ra khu vực thực địa hoàn toàn không có điểm tham quan; chỉ biết catalog và điều kiện hiện tại không trả được điểm.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R09.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R09.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R09.json)

### R10 — Ngày mưa: muốn bảo tàng, trong nhà

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **bảo tàng, trong nhà**. Mở Loại hình và điểm xuất phát: loại hình **Bảo tàng**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Bảo tàng nên nổi bật; kiểm tra có lẫn nơi ngoài trời không.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 76 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **3.787 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Bảo tàng Mỹ thuật Đà Nẵng | Bảo tàng | 0.973 | 2.509 | 2.509 |
| 2 | Bảo tàng Đà Nẵng | Bảo tàng | 0.964 | 3.263 | 3.263 |
| 3 | Ho Chi Minh Museum | Bảo tàng | 0.962 | 1.762 | 1.762 |
| 4 | Bảo tàng Điêu khắc Chăm Đà Nẵng | Bảo tàng | 0.932 | 2.320 | 2.320 |
| 5 | Bảo tàng Phật giáo | Bảo tàng | 0.908 | 8.289 | 8.289 |
| 6 | Khu Căn cứ Cách mạng K20 | Bảo tàng | 0.907 | 5.593 | 5.593 |
| 7 | Dong Dinh Museum | Bảo tàng | 0.896 | 9.389 | 9.389 |
| 8 | Công viên 29 tháng 3 | Công viên | 0.165 | 0.936 | 0.936 |
| 9 | Chợ Cồn | Chợ | 0.157 | 2.016 | 2.016 |
| 10 | Công viên Nam Dương | Công viên | 0.157 | 1.793 | 1.793 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.8565; chất lượng hiệu chỉnh 0.8986; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Thuộc loại hình bạn ưu tiên. Cách điểm xuất phát 2.5 km theo vị trí (đường chim bay). Nguồn ghi 4.5/5 từ 1648 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**Đánh giá: ĐẠT MỘT PHẦN.** 7 kết quả đầu là museum, phù hợp hướng tìm bảo tàng. Nhưng hệ thống điền thêm Công viên 29 tháng 3, Chợ Cồn, Công viên Nam Dương ở cuối; hai công viên có preference_match=0. Với người tránh mưa, đó là gợi ý chưa tốt. Hệ thống không đọc dự báo thời tiết và tag trong nhà không bảo đảm toàn bộ trải nghiệm ở nơi có mái che.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R10.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R10.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R10.json)

### R11 — Nhập ngắn: biển

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **biển**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Thiết lập đối chứng để kiểm tra khả năng hiểu phủ định.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 78 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **5.355 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Biển Thanh Bình | Bãi biển | 0.922 | 2.989 | 2.989 |
| 2 | Bãi biển Mỹ Khê | Bãi biển | 0.877 | 5.326 | 5.326 |
| 3 | Bãi Biển Thiên Đường | Bãi biển | 0.856 | 2.175 | 2.175 |
| 4 | Công viên biển Mân Thái | Bãi biển | 0.832 | 6.320 | 6.320 |
| 5 | Công viên Bãi biển Mỹ Khê | Bãi biển | 0.800 | 4.830 | 4.830 |
| 6 | Bãi Tắm Biển Mỹ Khê | Bãi biển | 0.799 | 4.831 | 4.831 |
| 7 | Bãi biển Nguyễn Tất Thành | Bãi biển | 0.778 | 3.782 | 3.782 |
| 8 | Bãi biển Tiên Sa | Bãi biển | 0.753 | 8.035 | 8.035 |
| 9 | Bãi biển Non Nước | Bãi biển | 0.658 | 10.075 | 10.075 |
| 10 | Công viên Sao Biển | Công viên | 0.650 | 5.186 | 5.186 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.1095; chất lượng hiệu chỉnh 0.7875; bằng chứng 0.25. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Nội dung địa điểm có từ ngữ tương đồng với nhu cầu. Cách điểm xuất phát 3.0 km theo vị trí (đường chim bay). Nguồn ghi 3.5/5 từ 55 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Chưa có giờ mở cửa cho ngày đã chọn; cần kiểm tra trước khi đi. Điểm tiếp cận ô tô chưa được xác minh.

**Đánh giá: HỢP LÝ.** 9/10 kết quả thuộc beach. Từ biển có trong tên/nội dung nên TF-IDF tạo khác biệt rõ giữa biển và loại hình khác. Điểm số vẫn tương đối trong pool; nhiều thực thể Mỹ Khê cần mở bản đồ xem vị trí, không mặc định là các trải nghiệm hoàn toàn khác nhau.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R11.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R11.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R11.json)

### R12 — Nhập: không thích biển

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **không thích biển**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Theo ý định người thật, phải giảm gợi ý biển; nếu vẫn ưu tiên biển là hạn chế ngữ nghĩa.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 78 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **5.355 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Biển Thanh Bình | Bãi biển | 0.922 | 2.989 | 2.989 |
| 2 | Bãi biển Mỹ Khê | Bãi biển | 0.877 | 5.326 | 5.326 |
| 3 | Bãi Biển Thiên Đường | Bãi biển | 0.856 | 2.175 | 2.175 |
| 4 | Công viên biển Mân Thái | Bãi biển | 0.832 | 6.320 | 6.320 |
| 5 | Công viên Bãi biển Mỹ Khê | Bãi biển | 0.799 | 4.830 | 4.830 |
| 6 | Bãi Tắm Biển Mỹ Khê | Bãi biển | 0.799 | 4.831 | 4.831 |
| 7 | Bãi biển Nguyễn Tất Thành | Bãi biển | 0.778 | 3.782 | 3.782 |
| 8 | Bãi biển Tiên Sa | Bãi biển | 0.752 | 8.035 | 8.035 |
| 9 | Bãi biển Non Nước | Bãi biển | 0.658 | 10.075 | 10.075 |
| 10 | Công viên Sao Biển | Công viên | 0.650 | 5.186 | 5.186 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.0485; chất lượng hiệu chỉnh 0.7875; bằng chứng 0.25. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Nội dung địa điểm có từ ngữ tương đồng với nhu cầu. Cách điểm xuất phát 3.0 km theo vị trí (đường chim bay). Nguồn ghi 3.5/5 từ 55 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Chưa có giờ mở cửa cho ngày đã chọn; cần kiểm tra trước khi đi. Điểm tiếp cận ô tô chưa được xác minh.

**So với R11:** các trường đổi = `interests`; giao nhau 10 POI; giữ nguyên toàn bộ thứ tự. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: CHƯA TỐT.** 10/10 POI và thứ tự giống R11, vẫn có 9 bãi biển. Cụm không thích không được chuyển thành điều kiện loại trừ; TF-IDF vẫn giữ tín hiệu từ biển. Điểm số có thay đổi nhỏ nhưng không sửa được ý định bị hiểu ngược. Đây là lỗi về chất lượng hiểu nhu cầu, dù HTTP và render đều thành công.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R12.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R12.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R12.json)

### R13 — Tìm cà phê nhưng để nhóm Tham quan và ngoài trời

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **cà phê**. Mở Loại hình và điểm xuất phát: loại hình **Cà phê**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Nhóm lọc hiện tại loại cà phê; đánh giá mức dễ hiểu của kết quả đối với người dùng.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 78 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **4.180 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Công viên cá voi | Công viên | 0.915 | 5.545 | 5.545 |
| 2 | Công viên Thanh Niên | Công viên | 0.705 | 3.361 | 3.361 |
| 3 | Biển Thanh Bình | Bãi biển | 0.704 | 2.989 | 2.989 |
| 4 | Công viên Nam Dương | Công viên | 0.702 | 1.793 | 1.793 |
| 5 | My Khe Beach | Bãi biển | 0.701 | 5.174 | 5.174 |
| 6 | Công viên Sao Biển | Công viên | 0.674 | 5.186 | 5.186 |
| 7 | Quảng trường Bạch Đằng | Công viên | 0.674 | 2.306 | 2.306 |
| 8 | Đường hoa Bạch Đằng | Công viên | 0.669 | 2.458 | 2.458 |
| 9 | Công viên Biển Đông | Công viên | 0.664 | 4.987 | 4.987 |
| 10 | Hoang Sa Beach | Bãi biển | 0.657 | 8.000 | 8.000 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.0428; chất lượng hiệu chỉnh 0.8372; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Nội dung địa điểm có từ ngữ tương đồng với nhu cầu. Cách điểm xuất phát 5.5 km theo vị trí (đường chim bay). Nguồn ghi 4.0/5 từ 75 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**Đánh giá: CHƯA TỐT.** Người dùng muốn cà phê nhưng bộ lọc Tham quan và ngoài trời loại cafe trước khi xếp hạng. Không có quán cà phê nào trong kết quả, web vẫn trả 10 điểm khác. Công viên cá voi còn đạt score khoảng 0,915 dù sở thích chỉ khớp 0,0428. Thiếu cảnh báo xung đột giữa bộ lọc và nhu cầu; không được biện minh điểm cao là độ phù hợp cao tuyệt đối.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R13.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R13.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R13.json)

### R14 — Sửa nhóm thành Tất cả loại hình để tìm cà phê

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tất cả loại hình**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **cà phê**. Mở Loại hình và điểm xuất phát: loại hình **Cà phê**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Cà phê có thể xuất hiện trở lại khi bỏ bộ lọc loại trừ.

**Web trả thực tế:** 10 POI; 353 qua điều kiện, 116 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **1.983 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Trình cà phê | Cà phê | 0.886 | 2.523 | 2.523 |
| 2 | Cà phê 27 | Cà phê | 0.872 | 1.177 | 1.177 |
| 3 | Cộng Cà Phê | Cà phê | 0.858 | 2.384 | 2.384 |
| 4 | Highlands Coffee | Cà phê | 0.857 | 1.713 | 1.713 |
| 5 | Cà Phê Chim 606 | Cà phê | 0.853 | 1.722 | 1.722 |
| 6 | Highlands Coffee | Cà phê | 0.852 | 2.143 | 2.143 |
| 7 | Nia Coffee | Cà phê | 0.851 | 2.068 | 2.068 |
| 8 | Sơn Hải | Cà phê | 0.851 | 1.004 | 1.004 |
| 9 | Pillar Coffee | Cà phê | 0.850 | 2.210 | 2.210 |
| 10 | HT ca phe | Cà phê | 0.849 | 2.884 | 2.884 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.8691; chất lượng hiệu chỉnh 0.9595; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Thuộc loại hình bạn ưu tiên. Cách điểm xuất phát 2.5 km theo vị trí (đường chim bay). Nguồn ghi 4.8/5 từ 7557 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R13:** các trường đổi = `tourism_only`; giao nhau 0 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: ĐẠT MỘT PHẦN.** Chỉ đổi Nhóm địa điểm sang Tất cả loại hình, cả 10 kết quả trở thành cafe: phục hồi được ý định tìm quán. Tuy nhiên 9/10 không có cặp rating–review đủ bằng chứng và dùng chất lượng trung tính 0,5. Trình cà phê có quan sát rating hợp lệ; không nên nói mọi quán trong danh sách đã được đánh giá chất lượng tốt.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R14.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R14.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R14.json)

### R15 — Vẫn thích lịch sử, văn hóa nhưng chuyển sang thứ Hai

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-21**, bán kính **15 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **lịch sử, văn hóa**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Chỉ thay đổi do dữ liệu lịch mở cửa; không bắt buộc đảo hạng nếu dữ liệu không khác.

**Web trả thực tế:** 10 POI; 87 qua điều kiện, 75 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **4.635 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Bảo tàng Mỹ thuật Đà Nẵng | Bảo tàng | 0.917 | 2.509 | 2.509 |
| 2 | Bảo tàng Đà Nẵng | Bảo tàng | 0.902 | 3.263 | 3.263 |
| 3 | Bảo tàng Điêu khắc Chăm Đà Nẵng | Bảo tàng | 0.901 | 2.320 | 2.320 |
| 4 | Khu Căn cứ Cách mạng K20 | Bảo tàng | 0.843 | 5.593 | 5.593 |
| 5 | Động Vân Thông | Di tích | 0.792 | 8.642 | 8.642 |
| 6 | Bảo tàng Phật giáo | Bảo tàng | 0.790 | 8.289 | 8.289 |
| 7 | Dong Dinh Museum | Bảo tàng | 0.771 | 9.389 | 9.389 |
| 8 | Chợ Cồn | Chợ | 0.550 | 2.016 | 2.016 |
| 9 | Danang Riverwalk | Điểm tham quan | 0.550 | 2.298 | 2.298 |
| 10 | Lang Bich hoa Da Nang | Điểm tham quan | 0.546 | 2.030 | 2.030 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7363; chất lượng hiệu chỉnh 0.8986; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Khớp sở thích: lịch sử, văn hóa. Cách điểm xuất phát 2.5 km theo vị trí (đường chim bay). Nguồn ghi 4.5/5 từ 1648 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R05:** các trường đổi = `date`; giao nhau 9 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ.** Đổi riêng Chủ nhật 20/09 sang thứ Hai 21/09 khiến Ho Chi Minh Museum bị loại. Chi tiết POI lưu hours_weekly[0]=[] (thứ Hai đóng), còn Chủ nhật là null (chưa biết), nên giải thích bám dữ liệu là: thứ Hai có bằng chứng đóng cửa trong catalog. Không nói đã kiểm tra lịch mở cửa trực tiếp tại bảo tàng.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R15.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R15.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R15.json)

### R16 — Chọn một điểm rồi xin gợi ý tiếp

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** POI đã chọn không bị gợi ý lại, lựa chọn được giữ khi chuyển trang và tải lại.

**Web trả thực tế:** 10 POI; 87 qua điều kiện, 78 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **2.635 km**.

Thao tác bổ sung đã chạy: trước bảng dưới, thêm thẻ đầu Bãi Biển Thiên Đường, bấm Nhận gợi ý lần nữa; sau đó sang Lịch trình và tải lại để kiểm tra vẫn giữ lựa chọn.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Đường hoa Bạch Đằng | Công viên | 0.922 | 2.458 | 2.458 |
| 2 | Công viên Nam Dương | Công viên | 0.903 | 1.793 | 1.793 |
| 3 | Công viên 29 tháng 3 | Công viên | 0.902 | 0.936 | 0.936 |
| 4 | Quảng trường Bạch Đằng | Công viên | 0.896 | 2.306 | 2.306 |
| 5 | Công viên APEC | Công viên | 0.889 | 2.286 | 2.286 |
| 6 | Công viên Cung Thiếu nhi Đà Nẵng | Công viên | 0.873 | 2.905 | 2.905 |
| 7 | Funny Games Vincom Đà Nẵng | Công viên | 0.869 | 3.537 | 3.537 |
| 8 | Công viên Thanh Niên | Công viên | 0.868 | 3.361 | 3.361 |
| 9 | Biển Thanh Bình | Bãi biển | 0.860 | 2.989 | 2.989 |
| 10 | Bãi biển Nguyễn Tất Thành | Bãi biển | 0.847 | 3.782 | 3.782 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7684; chất lượng hiệu chỉnh 0.9249; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Cách điểm xuất phát 2.5 km theo vị trí (đường chim bay). Nguồn ghi 4.7/5 từ 106 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R02:** các trường đổi = `selected_poi_ids`; giao nhau 9 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ VỀ LỰA CHỌN.** Sau khi thêm Bãi Biển Thiên Đường, lần gợi ý tiếp không trả lại POI đó; danh sách đã chọn vẫn còn sau sang Lịch trình và tải lại. Đây là kiểm tra tính liên tục của hành trình người dùng. Lỗi bản đồ ở trang Lịch trình được đánh giá riêng trong nhóm T; ca này không chứng minh cả trang Lịch trình không có lỗi.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R16.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R16.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R16.json)

### R17 — Thiên nhiên nhưng chỉ 5 km quanh trung tâm

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **5 km**, mẫu **Cân bằng các yếu tố**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Tất cả kết quả trong 5 km; kiểm tra có dùng được thời gian đường ô tô khi pool nhỏ hơn.

**Web trả thực tế:** 10 POI; 47 qua điều kiện, 47 trong pool xếp hạng. Thước đo: **phút lái xe OSRM (API lưu giây)**. Khoảng cách đường chim bay trung bình: **2.804 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Phút OSRM |
| --- | --- | --- | --- | --- | --- |
| 1 | Công viên Nam Dương | Công viên | 0.917 | 1.793 | 2.702 |
| 2 | Công viên 29 tháng 3 | Công viên | 0.917 | 0.936 | 1.968 |
| 3 | Đường hoa Bạch Đằng | Công viên | 0.909 | 2.458 | 3.920 |
| 4 | Bãi Biển Thiên Đường | Bãi biển | 0.886 | 2.175 | 4.460 |
| 5 | Quảng trường Bạch Đằng | Công viên | 0.886 | 2.306 | 3.937 |
| 6 | Công viên APEC | Công viên | 0.877 | 2.286 | 4.118 |
| 7 | Công viên Cung Thiếu nhi Đà Nẵng | Công viên | 0.843 | 2.905 | 5.072 |
| 8 | Công viên Thanh Niên | Công viên | 0.831 | 3.361 | 5.622 |
| 9 | Bãi Tắm Biển Mỹ Khê | Bãi biển | 0.806 | 4.831 | 6.570 |
| 10 | Công viên Biển Đông | Công viên | 0.802 | 4.987 | 6.780 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7723; chất lượng hiệu chỉnh 0.8947; bằng chứng 0.25. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.4, 0.3, 0.2, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Khoảng 3 phút lái xe từ điểm xuất phát theo OSRM. Nguồn ghi 4.5/5 từ 17 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Chưa có giờ mở cửa cho ngày đã chọn; cần kiểm tra trước khi đi. Điểm tiếp cận ô tô chưa được xác minh.

**So với R02:** các trường đổi = `radius_km`; giao nhau 8 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ, CÓ ĐÁNH ĐỔI.** Bán kính giảm từ 15 xuống 5 km, pool còn 47 ứng viên và đủ đường OSRM; web dùng thời gian lái xe. Top-1 là Công viên Nam Dương, không phải điểm gần nhất theo đường chim bay. Khoảng cách trung bình Top-10 còn tăng từ khoảng 2,475 lên 2,804 km: vừa đổi pool, vừa đổi thước đo di chuyển nên không có quy luật thu hẹp bán kính luôn làm trung bình Top-10 giảm.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R17.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R17.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R17.json)

### R18 — Cùng thiên nhiên, ưu tiên Hợp sở thích

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **15 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **thiên nhiên**. Mở Loại hình và điểm xuất phát: loại hình **(không chọn)**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Tăng trọng số sở thích; kết quả có thể giữ nguyên nếu các tiêu chí cùng ủng hộ một nhóm.

**Web trả thực tế:** 10 POI; 88 qua điều kiện, 79 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **2.475 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Bãi Biển Thiên Đường | Bãi biển | 0.947 | 2.175 | 2.175 |
| 2 | Đường hoa Bạch Đằng | Công viên | 0.935 | 2.458 | 2.458 |
| 3 | Công viên Nam Dương | Công viên | 0.915 | 1.793 | 1.793 |
| 4 | Quảng trường Bạch Đằng | Công viên | 0.910 | 2.306 | 2.306 |
| 5 | Công viên 29 tháng 3 | Công viên | 0.907 | 0.936 | 0.936 |
| 6 | Công viên APEC | Công viên | 0.905 | 2.286 | 2.286 |
| 7 | Funny Games Vincom Đà Nẵng | Công viên | 0.900 | 3.537 | 3.537 |
| 8 | Công viên Thanh Niên | Công viên | 0.897 | 3.361 | 3.361 |
| 9 | Biển Thanh Bình | Bãi biển | 0.895 | 2.989 | 2.989 |
| 10 | Công viên Cung Thiếu nhi Đà Nẵng | Công viên | 0.892 | 2.905 | 2.905 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.7818; chất lượng hiệu chỉnh 0.8708; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Khớp sở thích: thiên nhiên. Cách điểm xuất phát 2.2 km theo vị trí (đường chim bay). Nguồn ghi 4.3/5 từ 60 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R02:** các trường đổi = `preset`; giao nhau 10 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: HỢP LÝ.** Tăng trọng số sở thích lên 0,55 không thay ba vị trí đầu trong ca này; cùng 10 POI nhưng một số vị trí phía sau đổi. Điều này hợp lý khi các điểm đầu vốn đã có điểm sở thích tốt. Không dựng câu chuyện rằng cứ thay mẫu ưu tiên là toàn bộ danh sách phải khác.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R18.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R18.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R18.json)

### R19 — Kiểm tra ranh giới: chọn Đà Nẵng, mở rộng bán kính 30 km

**Người demo thao tác:** tại `/`, chọn Đà Nẵng và Theo địa phương đã chọn. Đặt nhóm **Tham quan và ngoài trời**, ngày **2026-09-20**, bán kính **30 km**, mẫu **Hợp sở thích**. Chủ đề/nhu cầu: **bảo tàng, trong nhà**. Mở Loại hình và điểm xuất phát: loại hình **Bảo tàng**, tọa độ **(16.0544, 108.2022)**. Bấm **Nhận gợi ý**, mở **Vì sao được gợi ý?** ở thẻ đầu.

**Kỳ vọng trước khi chạy:** Ý định chỉ Đà Nẵng không bao gồm Hội An; kiểm tra vùng theo tọa độ, không chỉ nhãn location.

**Web trả thực tế:** 10 POI; 128 qua điều kiện, 96 trong pool xếp hạng. Thước đo: **km đường chim bay**. Khoảng cách đường chim bay trung bình: **10.327 km**.

| # | POI thực tế | Loại | TOPSIS | Km chim bay | Chi phí (km) |
| --- | --- | --- | --- | --- | --- |
| 1 | Bảo tàng Đà Nẵng | Bảo tàng | 0.901 | 3.263 | 3.263 |
| 2 | Bảo tàng Mỹ thuật Đà Nẵng | Bảo tàng | 0.901 | 2.509 | 2.509 |
| 3 | Dong Dinh Museum | Bảo tàng | 0.898 | 9.389 | 9.389 |
| 4 | Bảo tàng Phật giáo | Bảo tàng | 0.896 | 8.289 | 8.289 |
| 5 | Ho Chi Minh Museum | Bảo tàng | 0.896 | 1.762 | 1.762 |
| 6 | Bảo tàng Hội An | Bảo tàng | 0.856 | 23.662 | 23.662 |
| 7 | Bảo tàng Điêu khắc Chăm Đà Nẵng | Bảo tàng | 0.856 | 2.320 | 2.320 |
| 8 | Khu Căn cứ Cách mạng K20 | Bảo tàng | 0.850 | 5.593 | 5.593 |
| 9 | Di San Vô Giá | Bảo tàng | 0.848 | 24.241 | 24.241 |
| 10 | Terracotta Park | Bảo tàng | 0.814 | 22.244 | 22.244 |

**Vì sao thẻ đầu có điểm đó:** sở thích 0.8579; chất lượng hiệu chỉnh 0.8599; bằng chứng 0.50. Trọng số [sở thích, chất lượng, di chuyển, bằng chứng] = [0.55, 0.2, 0.15, 0.1]. Lời giải thích API: Thuộc loại hình bạn ưu tiên. Cách điểm xuất phát 3.3 km theo vị trí (đường chim bay). Nguồn ghi 4.3/5 từ 3691 đánh giá.

**Dữ liệu thiếu của thẻ đầu:** Điểm tiếp cận ô tô chưa được xác minh.

**So với R10:** các trường đổi = `radius_km`; giao nhau 7 POI; danh sách hoặc thứ tự đã thay đổi. Không quy kết riêng một yếu tố nếu liệt kê nhiều trường đổi.

**Đánh giá: CHƯA ĐẠT PHẠM VI.** Mở từ 15 lên 30 km làm xuất hiện Bảo tàng Hội An, Di San Vô Giá và Terracotta Park; đối chiếu tọa độ cho region=hoi_an dù cả ba ghi location=Đà Nẵng. Nhãn hành chính không đủ diễn đạt ý định khu vực Đà Nẵng, không Hội An. Ca này là phép thử âm phát hiện vượt phạm vi, không phải kịch bản dẫn người dùng đi Hội An. Bộ demo chính R01–R18 và T01–T10 đã đối chiếu tất cả điểm trả về ở region=danang.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/R19.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/R19.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/R19.json)

## 5. Nhóm lịch trình: một chuyến thật và các biến thể

**Chuẩn bị chung cho từng ca:** sang Khám phá, chọn Địa phương Đà Nẵng, chuyến đi Đà Nẵng. Tìm `my khe`, chọn đúng **Bãi biển Mỹ Khê** (`osm:relation:19000664`); tìm `pham van dong`, chọn **Bãi tắm Phạm Văn Đồng** (`poi-google:9f6b613e52c6d0f34461666b`). Có nhiều tên gần giống Mỹ Khê, phải chọn đúng thực thể này để lặp lại các con số.

Bấm Lịch trình 2. Đặt ngày 20/09/2026, giờ đi 08:00, giờ về 18:00, tâm mẫu (16.0544,108.2022); mở Tùy chọn thêm, tắt ăn/nghỉ/tự bổ sung trừ ca có yêu cầu. Đánh dấu cả hai Nhất định phải ghé trừ ca chỉ yêu cầu Mỹ Khê. Bấm Xem lịch gợi ý. Chọn thẻ đầu; khi có hộp điều chỉnh, bấm Quay lại, kiểm tra chưa đổi lựa chọn, mở lại và Chấp nhận điều chỉnh và chọn lịch.

**Lỗi chung đã quan sát:** cả 10 ca phát sinh `exploreFilters is not defined`, `mapFeatures` không có POI, dù tuyến của phương án đã chọn vẫn vẽ được. Vì thế đánh giá logic planner dưới đây không có nghĩa giao diện bản đồ hoàn chỉnh. Không sửa lỗi trong đợt kiểm thử này để giữ đúng hiện trạng đã đánh giá.

### T01 — Hai bãi biển trong một ngày, cả hai bắt buộc

**Người demo thao tác:** giờ 08:00–18:00; tọa độ (16.0544, 108.2022); 2/2 điểm bắt buộc; giữ thời lượng tham khảo theo từng phương án; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Có lịch ghé đủ hai điểm và quay về trong 08:00–18:00.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thuận đường | 08:00–12:28 | 2/2 | 2/2 | 17.17 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 2 | Ghé nhiều hơn | 08:00–10:43 | 2/2 | 2/2 | 17.17 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 3 | Thư thả | 08:00–15:28 | 2/2 | 2/2 | 17.17 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 10:18 | 120 |
| Bãi tắm Phạm Văn Đồng | 10:40 | 12:10 | 90 |

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời lượng tham khảo, có thể điều chỉnh. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: LOGIC LỊCH HỢP LÝ; WEB CÒN LỖI.** Ba phương án ghé đủ hai điểm. Thuận đường dùng 120 phút tại Mỹ Khê và 90 phút tại Phạm Văn Đồng, về 12:28. Ghé nhiều hơn dùng 60/45 phút, về 10:43; Thong thả dùng 240/150 phút, về 15:28. Tên phương án nói nhịp tham quan, không cam kết khác số điểm khi người dùng chỉ chọn hai điểm. Cả ba cùng đường ô tô khoảng 17,17 phút, thời gian tiếp cận hai chiều là phần cộng riêng.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T01.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T01.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T01.json)

### T02 — Chỉ còn một giờ nhưng vẫn yêu cầu hai biển

**Người demo thao tác:** giờ 08:00–09:00; tọa độ (16.0544, 108.2022); 2/2 điểm bắt buộc; giữ thời lượng tham khảo theo từng phương án; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Không âm thầm bỏ điểm bắt buộc hoặc kéo dài; điều chỉnh phải xin xác nhận.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Ghé nhiều hơn | 08:00–10:43 | 2/2 | 2/2 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 2 | Ghé nhiều hơn | 06:00–08:43 | 2/2 | 2/2 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 3 | Ghé nhiều hơn | 05:00–07:43 | 2/2 | 2/2 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 09:18 | 60 |
| Bãi tắm Phạm Văn Đồng | 09:40 | 10:25 | 45 |

**Điều chỉnh được thông báo:** Đề xuất đi lúc 08:00, về lúc 10:43 (yêu cầu 08:00–09:00).

**Hộp xác nhận đã mở:** Đề xuất đi lúc 08:00, về lúc 10:43 (yêu cầu 08:00–09:00).

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời lượng tham khảo, có thể điều chỉnh. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: RÀNG BUỘC ĐƯỢC CÔNG KHAI; WEB CÒN LỖI.** Không có lịch đủ hai điểm trong đúng 08:00–09:00 với thời lượng tham khảo. Hệ thống đề xuất 08:00–10:43 hoặc xuất phát sớm 06:00/05:00; cả ba cần xác nhận. Đã bấm Quay lại và kiểm tra chưa chọn nhầm, sau đó mở lại và Chấp nhận điều chỉnh. Đề xuất không đồng nghĩa đã đáp ứng yêu cầu ban đầu.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T02.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T02.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T02.json)

### T03 — Một giờ, mỗi bãi biển chỉ dừng 10 phút

**Người demo thao tác:** giờ 08:00–09:00; tọa độ (16.0544, 108.2022); 2/2 điểm bắt buộc; thời lượng mỗi điểm 10 phút; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Giữ đúng 10 phút; kiểm tra việc rút thời lượng có giúp đủ hai điểm không.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thuận đường | 08:00–08:44 | 1/2 | 1/2 | 13.69 | Có | Bãi biển Mỹ Khê |
| 2 | Thuận đường | 08:00–09:18 | 2/2 | 2/2 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 08:28 | 10 |

**Điều chỉnh được thông báo:** Chưa ghé được điểm bắt buộc: Bãi tắm Phạm Văn Đồng

**Điểm chưa xếp ở thẻ đầu:** Bãi tắm Phạm Văn Đồng: Chưa xếp được trong khung giờ, giờ mở cửa và thứ tự này; tìm kiếm có giới hạn.

**Hộp xác nhận đã mở:** Chưa ghé được điểm bắt buộc: Bãi tắm Phạm Văn Đồng

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: ĐÁNH ĐỔI RÕ; WEB CÒN LỖI.** Hai lần ghé 10 phút vẫn cần 20 phút tham quan + 40 phút tiếp cận vào/ra + khoảng 17,17 phút lái xe, tổng khoảng 77,17 phút. Một phương án ghé Mỹ Khê và về 08:44, thiếu một điểm bắt buộc; phương án đủ hai điểm về 09:18. Cả hai phải xác nhận đúng loại điều chỉnh. Không kết luận hệ thống tính sai chỉ vì 10+10 nhỏ hơn 60.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T03.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T03.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T03.json)

### T04 — Một giờ, ưu tiên bắt buộc Mỹ Khê, điểm kia tùy chọn

**Người demo thao tác:** giờ 08:00–09:00; tọa độ (16.0544, 108.2022); 1/2 điểm bắt buộc; giữ thời lượng tham khảo theo từng phương án; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Tôn trọng điểm bắt buộc, công khai điểm tùy chọn chưa xếp được.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Ghé nhiều hơn | 08:00–10:43 | 2/2 | 1/1 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 2 | Ghé nhiều hơn | 06:00–08:43 | 2/2 | 1/1 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 3 | Ghé nhiều hơn | 05:00–07:43 | 2/2 | 1/1 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 09:18 | 60 |
| Bãi tắm Phạm Văn Đồng | 09:40 | 10:25 | 45 |

**Điều chỉnh được thông báo:** Đề xuất đi lúc 08:00, về lúc 10:43 (yêu cầu 08:00–09:00).

**Hộp xác nhận đã mở:** Đề xuất đi lúc 08:00, về lúc 10:43 (yêu cầu 08:00–09:00).

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời lượng tham khảo, có thể điều chỉnh. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: HỢP LÝ NHƯNG CHƯA GIẢI QUYẾT KHUNG GIỜ.** Chỉ bỏ bắt buộc Phạm Văn Đồng, vẫn để thời lượng tham khảo. Riêng Mỹ Khê theo nhịp ngắn đã cần 60 phút tham quan + thời gian vào/ra và lái xe, nên chưa thể vừa 1 giờ. Kết quả vẫn đề xuất đổi giờ. Ca T10 mới cho thấy bỏ bắt buộc kết hợp thời lượng 10 phút tạo được phương án đúng khung.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T04.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T04.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T04.json)

### T05 — Đổi điểm xuất phát sang gần Mỹ Khê

**Người demo thao tác:** giờ 08:00–18:00; tọa độ (16.063, 108.245); 2/2 điểm bắt buộc; giữ thời lượng tham khảo theo từng phương án; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Đường đi và thời gian lái xe thay đổi theo điểm xuất phát.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thuận đường | 08:00–12:18 | 2/2 | 2/2 | 7.86 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 2 | Ghé nhiều hơn | 08:00–10:33 | 2/2 | 2/2 | 7.86 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 3 | Thư thả | 08:00–15:18 | 2/2 | 2/2 | 7.86 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:14 | 10:14 | 120 |
| Bãi tắm Phạm Văn Đồng | 10:36 | 12:06 | 90 |

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời lượng tham khảo, có thể điều chỉnh. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: THAY ĐỔI ĐÚNG THEO TỌA ĐỘ; WEB CÒN LỖI.** Cùng hai điểm và nhịp tham quan nhưng xuất phát gần Mỹ Khê: lái xe giảm từ khoảng 17,17 xuống 7,86 phút, Thuận đường về 12:18 thay vì 12:28. Dữ liệu tuyến thật được vẽ lại. Khoảng cách gần không loại bỏ 40 phút tiếp cận đang nằm trong dữ liệu hai địa điểm.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T05.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T05.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T05.json)

### T06 — Muốn ghé Phạm Văn Đồng trước Mỹ Khê

**Người demo thao tác:** giờ 08:00–18:00; tọa độ (16.0544, 108.2022); 2/2 điểm bắt buộc; giữ thời lượng tham khảo theo từng phương án; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt; nhấn ↑ ở Phạm Văn Đồng để ghé trước Mỹ Khê. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Các phương án giữ thứ tự chỉnh tay; công khai ảnh hưởng đến thời gian.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thuận đường | 08:00–12:29 | 2/2 | 2/2 | 18.73 | Không | Bãi tắm Phạm Văn Đồng → Bãi biển Mỹ Khê |
| 2 | Ghé nhiều hơn | 08:00–10:44 | 2/2 | 2/2 | 18.73 | Không | Bãi tắm Phạm Văn Đồng → Bãi biển Mỹ Khê |
| 3 | Thư thả | 08:00–15:29 | 2/2 | 2/2 | 18.73 | Không | Bãi tắm Phạm Văn Đồng → Bãi biển Mỹ Khê |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi tắm Phạm Văn Đồng | 08:18 | 09:48 | 90 |
| Bãi biển Mỹ Khê | 10:13 | 12:13 | 120 |

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời lượng tham khảo, có thể điều chỉnh. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: GIỮ ĐÚNG THỨ TỰ; WEB CÒN LỖI.** Nhấn đưa Phạm Văn Đồng lên trước khiến cả ba phương án giữ Phạm Văn Đồng → Mỹ Khê. Thời gian lái xe tăng từ khoảng 17,17 lên 18,73 phút và Thuận đường về 12:29. Đây là tác động của thứ tự và mạng đường ô tô, không nhất thiết đối xứng. Không khẳng định thứ tự ban đầu tối ưu toàn cục vì planner tìm kiếm có giới hạn.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T06.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T06.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T06.json)

### T07 — Muốn nghỉ ăn và uống cà phê trong ngày

**Người demo thao tác:** giờ 08:00–18:00; tọa độ (16.0544, 108.2022); 2/2 điểm bắt buộc; giữ thời lượng tham khảo theo từng phương án; ăn=bật; nghỉ=bật; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Lịch có khối nghỉ phù hợp; không giả định một nhà hàng đã được đặt hoặc chọn.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thuận đường | 08:00–13:33 | 2/2 | 2/2 | 17.17 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 2 | Ghé nhiều hơn | 08:00–10:43 | 2/2 | 2/2 | 17.17 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |
| 3 | Thư thả | 08:00–16:33 | 2/2 | 2/2 | 17.17 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 10:18 | 120 |
| Nghỉ tự túc tại điểm dừng | 10:28 | 10:48 | 20 |
| Bãi tắm Phạm Văn Đồng | 11:00 | 12:30 | 90 |
| Bữa trưa tự túc tại điểm dừng | 12:40 | 13:25 | 45 |

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời lượng tham khảo, có thể điều chỉnh. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: CÓ NGHỈ, CHƯA ĐỒNG ĐỀU MỌI PHƯƠNG ÁN.** Thuận đường thêm nghỉ 10:28–10:48 và ăn trưa 12:40–13:25, về 13:33 thay vì 12:28. Đó là nghỉ/ăn tự túc tại điểm dừng, không phải đã chọn một quán cụ thể. Phương án Ghé nhiều hơn kết thúc 10:43 không chèn khối ăn/nghỉ; các lựa chọn này là linh hoạt, không bảo đảm xuất hiện trong mọi phương án. Cần đọc từng timeline.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T07.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T07.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T07.json)

### T08 — Hai biển, bật tự bổ sung điểm tham quan

**Người demo thao tác:** giờ 08:00–18:00; tọa độ (16.0544, 108.2022); 2/2 điểm bắt buộc; giữ thời lượng tham khảo theo từng phương án; ăn=tắt; nghỉ=tắt; tự bổ sung=bật. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Tối đa ba điểm thêm, công khai danh sách và vẫn giữ các điểm bắt buộc.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thư thả | 08:00–16:49 | 2/2 | 2/2 | 18.33 | Không | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng → Cầu Trần Thị Lý |
| 2 | Thuận đường | 08:00–15:33 | 2/2 | 2/2 | 22.66 | Không | Trình cà phê → Đường hoa Bạch Đằng → Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng → Cầu Trần Thị Lý |
| 3 | Ghé nhiều hơn | 08:00–12:53 | 2/2 | 2/2 | 22.66 | Không | Trình cà phê → Đường hoa Bạch Đằng → Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng → Cầu Trần Thị Lý |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 12:18 | 240 |
| Bãi tắm Phạm Văn Đồng | 12:40 | 15:10 | 150 |
| Cầu Trần Thị Lý | 15:35 | 16:35 | 60 |

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời lượng tham khảo, có thể điều chỉnh. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: BỔ SUNG CÓ ÍCH; CẦN NGƯỜI DÙNG CHỌN.** Tự thêm tối đa ba POI. Thuận đường thêm Trình cà phê, Đường hoa Bạch Đằng, Cầu Trần Thị Lý; giữ hai bãi biển, về 15:33. Phương án đầu tiên lại là Thong thả: thêm chỉ Cầu Trần Thị Lý và về 16:49. Thứ tự thẻ không có nghĩa phương án đầu ghé nhiều nhất. Auto-add trong Lịch trình không kế thừa bộ lọc Tham quan và ngoài trời của trang Gợi ý, nên có thể thêm cà phê.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T08.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T08.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T08.json)

### T09 — Muốn ở mỗi biển 6 giờ trong ngày 10 giờ

**Người demo thao tác:** giờ 08:00–18:00; tọa độ (16.0544, 108.2022); 2/2 điểm bắt buộc; thời lượng mỗi điểm 360 phút; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Không thể ghé đủ trong khung ban đầu; phải báo thiếu hoặc đề xuất có xác nhận.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thuận đường | 08:00–14:34 | 1/2 | 1/2 | 13.69 | Có | Bãi biển Mỹ Khê |
| 2 | Thuận đường | 08:00–20:58 | 2/2 | 2/2 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 14:18 | 360 |

**Điều chỉnh được thông báo:** Chưa ghé được điểm bắt buộc: Bãi tắm Phạm Văn Đồng

**Điểm chưa xếp ở thẻ đầu:** Bãi tắm Phạm Văn Đồng: Chưa xếp được trong khung giờ, giờ mở cửa và thứ tự này; tìm kiếm có giới hạn.

**Hộp xác nhận đã mở:** Chưa ghé được điểm bắt buộc: Bãi tắm Phạm Văn Đồng

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: KHÔNG ÂM THẦM CẮT THỜI LƯỢNG; WEB CÒN LỖI.** Yêu cầu 6 giờ mỗi biển vượt khung 10 giờ ngay từ thời gian ghé. Hệ thống giữ đúng 360 phút: chọn một biển, về 14:34 và báo thiếu điểm bắt buộc; hoặc đủ hai biển, về 20:58 và đề nghị kéo dài. Cả hai cần xác nhận. Sai số 360,0000000000001 trong JSON là số thực, không phải thay đổi thời lượng.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T09.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T09.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T09.json)

### T10 — Một giờ, dừng mỗi nơi 10 phút, chỉ Mỹ Khê bắt buộc

**Người demo thao tác:** giờ 08:00–09:00; tọa độ (16.0544, 108.2022); 1/2 điểm bắt buộc; thời lượng mỗi điểm 10 phút; ăn=tắt; nghỉ=tắt; tự bổ sung=tắt. Bấm Xem lịch gợi ý.

**Kỳ vọng trước khi chạy:** Nếu chỉ ghé Mỹ Khê thì phải công khai bỏ Phạm Văn Đồng; không cần xác nhận bỏ điểm bắt buộc vì đã đổi thành tùy chọn.

| Thẻ | Phương án | Đi–về | Điểm chọn | Bắt buộc | Lái xe (phút) | Cần xác nhận | Thứ tự ghé |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Thuận đường | 08:00–08:44 | 1/2 | 1/1 | 13.69 | Không | Bãi biển Mỹ Khê |
| 2 | Thuận đường | 08:00–09:18 | 2/2 | 1/1 | 17.17 | Có | Bãi biển Mỹ Khê → Bãi tắm Phạm Văn Đồng |

**Các mốc của thẻ đầu đã chọn trên web:**

| Hoạt động | Từ | Đến | Phút |
| --- | --- | --- | --- |
| Bãi biển Mỹ Khê | 08:18 | 08:28 | 10 |

**Điểm chưa xếp ở thẻ đầu:** Bãi tắm Phạm Văn Đồng: Chưa xếp được trong khung giờ, giờ mở cửa và thứ tự này; tìm kiếm có giới hạn.

**Giới hạn hiển thị trong lịch:** Cần kiểm tra giờ trước khi đi. Điểm tiếp cận chưa xác minh; thời gian vào/ra có thể cần bổ sung. Thời gian OSRM không có giao thông trực tiếp.

**Đánh giá: PHÂN BIỆT ĐÚNG BẮT BUỘC VÀ TÙY CHỌN.** So với T03 chỉ bỏ bắt buộc Phạm Văn Đồng. Phương án ghé Mỹ Khê 10 phút, về 08:44, đạt 1/1 điểm bắt buộc trong giờ nên không cần xác nhận điều chỉnh; danh sách chưa xếp công khai Phạm Văn Đồng. Phương án ghé đủ hai nơi vẫn về 09:18 và cần xác nhận. Đây là ca minh họa rõ nhất tác dụng điểm bắt buộc.

[Ảnh màn hình](../artifacts/danang-demo/20260919-231136/T10.png) · [Chữ hiển thị](../artifacts/danang-demo/20260919-231136/T10.txt) · [Request/response đầy đủ](../artifacts/danang-demo/20260919-231136/T10.json)

## 6. Lỗi và điểm yếu cần nói thẳng

| Mức | Phát hiện | Bằng chứng | Hướng cải thiện (chưa triển khai) |
| --- | --- | --- | --- |
| Cao | Không hiểu phủ định | R11/R12 cùng 10 POI, cùng thứ tự | Có danh mục không muốn; phân tích phủ định hoặc báo chưa hỗ trợ |
| Cao | Không diễn đạt được chỉ vùng Đà Nẵng | R19 có 3 POI region=hoi_an | Tách vùng du lịch và tỉnh/thành hành chính; lọc đa giác theo vùng yêu cầu |
| Cao | Lỗi tải POI bản đồ trang Lịch trình | 10/10 ca T: exploreFilters undefined, mapFeatures=0 | Đặt hàm tạo bộ lọc vào mã dùng chung hoặc tách rõ theo trang |
| Vừa | Xung đột bộ lọc với sở thích không được cảnh báo | R13 tìm cafe trả công viên/biển | Báo bộ lọc đang loại cà phê; đề nghị đổi nhóm trước khi gợi ý |
| Vừa | Điền đủ Top-K dù khớp sở thích bằng 0 | R08 Chợ Phước Mỹ; R10 hai công viên | Ngưỡng relevance tối thiểu; cho phép ít kết quả; tách gợi ý mở rộng |
| Vừa | Ưu tiên loại hình chưa đủ rõ với người muốn chỉ biển | R06 chỉ 2/10 beach | Tách lọc bắt buộc và ưu tiên mềm; giải thích rõ khi chọn loại hình |
| Vừa | Taxonomy có dấu hiệu chưa chính xác | Funny Games Vincom được gán park và thiên nhiên | Kiểm duyệt POI trọng tâm, không suy toàn bộ tag từ category đáng ngờ |
| Vừa | Bằng chứng rating/giờ/cổng vào còn thiếu | R14 có 9/10 chất lượng trung tính; lịch cảnh báo cổng vào chưa xác minh | Xác minh dữ liệu trước khi đánh giá trải nghiệm thực tế |
| Vừa | Điều kiện ăn/nghỉ chỉ mềm | T07 có thẻ không có khối nghỉ | Hiển thị đã/không đáp ứng từng tùy chọn ngay trên thẻ |

Vị trí nguồn giải thích kết quả: [recommendations.py](../where2go/v2/recommendations.py) (PRESETS, lọc ngày/bán kính, một thước đo di chuyển cho cả pool, TOPSIS, không có ngưỡng điểm sở thích tối thiểu); [ranking.py](../where2go/v2/ranking.py) (preference_components: 0,7 × taxonomy + 0,3 × cosine); [discovery.py](../where2go/v2/discovery.py) (EXCLUDED và region_for); [hours.py](../where2go/v2/hours.py) (null khác đóng cửa); [trips.py](../where2go/v2/trips.py) (thời gian tiếp cận hai chiều, lịch, điều chỉnh); [map.js](../web/map.js) (loadMapPois gọi exploreFilters), [explore.js](../web/explore.js) (nơi định nghĩa hàm), [itinerary.html](../web/itinerary.html) (trang lịch không nạp explore.js).

[Chi tiết POI đã đọc từ API](../artifacts/danang-demo/detail-evidence.json) ghi lịch đóng thứ Hai của Ho Chi Minh Museum và tag/loại hình Funny Games. Không xác minh ngoài thực địa; dữ liệu bản đồ nguồn cũng không được coi là tuyệt đối chính xác.

## 7. Một bài demo 12–15 phút có thể trình bày ngay

| Thời gian | Thao tác | Lời nói gợi ý |
| --- | --- | --- |
| 0:00–2:00 | R02 → R03 | Tôi muốn thiên nhiên nhưng ngại đi xa. Chuyển Đi gần làm Công viên 29 tháng 3 lên đầu. Cùng tập 10 điểm vẫn có thể khác thứ tự. |
| 2:00–3:30 | R05 → R15 | Tôi đổi sang văn hóa; các bảo tàng lên đầu. Đổi thứ Hai thì nơi có dữ liệu đóng cửa bị loại; nơi thiếu giờ vẫn phải kiểm tra. |
| 3:30–5:00 | R07 → R08 | Khách ở gần Mỹ Khê, chỉ muốn trong 1 km. Chỉ có 4 điểm; hệ thống không tự lấy điểm xa cho đủ 10. Chợ cuối danh sách là hạn chế relevance. |
| 5:00–6:30 | R11 → R12 | Đây là phép thử khó: thêm không thích mà danh sách biển vẫn giữ nguyên. Hệ thống hiện chưa hiểu phủ định. |
| 6:30–8:00 | R13 → R14 | Tìm cà phê nhưng bộ lọc đang loại cà phê. Chuyển Tất cả loại hình thì quán xuất hiện; giao diện cần cảnh báo xung đột này. |
| 8:00–10:00 | Chọn hai biển ở Khám phá → T01 | Các lựa chọn được chuyển sang lịch. Xem đúng thời lượng ghé, tiếp cận, đi đường và quay về; đây là đường OSRM, chưa tính giao thông. |
| 10:00–12:00 | T02 → T03 → T10 | Một giờ không đủ. Giảm mỗi nơi còn 10 phút vẫn cần khoảng 77 phút nếu ghé cả hai. Cho điểm thứ hai tùy chọn thì Mỹ Khê về 08:44 là phương án phù hợp. |
| 12:00–13:30 | T05 hoặc T06 | Đổi điểm xuất phát giảm thời gian đi xe; ép thứ tự ghé làm thời gian tăng. Ranking gợi ý và thứ tự tuyến là hai quyết định khác nhau. |
| 13:30–15:00 | T08 và kết luận | Tự bổ sung có thể thêm quán cà phê, đường hoa và cầu. Tôi đọc từng phương án, không coi thẻ đầu là tối ưu toàn cục. Lỗi bản đồ hiện tại cần sửa trước demo chính thức. |

R19 chỉ cần trình bày trong phần hạn chế phạm vi; không dùng các điểm Hội An của ca đó làm điểm đến trong bài demo. Nếu chỉ có 5 phút, dùng R02→R03, R05, R12, T01→T02→T10.

## 8. Chạy lại và tìm bằng chứng

Tại thư mục gốc dự án, nếu web chưa chạy:

```powershell
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Ở terminal khác, chạy bộ demo:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/demo_danang.py --url http://127.0.0.1:8000
# Chỉ lặp một cặp để kiểm tra nhanh:
.venv\Scripts\python.exe -X utf8 scripts/demo_danang.py --only R11,R12
```

Cần Playwright và Chromium trong môi trường. Nếu thiếu: `.venv\Scripts\python.exe -m pip install playwright`, sau đó `.venv\Scripts\python.exe -m playwright install chromium`. OSRM local phải hoạt động nếu muốn lặp nhóm lịch. Hướng dẫn runtime: [huong_dan_chay.md](huong_dan_chay.md).

Bằng chứng chính ở [`artifacts/danang-demo/20260919-231136`](../artifacts/danang-demo/20260919-231136/): mỗi mã có PNG toàn trang, TXT chữ trên web, JSON request/response đầy đủ, và ảnh hộp xác nhận khi có. `results.json` trong thư mục đó giữ SHA-256 của bằng chứng. [Bản tổng hợp máy đọc](../data/reports/demo_danang/results.json) chứa đủ Top-10, criteria, lý do, cảnh báo, phương án, thời gian và kết quả kiểm tra.

Mỗi lần chạy tạo thư mục thời gian mới; lần chạy đầy đủ cập nhật bản tổng hợp JSON. Báo cáo Markdown này là nhận xét đóng băng của lần chạy ghi đầu tài liệu, không tự cập nhật khi catalog hoặc mã thay đổi. Các lần dò trước đó nằm riêng trong artifacts; không trộn số liệu bán kính 30 km của lần dò với bộ demo 15 km này.

**Đã kiểm tra trong đợt này:** hành trình desktop Chromium, API thật, OSRM thật, ảnh/DOM, phạm vi theo đa giác dự án, thời lượng, thứ tự, hộp xác nhận, lint script và tính toàn vẹn bằng chứng. **Chưa kiểm tra trong đợt này:** đi thực địa, độ chính xác thời gian giao thông, khảo sát người dùng, accessibility đầy đủ, mobile đầy đủ, dữ liệu rating/giờ của từng POI với đơn vị vận hành. Không lấy số unit test lịch sử làm kết quả của đợt demo này.
