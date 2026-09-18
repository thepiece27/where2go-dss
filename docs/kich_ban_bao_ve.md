# Kịch bản bảo vệ — Hệ gợi ý POI dựa trên nội dung và ngữ cảnh, kết hợp ra quyết định đa tiêu chí

Dùng cùng [báo cáo kỹ thuật](bao_cao_du_an_poi.md), [hướng dẫn chạy](huong_dan_chay.md) và [notebook đã thực thi](../notebooks/phan_tich_du_lieu_poi.ipynb). Snapshot `v2-ae66988a1053d0de`, policy `poi-recommendation-1.0`. Đây là khung nội dung để dựng slide và luyện nói; không đưa nguyên các đoạn văn dài lên slide.

Thông điệp: **Từ dữ liệu POI nhiều nguồn và chưa đồng đều, nhóm xây dựng hệ gợi ý theo nhu cầu khai báo, kết hợp ngữ cảnh và đa tiêu chí, giải thích được kết quả và công bố rõ giới hạn.** Người dùng có thể chuyển POI đã chọn sang chức năng lập lịch.

## 1. Mạch 18 slide, 27 phút

| Slide | Nội dung | Phút | Mốc kết thúc |
|---|---|---:|---:|
| 1 | Đề tài và câu hỏi mở đầu | 0:45 | 0:45 |
| 2 | Bài toán gợi ý và đầu ra | 1:15 | 2:00 |
| 3 | Phạm vi, ba trang và đóng góp | 1:00 | 3:00 |
| 4 | Nguồn và quy trình dữ liệu | 1:30 | 4:30 |
| 5 | Crawl, ghép thực thể và chất lượng | 2:30 | 7:00 |
| 6 | LORE: ảnh hưởng tuần tự | 1:30 | 8:30 |
| 7 | Contextualized POI: ngữ cảnh và regularization | 1:30 | 10:00 |
| 8 | Đối chiếu và lựa chọn phương pháp | 1:00 | 11:00 |
| 9 | Biểu diễn nội dung và lấy ứng viên | 1:30 | 12:30 |
| 10 | Bốn tiêu chí và ngữ cảnh | 1:30 | 14:00 |
| 11 | Mẫu ưu tiên, AHP và Fuzzy AHP | 1:30 | 15:30 |
| 12 | TOPSIS và giải thích | 1:30 | 17:00 |
| 13 | Demo gợi ý → chọn → lịch trình | 3:00 | 20:00 |
| 14 | Thiết kế thực nghiệm | 1:30 | 21:30 |
| 15 | Kết quả quan sát được | 1:30 | 23:00 |
| 16 | Độ nhạy và ý nghĩa | 1:00 | 24:00 |
| 17 | Hạn chế và hướng phát triển | 1:45 | 25:45 |
| 18 | Đóng góp và kết luận | 1:15 | 27:00 |

Nếu 30 phút bao gồm hỏi đáp, còn khoảng 3 phút cho câu hỏi. Nếu giới hạn cả phần nói 25 phút, rút slide 5 nửa phút, gộp slide 8 trong nửa phút và demo còn hai phút. Không bỏ phần hạn chế hoặc nhập nhằng giữa kết quả nhóm với kết quả paper.

Nhóm ba người có thể chia: người 1 bài toán–dữ liệu (1–5); người 2 paper–phương pháp (6–12); người 3 demo–đánh giá–kết luận (13–18). Chuyển người ở đúng ranh giới ý, tránh kể lại nội dung trước.

## 2. Nội dung và lời nói từng slide

### Slide 1 — Bạn nên cân nhắc địa điểm nào?

**Trên slide:** tên đề tài, thành viên, giảng viên; hai nhu cầu khác nhau tại cùng một địa phương: thích lịch sử và muốn đi gần, thích thiên nhiên và chấp nhận đi xa hơn.

**Lời nói:** “Một danh sách địa điểm nổi tiếng không đáp ứng mọi người như nhau. Nhóm đặt câu hỏi: với sở thích và ngữ cảnh được khai báo, hệ thống nên gợi ý những POI nào, và giải thích lựa chọn đó ra sao?”

