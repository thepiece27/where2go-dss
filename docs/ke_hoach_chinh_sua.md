# Kế hoạch chỉnh sửa Where2Go theo nhu cầu người dùng

Ngày: 25/09/2026. Mục tiêu: **hỗ trợ khách du lịch lựa chọn điểm tham quan theo sở thích khai báo và điều kiện chuyến đi**, trọng tâm Đà Nẵng–Hội An. Hà Nội và dữ liệu toàn quốc vẫn được giữ để tra cứu/đối chiếu. Chưa đặt mục tiêu học hành vi dài hạn.

## 1. Quyết định về phạm vi

Người dùng cần biết: nơi nào đáp ứng yêu cầu, vì sao nên cân nhắc, dữ liệu nào còn thiếu, và các nơi đã chọn có thể ghé trong thời gian dự kiến không.

Luồng đích: **khai báo nhu cầu → kiểm tra điều kiện bắt buộc → tìm ứng viên có bằng chứng phù hợp → xếp hạng theo ưu tiên → người dùng chọn → lập lịch tham khảo**.

| Thành phần | Quyết định |
|---|---|
| Catalog, canonical ID, provenance, bản đồ và khám phá | Giữ; ưu tiên sửa nội dung tập trọng tâm thay vì tăng số bản ghi |
| Taxonomy và TF-IDF | Giữ làm nền đơn giản, sửa biểu diễn khái niệm và đo đóng góp riêng |
| TOPSIS | Giữ làm phương pháp đang phục vụ; so với tổng trọng số trước khi quyết định lâu dài |
| Trọng số preset | Dùng trực tiếp, công bố là chính sách thiết kế; không dựng ma trận AHP để tính lại chính chúng |
| AHP thường | Chỉ giữ ở API planner nghiên cứu có nhận so sánh cặp và kiểm tra CR |
| Nhánh trọng số tam giác, giải mờ và hệ số bất định | Loại khỏi mã, hợp đồng, thực nghiệm, notebook và tài liệu |
| Lập lịch, OSRM, thời lượng chỉnh tay, điểm bắt buộc | Giữ làm bước sau lựa chọn; phân biệt lịch ước lượng với lịch đã đủ bằng chứng |
| Mô hình hành vi, graph, chuỗi check-in | Chưa bổ sung khi chưa có dữ liệu và câu hỏi đánh giá phù hợp |

## 2. Đợt 1 — Đơn giản hóa và đồng bộ bằng chứng

**Trạng thái: đã hoàn tất.** Bản ghi riêng của đợt đơn giản hóa còn ở [simplification_verification.json](../data/reports/analysis/simplification_verification.json). Các số hiện hành sau khi triển khai tiếp được ghi ở `implementation_verification.json`; không dùng số đợt 1 để thay kết quả mới.

Phạm vi đã triển khai trong yêu cầu này:

- Loại nhánh trọng số đã bỏ ở cả lõi v1/v2, default của planner, request và evaluator; không giữ alias âm thầm chạy phương pháp khác.
- Luồng gợi ý dùng trọng số preset trực tiếp với TOPSIS, trả `weight_source` thay CR không có ý nghĩa với preset.
- API planner nghiên cứu chỉ nhận sáu so sánh cặp trong `ahp`, không còn trường `uncertainty`. Nhãn phương pháp nội bộ là `ahp` cho planner và `topsis` cho gợi ý; không giữ tên phương pháp cũ làm alias.
- Thêm baseline tổng trọng số cùng chuẩn hóa vector và cùng trọng số để phân biệt tác động của phép tổng hợp.
- Chạy lại đánh giá gợi ý theo chính sách `poi-recommendation-3.0`, đồng bộ bộ lọc mặc định với web. Giữ nhãn người chấm riêng, không đổi kết quả cũ thành kết quả của phương pháp mới.
- Cập nhật notebook, biểu đồ, báo cáo và slide. Dữ liệu nguồn được giữ nguyên. Kết quả planner lịch sử còn giữ phải có nhãn lịch sử, không coi là lần chạy lại hiện tại.
- Kiểm tra mã, request, xếp hạng, test hiện có, notebook và liên kết tài liệu.

Đợt này **chưa sửa cách hiểu phủ định, taxonomy, ngưỡng phù hợp hoặc chính sách rating thiếu**. Các vấn đề đó là phạm vi các đợt dưới đây; việc đơn giản hóa không được trình bày thành đã cải thiện relevance.

## 3. Đợt 2 — Làm rõ và thực thi yêu cầu người dùng

