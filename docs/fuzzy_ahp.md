# Phương pháp xếp hạng và lập lịch Where2Go DSS v2

Tài liệu này mô tả `where2go/v2/ranking.py`, `where2go/v2/planner.py` và hợp đồng trong `where2go/v2/models.py`.

**Phân biệt hai luồng kể từ 18/09/2026:** phần lọc/shortlist/seed và planner bên dưới mô tả endpoint nghiên cứu `/api/v2/itineraries`. Giao diện người dùng dùng `/api/v2/trip-suggestions` trong `trips.py`: tối đa 12 điểm do người dùng chọn, beam search, ba hồ sơ thời lượng, không dùng điểm TOPSIS để loại điểm đã chọn. Fuzzy AHP/TOPSIS với trọng số thiết kế vẫn được dùng tại `/api/v2/trip-recommendations` để xếp hạng đề xuất bổ sung có đường đi; người dùng thông thường không nhập so sánh cặp. Danh sách landmark biên tập tách khỏi điểm xếp hạng. Khi không có routing, gợi ý theo vị trí được ghi rõ và không giả thời gian lái xe. Xem [thuật toán và hợp đồng mới](trai_nghiem_lua_chon_lich_trinh.md).

## 1. Tập ứng viên

Planner lọc trước theo trạng thái dữ liệu, địa phương, bán kính, category bị loại, quan hệ cha-con và điểm tiếp cận. Khoảng cách thẳng chỉ dùng tạo shortlist. Khả năng đi/về và thời gian lái xe lấy từ OSRM Table; cạnh `null` hoặc snap quá xa bị loại.

Shortlist tối đa 40 điểm tham quan và 20 điểm ăn/nghỉ. Tập ứng viên cố định được dùng cho các phương pháp `nearby`, `equal`, `crisp` và `fuzzy` trong evaluator.

## 2. Bốn tiêu chí

Thứ tự API cố định:

1. `preference_match`: benefit.
2. `place_quality`: benefit.
3. `drive_time`: cost, đơn vị giây.
4. `data_confidence`: benefit.

Điểm sở thích gồm 70% taxonomy/tag và 30% cosine TF-IDF trên tên, alias, mô tả có nguồn. Nếu không nhập sở thích/chủ đề, mọi ứng viên nhận 1 để tiêu chí này trung tính.

Rating hiệu chỉnh:

\[
Q=\frac{vR+mC}{v+m},\qquad m=50
\]

Trong đó `R` và `v` phải cùng quan sát/nhà cung cấp. Prior `C` lấy theo loại hình-thành phố nếu có ít nhất 10 quan sát, nếu không lùi về cùng loại rồi toàn nhà cung cấp. Thiếu rating nhận 0,5 trung tính; hệ thống không tạo rating giả.

Confidence là trung bình bốn thành phần nhị phân: đúng thực thể, access đã xác minh, giờ giải được cho ngày yêu cầu và hoạt động được kiểm tra trong 180 ngày. Đây là chỉ số bằng chứng, không phải xác suất đúng hay mức hấp dẫn.

## 3. AHP và Fuzzy AHP

Trọng số thiết kế mặc định:

```text
Sở thích        0,40
Chất lượng      0,30
Thời gian lái   0,20
Tin cậy         0,10
```

Sáu so sánh cặp thuộc `[1/9, 9]`. Ma trận reciprocal 4x4 được tạo theo thứ tự tiêu chí trên. Với giá trị riêng lớn nhất `lambda_max`:

\[
CI=\frac{\lambda_{max}-4}{3},\qquad CR=\frac{CI}{0,90}
\]

Request bị từ chối khi `CR > 0,1`.

Mỗi cặp có hệ số bất định `gamma_ij` trong `[1,2]`. Số mờ tam giác là `(a/gamma, a, a*gamma)`. Code tính geometric mean theo hàng cho lower/middle/upper, chuẩn hóa theo tổng đảo và giải mờ bằng trung bình ba thành phần.

Giới hạn cần công bố: khi sáu `gamma` giống nhau, ví dụ mặc định đều bằng 1,2, trọng số fuzzy bằng geometric-mean AHP crisp. Vì vậy nhãn “Fuzzy AHP” không chứng minh kết quả tốt hơn. Muốn mô hình hóa bất định thật cần thu độ bất định riêng từng phán đoán và đánh giá độc lập.

## 4. TOPSIS

Với ma trận quyết định `X`, chuẩn hóa vector từng cột:

\[
r_{ij}=\frac{x_{ij}}{\sqrt{\sum_k x_{kj}^2}},\quad v_{ij}=w_jr_{ij}
\]

Ideal tốt/xấu dùng max/min theo chiều benefit/cost. Điểm gần lý tưởng:

\[
C_i=\frac{D_i^-}{D_i^++D_i^-}
\]

Cột toàn 0 hoặc hằng không sinh NaN; trường hợp không phân biệt nhận 0,5. Hòa điểm được phá bằng canonical ID. Điểm TOPSIS chỉ có nghĩa tương đối trong cùng pool.

## 5. Planner

Planner dùng multi-start heuristic:

1. Xếp hạng ứng viên.
2. Thử tối đa ba seed hạng cao hoặc tập POI bắt buộc.
3. Chèn ứng viên vào mọi vị trí hợp lệ.
4. Chọn utility cao hơn, rồi thử thay điểm cục bộ tối đa ba vòng.
5. Gọi OSRM Route và mô phỏng lại toàn lịch bằng thời gian từng leg thực tế.

Utility cộng điểm xếp hạng, bonus đa dạng/chủ đề và trừ thời gian lái, chờ, thiếu confidence. Giới hạn điểm tham quan: nhanh 5, cân bằng 4, thư thả 3. Chế độ cân bằng tối đa hai POI cùng category. Điểm cha/con hoặc cùng cha không được chọn trùng trải nghiệm.

Mỗi lượt mô phỏng gồm thời gian lái xe, access, chờ mở cửa, tham quan, ăn/nghỉ, đường về và dự phòng. Dự phòng là 10% thời gian lái, tối thiểu 15 và tối đa 45 phút. Planner không tự rút duration để nhét thêm điểm.

Kết quả `ready` chỉ khi mọi giờ/duration/access dùng trong lịch đủ điều kiện hiện tại; còn dữ liệu ước lượng là `provisional`. `routing_unavailable` được trả khi OSRM lỗi hoặc lệch snapshot; không thay bằng khoảng cách chim bay.