Chuyển ý: xác định đầu vào và đầu ra trước khi nói tên thuật toán.

### Slide 2 — Đầu ra là Top-K có giải thích

**Hình:** `Sở thích + vị trí + ngày + phạm vi + ưu tiên → ứng viên → xếp hạng → Top-K + lý do`.

**Lời nói:** “POI là các địa điểm có danh tính và vị trí cụ thể. Hệ thống nhận nhu cầu, trả mặc định mười địa điểm theo thứ tự cân nhắc. Giải thích kèm theo gồm mức khớp nội dung, chi phí đi lại và bằng chứng hiện có. Địa điểm nào đi trước trong chuyến đi là câu hỏi khác, do bộ lập lịch xử lý sau.”

Không dùng ảnh timeline làm hình trung tâm của slide bài toán.

### Slide 3 — Phạm vi và ba trang

**Trên slide:** ba ảnh nhỏ Gợi ý POI / Khám phá / Lịch trình; gợi ý tại Hà Nội, Đà Nẵng; khám phá toàn quốc; sở thích khai báo, nhớ trên trình duyệt.

**Lời nói:** “Trang chủ phục vụ đề tài gợi ý. Khám phá cho phép chủ động tra cứu và kiểm tra trên bản đồ. Lịch trình dùng các điểm đã chọn để hỗ trợ thực hiện chuyến đi. Nhóm chưa học hồ sơ người dùng dài hạn; đóng góp là hệ thống tích hợp có khả năng giải thích, tái lập và kiểm tra.”

### Slide 4 — Nguồn và vòng đời dữ liệu

**Hình:** OSM PBF + ba workbook kế thừa + quan sát bổ sung → chuẩn hóa → ghép thực thể → chọn giá trị có provenance → SQLite → API/CSV/notebook.

**Lời nói:** “Các workbook là phiên bản quan sát chồng lặp, không phải ba tập POI độc lập để cộng số dòng. Chúng em giữ bằng chứng nguồn theo từng trường, ghép về canonical ID và tách dữ liệu gốc khỏi catalog phục vụ. Snapshot có 16.018 POI; số này mô tả dữ liệu nhóm có, không phải tổng POI thật của Việt Nam.”

Chỉ rõ địa giới snapshot khi nói Hà Nội/Đà Nẵng, nhất là dữ liệu Hội An thuộc địa bàn Quảng Nam cũ.

### Slide 5 — Crawl được chưa có nghĩa dữ liệu đúng

**Hình:** chọn hai biểu đồ phân bố/thiếu dữ liệu trong notebook, thêm một ví dụ sai danh tính hoặc tọa độ viewport.

**Lời nói:** “Pipeline thu thập theo địa điểm mục tiêu, lưu quan sát và bằng chứng; khâu review kiểm tra tên, vị trí, loại hình, rating và ảnh. Tên trùng, ảnh đại diện hoặc tọa độ khung nhìn có thể làm dữ liệu sai dù request thành công. Vì thế chỉ quan sát đủ bằng chứng được chọn vào catalog; phần chưa rõ giữ trạng thái cần kiểm tra.”

Rating chỉ phủ khoảng 0,54% toàn catalog theo snapshot; mẫu số này khác tập đủ điều kiện đề xuất. Sau cổng phục vụ, Hà Nội có 742 và Đà Nẵng có 493 POI đề xuất, trước lọc ngày/bán kính. Thiếu dữ liệu mô tả, rating, giờ hoặc lối tiếp cận là hạn chế thực của hệ thống.

**Chốt:** “Làm sạch danh tính và minh bạch dữ liệu thiếu có giá trị trực tiếp với chất lượng gợi ý; thêm thuật toán không tự chữa được dữ liệu nguồn.”

### Slide 6 — LORE 2014

**Trên slide:** check-in theo thứ tự → Location–Location Transition Graph → Additive Markov Chain; kết hợp sequential, social và geographical influence.