**Trạng thái: đã triển khai trong policy `poi-recommendation-3.0`.** API, form, nháp và evaluator dùng cùng các trường chủ đề trải nghiệm, văn bản tự do, loại hình ưu tiên/chỉ tìm/loại trừ, giờ đã ghi nhận và nới kết quả. Từ điển `poi-intent-1.0` trả lại cách hiểu; phủ định không hỗ trợ bị từ chối rõ ràng.

Thay đổi `RecommendationRequest`, form gợi ý, lưu nháp và evaluator trong cùng đợt:

- Tách **loại hình mong muốn**, **chỉ tìm những loại này**, **loại trừ**, **chủ đề trải nghiệm** và **ưu tiên xếp hạng**. Điều kiện loại trừ luôn thắng ưu tiên; đầu vào mâu thuẫn được báo rõ.
- Bán kính, phạm vi, đóng cửa đã biết, loại hình bắt buộc và loại trừ là bộ lọc trước xếp hạng. Giờ không biết vẫn là không biết; nếu người dùng yêu cầu có giờ được ghi nhận thì loại POI thiếu giờ.
- Chuẩn hóa nhu cầu bằng từ điển khái niệm và cụm từ tiếng Việt có phiên bản. Nhận các mẫu phủ định được hỗ trợ, hiển thị lại điều hệ thống đã hiểu. Câu vượt khả năng xử lý yêu cầu người dùng chọn bộ lọc rõ ràng, không âm thầm chuyển thành sở thích dương.
- Thêm tên loại hình và đồng nghĩa vào biểu diễn: `biển`, `bãi biển`, `ngắm biển` phải ánh xạ tới trải nghiệm biển. Tránh tính trùng các tags mặc định như hai bằng chứng độc lập.
- Không bổ sung địa điểm không khớp chỉ để đủ Top-10. Kết quả chính cần có bằng chứng phù hợp với ý định đã nhận diện; trả ít hơn K hoặc không có kết quả khi cần. Phương án nới điều kiện chỉ được áp dụng khi người dùng chọn.

Nghiệm thu: `không thích tâm linh` không gợi ý nơi thờ tự; `chỉ bảo tàng` không trả công viên; `ngắm cảnh biển` không được xem khớp chỉ vì tags có “ngắm cảnh”; `tâm linh` trong vùng không có điểm phù hợp trả thông báo trung thực; thay sở thích/bộ lọc cập nhật cả API và giao diện.

## 4. Đợt 3 — Chất lượng dữ liệu và tiêu chí xếp hạng

**Trạng thái phần mềm: đã triển khai; kiểm duyệt thực địa: NOT RUN.** Xếp hạng phục vụ còn ba tiêu chí sở thích–chất lượng–di chuyển; bằng chứng dữ liệu chỉ dùng cho cổng/cảnh báo. TF-IDF chỉ dùng tên/alias/mô tả nguồn, taxonomy không bị lặp vào corpus. Rating thiếu dùng prior nhóm có nhãn `observed=false`; website đơn lẻ không đủ qua cổng. Không sáng tác hoặc sửa dữ liệu nguồn trong đợt này.

- Rà soát tập tham quan trọng tâm theo địa bàn/nhóm trải nghiệm. Mỗi POI cần danh tính, tọa độ, loại hình và nội dung mô tả có nguồn đủ phân biệt với POI cùng nhóm. Không sáng tác thuộc tính để lấp chỗ thiếu.
- Tách **mức phù hợp**, **chi phí di chuyển**, **rating tham khảo** khỏi **mức đầy đủ của bằng chứng**. Đích thiết kế là ba tiêu chí lợi ích/chi phí; mức đầy đủ dùng cho điều kiện và cảnh báo, không gọi là độ hấp dẫn.
- Rating thiếu không được gán thành đánh giá xấu. Thử prior theo nhóm/provider có đủ mẫu, luôn giữ trạng thái không có rating; so với phương án bỏ tiêu chí rating. Chọn chính sách bằng đánh giá, không tự coi prior là giá trị đã quan sát.
- Cổng metadata cần phù hợp loại điểm: có website không đủ chứng minh một nơi hấp dẫn; điểm ngoài trời không có website cũng không tự động vô dụng.
- Đánh giá truy hồi riêng với xếp hạng. Với tập trọng tâm nhỏ, dùng toàn bộ ứng viên hợp lệ làm đối chứng để đo tổn thất của shortlist.
- Khi thiếu OSRM, dùng một thước đo địa lý có nhãn cho cả lượt. Không tạo thời gian lái xe giả; trường hợp cần tàu/đi bộ phải có chính sách riêng.

Nghiệm thu: thống kê độ phủ đúng mẫu số của từng nhóm; phiếu rà soát có nguồn; phân tích tác động của rating thiếu, bỏ confidence và thay shortlist; không có vi phạm điều kiện bắt buộc trong tập ca kiểm tra.

