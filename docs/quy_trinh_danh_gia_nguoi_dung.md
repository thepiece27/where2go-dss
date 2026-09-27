# Quy trình đánh giá gợi ý với người dùng

Trạng thái ngày 25/09/2026: **NOT RUN**. Tài liệu này định nghĩa cách thu bằng chứng còn thiếu; không thay thế người tham gia thật và không cho phép điền nhãn từ score của hệ thống.

## 1. Câu hỏi và giả thuyết

Câu hỏi chính: với cùng yêu cầu và tập POI hợp lệ, kết hợp sở thích khai báo, rating tham khảo và chi phí địa lý có giúp Top-K phù hợp hơn sắp theo độ gần/rating/taxonomy/TF-IDF hay không?

- H1: TOPSIS có NDCG@10 cao hơn `nearby` và `quality`.
- H2: TOPSIS có lợi ích thực tế so với `weighted_sum`, không chỉ khác thứ tự.
- H3: bỏ rating (`topsis_no_quality`) không làm giảm chất lượng khi rating quá thưa.
- Điều kiện an toàn: tỷ lệ vi phạm loại trừ, “chỉ tìm” và giờ bắt buộc phải bằng 0.

Không đặt giả thuyết sau khi xem nhãn. Nếu dùng holdout để chỉnh taxonomy, preset hoặc code, phải tạo tập đánh giá mới.

## 2. Đối tượng và đơn vị đánh giá

Tuyển người có nhu cầu du lịch tự túc tại Hà Nội hoặc Đà Nẵng–Hội An. Ghi tiêu chí tuyển, số người mời/tham gia/bỏ dở và mức quen thuộc địa phương. Không thu dữ liệu định danh không cần thiết.

Đơn vị bootstrap và so sánh là **người × kịch bản**, không phải từng POI trong cùng danh sách. Pilot nội bộ phải báo riêng với đánh giá độc lập.

## 3. Tài liệu cố định trước khi chấm

1. Đóng băng snapshot `v2-c3ad315d02c5356a`, policy `poi-recommendation-3.0`, file kịch bản và mode khoảng cách/routing.
2. Chạy evaluator một lần; lưu `evaluation.json`, `grading_template.csv` và `grading_manifest.json` cùng nhau.
3. Kiểm tra hash trong manifest. Đợt hiện tại có hash evaluation `a27c374453b72da5b3c14e752ca7f4ccd9542871e0a4b82fc1bce8c7964aae2b`.
4. Không cho người chấm xem tên phương pháp, score, rank theo từng phương pháp hoặc file `evaluation.json`.

Pool chấm là hợp Top-10 của bảy phương pháp, khử trùng và xáo trộn theo seed cố định. Mọi POI trong pool của một kịch bản phải được chấm; nhãn trống không được coi là không liên quan.

## 4. Rubric POI 0–3

| Điểm | Diễn giải |
|---:|---|
| 0 | Không phù hợp hoặc vi phạm yêu cầu của kịch bản |
| 1 | Liên quan yếu; chỉ cân nhắc khi thiếu lựa chọn tốt hơn |
| 2 | Phù hợp và có thể chọn cho chuyến đi |
| 3 | Rất phù hợp; ưu tiên cao trong bối cảnh này |

Người chấm đọc cùng mô tả, loại hình, khoảng cách và nguồn cho mọi phương pháp. Nếu thiếu dữ liệu để phán đoán, ghi chú “không đủ thông tin”; không suy từ điểm tự động. Relevance nhị phân dùng grade ≥2 chỉ khi tính Precision@K.

## 5. Quy trình phiên đánh giá

1. Giải thích mục tiêu và xin đồng ý tham gia; không giải thích phương pháp nào đang được kiểm tra.
2. Cho một kịch bản luyện tập không nằm trong tập báo cáo.
3. Mỗi người chấm các kịch bản theo thứ tự ngẫu nhiên; thứ tự POI trong từng pool cũng ngẫu nhiên.
4. Ghi thời gian hoàn thành, câu hỏi làm rõ và lý do bỏ qua; không hướng người chấm tới một category.
5. Sau chấm POI, cho so sánh danh sách A/B đã ẩn phương pháp và hỏi danh sách nào hữu ích hơn, hoặc hòa.
6. Với luồng sản phẩm, đo thêm tỷ lệ chấp nhận ít nhất một POI, thời gian tới lựa chọn đầu tiên và lỗi thao tác.

## 6. Tính chỉ số

```powershell
if (-not (Test-Path data\manual\recommendation_grades.csv)) {
    Copy-Item data\reports\recommendations\grading_template.csv data\manual\recommendation_grades.csv
}
.venv\Scripts\python.exe -X utf8 scripts\evaluate_recommendations.py --grades data\manual\recommendation_grades.csv
.venv\Scripts\python.exe -X utf8 scripts\run_analysis.py
```

Báo Precision@5/10, NDCG@5/10, tỷ lệ vi phạm điều kiện, tỷ lệ không kết quả, lựa chọn A/B và thời gian thao tác. Dùng khoảng tin cậy bootstrap 95% theo người × kịch bản và hiệu số ghép cặp. Báo cả kích thước hiệu ứng; không chỉ báo p-value.

## 7. Quy tắc kết luận

- Chỉ giữ tuyên bố “TOPSIS tốt hơn” khi có cải thiện có ý nghĩa thực tế và khoảng tin cậy không quá rộng trên tập chưa dùng để chỉnh.
- Nếu TOPSIS không hơn `weighted_sum` một cách đáng tin cậy, ưu tiên phương pháp đơn giản hơn.
- Nếu `topsis_no_quality` ngang hoặc tốt hơn, bỏ rating khỏi xếp hạng đến khi dữ liệu đủ hơn.
- Kết quả pilot nội bộ không được gọi là đánh giá người dùng độc lập.
- Test phần mềm PASS, shortlist recall và danh sách thay đổi không phải accuracy/relevance.

## 8. Đánh giá lịch trình riêng

Với phương án lịch đã chọn, chấm 1–5 cho mức hợp lý của thứ tự, thời lượng, thời gian đệm và khả năng thực hiện. Ghi riêng vi phạm giờ mở cửa, chặng quay về, điểm bắt buộc và sai số thời gian thực tế. Mọi phương án hiện mang nhãn `tham_khao`; OSRM không có giao thông trực tiếp và thời lượng chưa xác minh thực địa.