**Lời nói:** “LORE khai thác việc nơi tiếp theo liên quan đến chuỗi nơi đã ghé. Tác giả xây L2TG, dùng AMC dự đoán ảnh hưởng tuần tự rồi kết hợp ảnh hưởng xã hội và phân bố địa lý hai chiều. Dữ liệu nghiên cứu là Foursquare/Gowalla có lịch sử hành vi. Nhóm học cách tách tín hiệu và thiết kế baseline; hiện không có dữ liệu để triển khai lại LORE.”

Nguồn dưới slide: PDF LORE trong `paper/`, §3–4, công thức và bảng dữ liệu dẫn ở báo cáo §10. Không gọi beam search lập tuyến của dự án là AMC.

### Slide 7 — Contextualized POI 2020

**Trên slide:** ngữ cảnh toàn cục → graph Laplacian; ngữ cảnh cục bộ → nhóm người dùng và regularization; tối ưu luân phiên → ma trận dự đoán.

**Lời nói:** “Paper mô hình hóa độ tương tự và ngữ cảnh thông qua ràng buộc trong hàm mục tiêu, dùng graph và nhóm người dùng. Nó cần tương tác và quan hệ giữa người dùng/POI. Đây không phải cùng cách biểu diễn ngữ cảnh với việc nhóm nhận vị trí, ngày và sở thích khai báo.”

Nguồn: PDF Contextualized POI, §3–5; báo cáo §11. Không gọi phương pháp này là GNN hoặc deep learning nếu paper không dùng các kiến trúc đó.

### Slide 8 — Vì sao chọn nội dung + ngữ cảnh + MCDM?

**Bảng ba cột:** LORE / Contextualized POI / Where2Go. Chỉ giữ các dòng dữ liệu, cá nhân hóa, ngữ cảnh, cách kết hợp và đánh giá.

**Lời nói:** “Điểm chung là phối hợp nhiều tín hiệu để chọn POI. Khác biệt quyết định là dữ liệu: nhóm có metadata địa điểm và nhu cầu khai báo, chưa có chuỗi check-in hay social graph. Content-based cho phép hoạt động ngay trong điều kiện đó; MCDM diễn đạt đánh đổi giữa sở thích, chất lượng và đi lại. Đây là lựa chọn phù hợp đầu vào, chưa phải bằng chứng vượt phương pháp của paper.”

### Slide 9 — Nội dung và truy hồi ứng viên

**Trên slide:** tên/bí danh/mô tả/loại hình/tags → TF-IDF + cosine; công thức $P=0,7P_{tax}+0,3P_{text}$; hợp 40 nội dung + 40 gần + 40 chất lượng.

**Lời nói:** “TF-IDF biểu diễn các từ phân biệt trong metadata; cosine đo tương đồng với yêu cầu. Taxonomy bổ sung chủ đề có cấu trúc. Hệ số 0,7/0,3 do nhóm thiết kế, chưa tối ưu trên nhãn. Nếu chỉ lấy ba mươi điểm gần trước khi xếp hạng, có thể bỏ sót nơi rất hợp sở thích. Vì vậy nhóm hợp ba nhánh truy hồi rồi khử trùng, tối đa 120 ứng viên.”

Nêu hạn chế: mô tả thưa, bỏ dấu, khớp từ chưa hiểu đầy đủ đồng nghĩa/phủ định; shortlist vẫn có thể bỏ sót POI.

### Slide 10 — Bốn tiêu chí và điều kiện bắt buộc

**Trên slide:** sở thích ↑; rating có shrinkage ↑; chi phí đi lại ↓; bằng chứng dữ liệu ↑.

**Lời nói:** “Đóng cửa và ngoài phạm vi là điều kiện lọc. Các ứng viên còn lại được đánh đổi qua bốn tiêu chí. Rating hiệu chỉnh theo số lượt và prior để giảm tác động mẫu nhỏ; thiếu rating nhận giá trị trung tính theo chính sách, không tạo đánh giá giả. OSRM đầy đủ thì dùng giây; thiếu đường cho một phần pool thì cả lượt dùng km đường chim bay có nhãn.”

Không đặt giây của một POI và km của POI khác trong cùng cột. Giờ mở cửa chưa biết không được trình bày thành đang mở.