## 5. Đợt 4 — Đánh giá xem phương pháp nào đáng giữ

**Trạng thái thực nghiệm kỹ thuật: đã chạy; kết luận relevance: NOT GRADED.** Đã chạy 16 bối cảnh × 7 phương pháp = 112 lượt, tách taxonomy/TF-IDF, có tổng trọng số và ablation bỏ rating. Không có vi phạm điều kiện trong các ca; shortlist giữ trung bình 96,89% ứng viên và 100% Top-10 của pool đầy đủ. Chưa có nhãn người dùng nên chưa chọn TOPSIS là tốt hơn baseline.

Câu hỏi chính: **kết hợp sở thích khai báo và chi phí di chuyển có giúp lựa chọn điểm phù hợp hơn sắp theo độ gần hoặc rating không?**

So sánh cùng dữ liệu/ngữ cảnh: gần nhất, rating, taxonomy, văn bản, tổng trọng số và TOPSIS. Thử bỏ từng tín hiệu để hiểu đóng góp. Không tối ưu bằng chính nhãn sinh ra từ công thức chấm điểm.

Đóng băng dữ liệu, chính sách, bộ lọc, routing và tập yêu cầu. Thu đánh giá 0–3 từ người dùng mục tiêu trên pool gộp đã xáo trộn, ẩn phương pháp. Tập giữ lại để đánh giá không được dùng chọn trọng số; nếu đã xem để chỉnh thì tạo tập mới. Báo riêng pilot trong nhóm và người chấm độc lập.

Đo Precision/NDCG trên pool đã chấm đầy đủ, tỷ lệ vi phạm điều kiện, tỷ lệ không có kết quả, mức độ chấp nhận gợi ý và thời gian hoàn thành lựa chọn. Báo khoảng tin cậy theo người/kịch bản; không dùng số test phần mềm làm độ chính xác gợi ý. Thiếu nhãn tiếp tục ghi `NOT GRADED`.

Nếu TOPSIS không có lợi ích đáng tin cậy so với tổng trọng số, chọn phương pháp đơn giản hơn. Nếu giữ AHP trong nghiên cứu, phải thu so sánh cặp có nguồn và kiểm tra xem trọng số đó đem lại lợi ích gì.

## 6. Đợt 5 — Hoàn thiện luồng chọn và lịch trình

**Trạng thái phần mềm: đã triển khai và có kiểm thử; OSRM thực của đợt này: NOT RUN.** Lịch giữ điểm người dùng chọn, điểm bắt buộc, thứ tự/thời lượng chỉnh tay, thông báo điểm bỏ và thay đổi giờ. Mỗi phương án có `evidence.label=tham_khao`, danh sách giờ/access/thời lượng chưa đủ bằng chứng; giao diện ghi “Lịch tham khảo”.

Giữ quyền quyết định ở người dùng: xem lý do, dữ liệu thiếu, thêm/bỏ POI, điểm bắt buộc, sửa thời lượng và so sánh phương án. Lịch ưu tiên các nơi người dùng chọn, hiển thị rõ chỗ bỏ bớt, đổi giờ và khoảng đệm; không tự giảm thời lượng để nhét điểm.

Đánh giá riêng lịch trình: giờ mở cửa, đường về, điểm bắt buộc, mức thoải mái và sai số thời lượng. Kiểm tra desktop/mobile, nháp theo địa phương, quay lại từ bản đồ, yêu cầu chậm và phản hồi lỗi. Lịch chưa đủ thông tin vẫn phải có nhãn tham khảo.

## 7. Điều kiện coi việc chỉnh sửa hoàn tất

1. Mã, notebook, báo cáo và API dùng cùng phiên bản chính sách; bảng số cũ có nguồn và nhãn lịch sử.
2. Các ca phủ định, bắt buộc, không có kết quả và dữ liệu thiếu được kiểm tra từ request tới giao diện.
3. Có bằng chứng đánh giá phù hợp với mức kết luận: phần mềm chạy đúng khác với gợi ý được người dùng chấp nhận.
4. Báo cáo tập trung vào lựa chọn POI, nêu công thức thực sự dùng, lý do chọn và đối chứng; bản đồ/lịch trình là chức năng hỗ trợ.
5. Giữ khả năng tái lập dữ liệu và kết quả; không mất dữ liệu nguồn, curation, provenance hoặc nhãn người chấm.

Phần có thể thực hiện bằng mã và dữ liệu sẵn có của các đợt 2–5 đã hoàn tất. Hai khoảng trống không được tự tạo dữ liệu để lấp là: chấm relevance/nghiên cứu người dùng độc lập và xác minh thực địa/OSRM thật cho đợt hiện tại.