### Slide 11 — Trọng số, AHP và điều phải nói về fuzzy

**Trên slide:** bốn mẫu ưu tiên; ma trận $a_{ij}=w_i/w_j$; $CR\le0,1$; ghi chú “bất định đồng đều ⇒ fuzzy/crisp cùng trọng số”.

**Lời nói:** “Giao diện dùng mẫu có sẵn để người dùng không cần hiểu sáu so sánh cặp. Các trọng số là chính sách nhóm đề xuất. Ma trận dựng từ tỷ số trọng số nhất quán theo cấu trúc; CR thấp không chứng minh trọng số đúng với mọi người. Fuzzy AHP có trong mã nghiên cứu, nhưng khi bất định bằng nhau trên mọi cặp, chuẩn hóa làm ảnh hưởng fuzzy triệt tiêu. Thực nghiệm của nhóm thể hiện đúng tính chất này.”

Không tuyên bố fuzzy giảm mơ hồ và tăng chất lượng nếu chưa có phán đoán bất định hoặc nhãn chứng minh.

### Slide 12 — TOPSIS và lý do hiển thị

**Hình:** ma trận → chuẩn hóa → trọng số → ideal tốt/xấu → $S_i=d_i^-/(d_i^++d_i^-)$ → danh sách.

**Lời nói:** “Một POI tốt theo TOPSIS gần phương án lý tưởng tốt và xa phương án xấu theo trọng số đã chọn. Score 0,8 là điểm tương đối trong pool, không có nghĩa xác suất thích 80%. Chuẩn hóa trên cả pool trước khi lấy Top-K giúp đổi số lượng hiển thị không đổi điểm. Lý do trên giao diện lấy từ dữ liệu thực: loại hình khớp, chi phí di chuyển, rating quan sát và dữ liệu thiếu.”

Để phép tính số chi tiết ở phụ lục, dùng ví dụ hai POI của báo cáo §7.9. Nhắc rank reversal khi pool thay đổi.

### Slide 13 — Demo ba phút

**0:00–0:45:** mở trang chủ, Đà Nẵng, ngày cố định 20/09/2026, vị trí tâm mẫu. Chọn thiên nhiên, bấm Nhận gợi ý. Nói rõ ngày demo, không phải dữ liệu giờ mở cửa trực tiếp.

**0:45–1:30:** mở “Vì sao được gợi ý?”; chỉ vào lý do, điểm tương đối, nguồn và dữ liệu thiếu. Đổi sang Đi gần, nhận gợi ý lại để minh họa đánh đổi. Nếu thứ tự không đổi ở ca cụ thể, giải thích theo ma trận thay vì khẳng định mọi thay đổi đều phải đảo hạng.

**1:30–2:15:** thêm một hoặc hai POI; sang Khám phá kiểm tra vị trí và dùng ví dụ Mỹ Khê/Phạm Văn Đồng đã kiểm tra cho demo lịch.

**2:15–3:00:** sang Lịch trình, chứng minh danh sách được giữ; tạo một phương án nếu OSRM sẵn sàng. Chỉ trình bày ngắn quan hệ gợi ý → người dùng chọn → lập lịch. Nếu routing lỗi, hiển thị thông báo thật và dùng ảnh đã kiểm chứng, không giả lập tuyến thành kết quả trực tiếp.

### Slide 14 — Đánh giá cái gì và bằng cách nào?

**Trên slide:** 16 bối cảnh, 4 development/12 holdout; sáu phương pháp; ba tầng kiểm chứng: phần mềm / đặc tính kết quả / relevance.

**Lời nói:** “Đây là chia kịch bản yêu cầu, không phải huấn luyện từ check-in. Mỗi bối cảnh dùng cùng pool/ma trận cho Nearby, Quality, Content, Equal TOPSIS, AHP và Fuzzy AHP. Nhóm đã chạy 96 lượt. Để đo relevance, công cụ gộp Top-10, xáo trộn và ẩn phương pháp để nhóm chấm 0–3.”

Nếu phiếu chưa chấm, nói **chưa có Precision/NDCG**. Nếu đã chấm, thay slide bằng số thật, số bối cảnh đủ nhãn và hash đợt tương ứng; nêu nhóm tác giả là người chấm.

### Slide 15 — Kết quả quan sát được

**Hình:** `11_goi_y_top_k.png`; bảng sáu phương pháp trong báo cáo §9.0.

**Lời nói:** “Trên holdout, Nearby gần nhất trung bình 2,31 km đường chim bay; Content là 8,61 km; AHP là 6,69 km. AHP có trung bình 3,67 loại hình trong Top-10. Những con số thể hiện đánh đổi thiết kế. Không thể kết luận AHP chính xác hơn chỉ vì khoảng cách hoặc độ đa dạng nằm giữa hai baseline.”

12/16 bối cảnh có đủ đường OSRM; bốn bối cảnh fallback địa lý. Fuzzy và crisp trùng Top-10 trong 16/16. Không dùng số phương án lịch làm “accuracy” của gợi ý.

### Slide 16 — Độ nhạy giúp hiểu giới hạn

**Hình:** `13_do_nhay_goi_y.png`, có thể thêm `14_ngu_canh_duong_di.png` ở phụ lục.

**Lời nói:** “So với Cân bằng, mẫu Đi gần có overlap Top-10 trung bình khoảng 0,769, chứng tỏ chính sách ưu tiên tạo khác biệt. Đổi pool 20 hoặc 80 so với 40 có overlap khoảng 0,938 và 0,963. Chỉ trên 12 ca có OSRM, đổi sang chi phí địa lý có overlap khoảng 0,942. Overlap không đo thứ tự hay độ đúng; độ nhạy cho biết kết quả phụ thuộc lựa chọn thiết kế.”

### Slide 17 — Điểm tốt, chưa tốt và phát triển

**Trên slide:** ba cặp “hiện có → việc cần làm”.

- Chạy được với metadata, giải thích theo tiêu chí → cải thiện mô tả, taxonomy và cách xử lý thiếu rating.
- Dữ liệu nhiều nguồn có provenance → xác minh danh tính, giờ, cổng và thời lượng trên tập trọng tâm.
- Thực nghiệm tái lập, có baseline/sensitivity → hoàn thành nhóm chấm, sau đó thu người chấm độc lập và đánh giá sử dụng thực tế.

**Lời nói:** “Rủi ro lớn nhất không phải thiếu thuật toán phức tạp mà là dữ liệu thiếu và thiếu nhãn chất lượng. Trọng số vẫn là thiết kế; TF-IDF chưa hiểu sâu nhu cầu; shortlist/TOPSIS có phụ thuộc pool; thời gian OSRM không có giao thông trực tiếp. Khi đã có tương tác đáng tin cậy, nhóm mới thử học hồ sơ nội dung, tuần tự hoặc graph và so với baseline hiện tại.”

### Slide 18 — Kết luận đúng mức bằng chứng

**Trên slide:** “POI recommendation là trung tâm — nội dung/ngữ cảnh — đa tiêu chí — giải thích — đánh giá tái lập”.

**Lời nói:** “Nhóm đã xây dựng hệ gợi ý POI theo nhu cầu khai báo và dữ liệu hiện có, đưa kết quả ra giao diện ba trang và liên kết với lập lịch. Đóng góp nằm ở cách tổ chức dữ liệu, kết hợp tín hiệu, giải thích và thực nghiệm có thể tái lập. Nhóm chưa khẳng định vượt mô hình hành vi của hai paper hoặc hiệu quả với người dùng độc lập. Bước tiếp theo là hoàn thiện dữ liệu trọng tâm và nhãn đánh giá để kiểm chứng các lựa chọn.”

## 3. Câu hỏi phản biện cần chuẩn bị

| Câu hỏi | Cách trả lời có căn cứ |
|---|---|
| Đây có đúng hệ gợi ý POI không? | Đầu vào sở thích/ngữ cảnh, đầu ra Top-K POI; có hàm xếp hạng và giải thích. Planner là chức năng sau lựa chọn. |
| Là lọc nội dung hay cộng tác? | Nội dung và ngữ cảnh với MCDM. Chưa có ma trận tương tác user–item để gọi là CF. Rating Google không thay ma trận đó. |
| TF-IDF có phải học máy không? | Fit từ vựng và IDF của corpus là biểu diễn thống kê nội dung; chưa học mô hình hành vi hay sở thích từ nhãn. |
| Cá nhân hóa ở đâu? | Theo sở thích người dùng khai báo cho yêu cầu hiện tại; không tuyên bố học cá nhân hóa dài hạn. |
| AHP sinh từ trọng số có vòng tròn không? | Mẫu trọng số là chính sách; tạo tỷ số để đi qua cơ chế AHP nhất quán. Không dùng CR=0 làm bằng chứng elicitation khách quan. |
| Vậy fuzzy có ích gì? | Cấu hình đồng đều hiện tại không đổi trọng số. Được giữ để nghiên cứu bất định theo cặp, chưa chứng minh giá trị gia tăng. |
| Sao không dùng LORE/graph của paper? | Thiếu chuỗi check-in/social/context hành vi. Nhóm so sánh điều kiện dữ liệu và kế thừa cách đánh giá, chưa tái hiện mô hình đó. |
| Tại sao 0,7/0,3, prior 50, shortlist 40? | Tham số thiết kế ban đầu; đã có sensitivity pool/trọng số, cần nhãn để chọn/tối ưu có căn cứ. |
| Thiếu rating dùng 0,5 có công bằng không? | Đây là mặc định có rủi ro, có thể thấp hơn nhóm có rating; công bố missingness và cần ablation/nhãn để kiểm tra thiên lệch. |
| Không có OSRM còn là context-aware không? | Có vị trí, bán kính, ngày và chi phí địa lý có nhãn. Không giả có thời gian lái xe hoặc lịch khả thi. |
| Precision/NDCG đâu? | Khi chưa chấm: chưa có. Sau chấm: relevance ≥2; NDCG trên pooled set đã chấm, không suy Recall toàn catalog. |
| 4/12 có phải train/test không? | Development/holdout theo yêu cầu, không phải check-in training/test. Holdout đã xem không được dùng tối ưu rồi tuyên bố đánh giá độc lập. |
| Tại sao có POI xa hoặc khác loại trong Top-K? | Category là ưu tiên mềm, bốn tiêu chí có bù trừ; xem ma trận và trọng số cụ thể. Không bảo đảm mọi POI đều đúng ý khi metadata thưa. |
| Điểm cao nhất có đi đầu lịch trình không? | Không. Thứ tự ghé còn phụ thuộc đường, giờ mở cửa, thời lượng và điểm bắt buộc. |
| Kết quả có tối ưu toàn cục không? | Không: truy hồi giới hạn và planner beam search có giới hạn. TOPSIS chỉ xếp hạng tập được đưa vào. |

## 4. Phụ lục và chuẩn bị trước buổi bảo vệ

Chuẩn bị phụ lục công thức TF-IDF/cosine, taxonomy, shrinkage rating, Haversine, confidence, AHP/CR, fuzzy geometric mean/giải mờ, TOPSIS, Precision/NDCG, entropy/coverage/overlap. Mỗi công thức ghi biến, đơn vị, giả định và vị trí mã nguồn trong báo cáo. Phần paper ghi đúng số phương trình/trang PDF; không gán công thức paper thành phương pháp đã triển khai.

Chạy lại notebook và smoke trước buổi demo; dùng cùng dataset/policy với số trên slide. Kiểm tra riêng routing, ảnh và bản đồ; chuẩn bị ảnh đã chụp trong `artifacts/recommendations/`. Nếu đã có nhãn nhóm chấm, chạy `--grades`, kiểm tra hash rồi cập nhật cả notebook và slide. Nếu chưa có, giữ nhãn NOT GRADED.

Tập trình bày hai lần có bấm giờ. Mỗi biểu đồ phải trả lời được: mẫu số nào, dữ liệu nào, điều gì quan sát được, và điều gì chưa suy ra được. Không đọc toàn bộ bảng số; chọn một kết quả và một giới hạn để giải thích.
