# Kế hoạch triển khai Where2Go DSS v2: dữ liệu đa nguồn và lịch trình tham quan hợp lý

**Trạng thái:** Đặc tả chuẩn bị triển khai, cập nhật ngày 17/09/2026. Chưa bắt đầu coding v2; các chỉ tiêu dưới đây là mục tiêu, chưa phải kết quả nghiệm thu.  
**Thời gian:** 7 ngày làm việc.  
**Địa bàn:** Hà Nội và Đà Nẵng mới, bao gồm Quảng Nam cũ.  
**Ngân sách:** Công cụ miễn phí trước, Docker/WSL và máy hiện có.  
**Căn cứ:** [Review nền tảng](bao_cao_review_du_an_where2go_dss.md), [kế hoạch v1](ke_hoach_hoan_thien_where2go_dss.md), [kết quả v1](ket_qua_trien_khai.md).

Tài liệu này thay hướng catalog chỉ dùng OSM bằng dữ liệu đa nguồn có kiểm soát. Giữ yêu cầu ID bền vững, provenance, toán học đúng, tuyến thật và báo cáo trung thực. Không ghi đè kết quả v1 thành kết quả v2 chưa thực hiện.

## 1. Mục tiêu và quyết định đã chốt

Người dùng cần biết: với xuất phát, ngày, thời gian và sở thích của mình, nên ghé đâu, ở bao lâu, ăn/nghỉ lúc nào và quay về khi nào. Tìm được đường hoặc tạo đủ năm điểm chưa chứng minh chuyến đi hợp lý.

- Giữ Fuzzy AHP + TOPSIS và OSRM tự chạy.
- Hợp nhất nguồn sẵn có; thu thập bổ sung theo trường thiếu.
- 1–5 điểm tham quan; một điểm lớn có thể chiếm phần lớn ngày. Ăn/nghỉ tính riêng.
- Category mặc định là sở thích ưu tiên; có chế độ chuyên đề chỉ đi các loại đã chọn.
- Cho chọn nhanh/cân bằng/thư thả và sửa thời lượng từng điểm; backend phải tính lại toàn lịch.
- Chủ dự án chấm thử theo phiếu. Đây chưa phải khảo sát độc lập hay khảo sát thực địa.
- Chưa làm tối ưu tuyến toàn cục, giao thông trực tiếp, mô hình thời lượng học từ hành vi, thu toàn bộ review, dữ liệu cá nhân người đánh giá, phủ đều toàn quốc hoặc định tuyến đa phương tiện đầy đủ.
- Không tuyên bố fuzzy tốt hơn baseline khi chưa có bằng chứng.

## 2. Hiện trạng cần xử lý

Bản `vietnam_destinations_google_maps_browser_hotosm_backup_20260916_150600.xlsx` đã được kiểm kê:

| Chỉ số | Số dòng |
|---|---:|
| Tổng | 8.710 |
| Có nội dung đánh giá | 7.987 |
| Có số review | 4.155 |
| Có loại địa điểm Google | 4.055 |
| Có chuỗi giờ | 2.248 |
| Tên kết quả `Results` | 3.316 |

Các dòng đang mang địa danh Hà Nội/Đà Nẵng: 930 bản ghi; 857 có đánh giá, 644 có số review, 616 có loại hình, 285 có chuỗi giờ. Đây là độ có dữ liệu, chưa phải độ đúng.

Giờ cũ có thể lẫn phần trăm đông khách hoặc chỉ là một ngày. Tên khu có thể ghép với cổng/cáp treo/công trình con. Rating và review count chưa chắc cùng quan sát. Cần giữ dữ liệu để đối chiếu, không nối bảng rồi coi mọi giá trị đều đúng.

V1 còn các hạn chế: category lọc cứng; dwell cố định; khớp từ chung; chưa dùng rating hiệu chỉnh; chưa phân biệt cha–con; thiên về điểm nhỏ gần nhau; thiếu ăn/nghỉ và tiếp cận.

Phân công nguồn: Google/website địa điểm cung cấp metadata; OSM hỗ trợ POI và không gian; OSRM tính đường ô tô; kiểm duyệt giải quyết mâu thuẫn và đánh giá trải nghiệm. OSRM không phải crawler rating/giờ.

## 3. Kiến trúc dữ liệu đa nguồn

### 3.1. Vai trò các bộ dữ liệu

| Nhóm | Cách dùng |
|---|---|
| Workbook gốc, Google/HOTOSM và backup | Quan sát nguồn theo phiên bản |
| OSM, địa giới | Không gian, loại hình và đối chiếu |
| Workbook cleaned | Dẫn xuất để đối chiếu; chỉ phục hồi giá trị truy ngược được nguồn |
| Recommendation/evaluation/chronological | Kết quả lịch sử, không phải nhãn hay thuộc tính POI |
| Synthetic behavior | Fixture, không phải hành vi thật |
| Catalog/review hiện tại | Giữ ID và bằng chứng đã có |

```text
Nguồn bất biến → quan sát theo nguồn/thời điểm → đối sánh và giải quyết mâu thuẫn
→ catalog hợp nhất → lọc theo request → xếp hạng → lịch trình → giải thích
```

### 3.2. Ba lớp lưu trữ

1. **Nguồn nguyên bản:** workbook/snapshot/đợt thu thập có checksum, tên, thời điểm nhận, công cụ. Không sửa nguồn cũ.
2. **Quan sát:** một thực thể có nhiều quan sát Google/OSM/website/kiểm duyệt. Giá trị mới không xóa giá trị cũ. Không coi thời gian sửa file là thời gian thu thập.
3. **Catalog:** chọn theo từng trường, lưu lý do và liên kết quan sát; không lấy nguyên một dòng làm chuẩn cho mọi trường.

Mỗi giá trị chọn có `value`, `source`, `source_record_id`, `observed_at`, `verified_at`, `verification_method`, `selection_reason`. Ngày import không thành ngày xác minh.

### 3.3. Schema nghiệp vụ

| Nhóm | Trường cần có |
|---|---|
| ID | Canonical ID, alias, OSM ID, Google Place ID/CID |
| Danh tính | Tên chính/nguồn, alias, website |
| Vị trí | Địa phương gốc/hiện hành, POI coordinate, access coordinate, bằng chứng |
| Loại | Loại chính/phụ, nhãn trải nghiệm, quan hệ cha–con |
| Rating | Giá trị, số review, nhà cung cấp, thời điểm cùng quan sát |
| Hoạt động | Hoạt động/đóng tạm/đóng vĩnh viễn/chưa biết |
| Giờ | Lịch tuần, ngoại lệ ngày, raw và phạm vi lịch |
| Thời lượng | Ngắn/thông thường/dài, phương pháp và nguồn |
| Tiếp cận | Điểm ô tô, đỗ/đi bộ, mức xác minh |
| Kiểm duyệt | Người/công cụ, ngày, trường kiểm tra, mâu thuẫn |
| Quyền sử dụng | Nguồn, điều kiện, trạng thái cho phép xuất bản |

### 3.4. ID và ghép thực thể

- Giữ canonical ID đang phục vụ. ID mới phải lưu registry; không lấy số dòng sau lọc.
- Place ID/CID/OSM ID là khóa nguồn. STT chỉ có ý nghĩa trong họ workbook đã kiểm tra.
- STT/tên khớp giữa backup không chứng minh Google đã match đúng POI.
- Ghép theo ID đã liên kết → liên kết người duyệt → tổ hợp tên/alias, khu vực, tọa độ đáng tin, loại phù hợp.
- Có nhiều ứng viên thì để ambiguous. Không chỉ dựa tên, độ gần, cùng địa chỉ hoặc nằm trong cùng polygon.
- Tách khu tham quan, công trình con, cổng, ga cáp treo, bãi đỗ. Không biến chúng thành nhiều lần tham quan độc lập.

### 3.5. Chọn giá trị và mâu thuẫn

- Tên: giữ alias và tên phù hợp. Địa phương: polygon hiện hành, giữ địa danh cũ.
- Tọa độ: chọn bằng chứng đúng thực thể; `@lat,lng` của viewport không hợp lệ. Tách cổng và tâm khu.
- Rating: không trung bình tùy tiện giữa nền tảng, không ghép count từ nguồn khác.
- Giờ: ưu tiên thông báo hiện hành của địa điểm; vẫn lưu nguồn khác để đối chiếu.
- Thời lượng: hồ sơ POI tốt hơn mặc định loại hình. Mô tả không bịa trải nghiệm.
- Mâu thuẫn danh tính/vị trí/đóng cửa nghiêm trọng chặn phục vụ cho đến khi giải quyết.

## 4. Thu thập bổ sung bằng công cụ

### 4.1. Lựa chọn

Thử [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) trong Docker riêng, pin commit/image. Công cụ công bố hỗ trợ URL địa điểm, rating/count, giờ, category, Place ID/CID và resume; phải đo trên mẫu Việt Nam.

Playwright hiện có chuyển thành công cụ đối soát trang chi tiết và bảng giờ; không dùng quy tắc “có h1 là matched”. [populartimes](https://github.com/m-wrzr/populartimes) chỉ tham khảo: `time_spent` tùy chọn, có thể parse sai theo ngôn ngữ, không là dependency bắt buộc.

### 4.2. Pilot và cổng chất lượng

- 60 địa điểm, 30 mỗi thành phố: nổi tiếng, nhỏ, đồng tên, công trình con, bản ghi nghi sai, nhà hàng/cà phê, có/thiếu giờ và rating.
- Đo đúng thực thể, độ đúng từng trường, đủ lịch tuần, cặp rating/count cùng nguồn, lỗi và resume không trùng.
- Chỉ mở rộng nhập tự động khi ít nhất 95% mẫu được đối soát là đúng thực thể. Mẫu chưa được người chấm không được tự gắn PASS.
- Nếu không đạt: sửa chọn trang hoặc chuyển nhập tay cho tập ưu tiên. Không giảm ngưỡng âm thầm.

### 4.3. Hàng công việc

Ưu tiên POI tốt thiếu giờ/thời lượng → URL đã xác định → mâu thuẫn cần làm mới → loại thiếu trong cụm → điểm mới. Tác vụ lưu seed/truy vấn, thành phố/cụm, trường thiếu, trạng thái, số lần thử, thời điểm, kết quả match và lỗi.

Chạy lô nhỏ có checkpoint, retry giới hạn. CAPTCHA/chặn truy cập: dừng và ghi nhận, không vượt chặn. Không thu danh tính tác giả, email hoặc toàn bộ review.

### 4.4. Website chính thức

Đối soát giờ/ngoại lệ, cổng, địa chỉ, tình trạng hoạt động, lịch biểu diễn và thời lượng chương trình. Website có chữ “du lịch” chưa chắc là cơ quan quản lý. Chỉ dùng danh sách nguồn đã xác định chủ thể; nguồn thứ cấp có nhãn riêng.

### 4.5. Quyền sử dụng

Google hạn chế sao chép/tải hàng loạt; giấy phép scraper không cấp quyền với dữ liệu Google. Gắn hạn chế sử dụng, không tự xuất nguồn này công khai; dùng nội bộ không phải ngoại lệ mặc nhiên. [Điều khoản](https://maps.google.com/help/terms_maps/)

Nếu dùng Places API phải tuân thủ lưu trữ, attribution và hiển thị; không mặc định lưu vĩnh viễn/ghép mọi trường lên Leaflet. [Chính sách API](https://developers.google.com/maps/documentation/places/web-service/policies)

## 5. Hướng dẫn Google Maps thủ công

### 5.1. Workbook

Tạo riêng `data/manual/poi_enrichment_v2.xlsx`, gồm `places`, `opening_hours`, `visit_duration`, `verification`. Liên kết bằng `record_id`; `canonical_poi_id` giữ ID cũ nếu có. Không sửa workbook nguồn, SQLite hoặc CSV xuất.

### 5.2. Sheet places

| Trường | Cách ghi |
|---|---|
| record_id | Khóa riêng trong đợt |
| canonical_poi_id | ID cũ nếu xác định chắc chắn |
| seed_name, maps_name | Tên cần tìm và tên thực tế trên trang |
| maps_url, place_id, cid | URL chi tiết/chia sẻ; ID chỉ ghi nếu chắc chắn |
| address_raw, location_expected | Địa chỉ nguồn; Hà Nội/Đà Nẵng dự kiến |
| category_raw | Loại gốc, chưa thay bằng suy đoán |
| rating_raw, review_count_raw | Chuỗi nguyên bản cùng trang/cùng thời điểm |
| latitude, longitude | Tọa độ có bằng chứng, không dùng viewport |
| coordinate_method | POI point/manual_map_selection/entrance có bằng chứng |
| website, business_status_raw | Website và trạng thái hoạt động nguồn |
| observed_at, reviewer, notes | Thời điểm thật, người kiểm tra, nghi vấn |

Thiếu rating/review/tọa độ để trống; không dùng 0 thay cho thiếu.

### 5.3. Bảy bước kiểm tra mỗi điểm

1. **Trang đúng:** mở URL cũ nếu đúng; nếu tìm mới dùng tên + khu vực + thành phố. Kiểm tra tên, địa chỉ, loại và vị trí. Không dùng kết quả đầu tiên hay danh sách tìm kiếm làm bằng chứng.
2. **Thực thể:** phân biệt khu, bảo tàng con, cổng, cáp treo, bãi đỗ, nhà hàng cùng tên. Không rõ thì ambiguous.
3. **Rating/count:** ghi cùng trang/cùng lần xem. Không có thì để thiếu; không ghép hai thẻ khác nhau.
4. **Giờ:** mở bảng giờ chi tiết, kiểm tra bảy ngày. “Đang mở/đóng lúc…” không phải lịch tuần. Hai ca ghi hai khoảng; ngày chưa biết giữ unknown.
5. **Tọa độ:** không lấy `@lat,lng`. Điểm chọn bằng tay ghi `manual_map_selection`, chưa được gọi là cổng xác minh. Sau import kiểm tra polygon/OSRM, nhưng có đường chưa chứng minh cổng mở.
6. **Nguồn địa điểm:** xem website, thông báo giờ/địa chỉ/đóng cửa. Nguồn khác nhau thì giữ cả hai và ghi mâu thuẫn.
7. **Kết luận:** confirmed, ambiguous, unmatched, blocked hoặc closed. Ghi bằng chứng; không nâng trạng thái chỉ vì đủ ô.

### 5.4. Sheet opening_hours

```text
record_id, day_of_week, specific_date, status, open_time, close_time,
closes_next_day, source_url, observed_at, notes
```

Mỗi khoảng một dòng. `open` có giờ rõ, `closed` nguồn nói đóng, `unknown` chưa biết. Lịch tuần dùng day_of_week; ngoại lệ dùng specific_date. Qua nửa đêm đánh dấu closes_next_day. Không lấy popular-times làm giờ.

Ví dụ minh họa: thứ Ba 08:00–12:00 và 13:00–17:00 là hai khoảng; thứ Hai closed; Chủ Nhật unknown. Ba trạng thái phải khác nhau, không tự sao giờ sang những ngày chưa đọc.

### 5.5. Sheet visit_duration

```text
record_id, short_minutes, typical_minutes, long_minutes, duration_method,
source_url, source_text_short, observed_at, reviewer, notes
```

Phương pháp phải phân biệt chương trình địa điểm công bố, khoảng lưu lại nguồn báo cáo, ước lượng người duyệt, mặc định category. Nguồn chỉ có khoảng thì giữ khoảng; typical suy ra là dẫn xuất. Không lấy giờ mở cửa để suy thời lượng.

### 5.6. Sheet verification

Ghi người, ngày, trường kiểm tra, đúng/sai/chưa chắc, URL bằng chứng, mâu thuẫn và quyền vào tập demo. Tool review giữ nhãn tool; không tự ghi tên người chưa thực sự kiểm tra.

### 5.7. Quy trình lô

Làm 10–15 điểm cùng cụm; xác nhận danh tính trước, bổ sung trường sau. Cuối mỗi lô validate, dò trùng/mâu thuẫn, sửa tại workbook/biên bản rồi build lại. Không chỉnh đầu ra catalog bằng tay.

## 6. Chất lượng dữ liệu mục tiêu

Mỗi thành phố: 50 điểm tham quan + 20 ăn/nghỉ, ít nhất năm nhóm trải nghiệm. Vẫn kiểm kê toàn bộ nguồn, không ngừng ở mẫu này.

Hà Nội: Hoàn Kiếm/phố cổ, Ba Đình, Tây Hồ, Bát Tràng, ngoại thành có bằng chứng. Đà Nẵng: trung tâm, ven biển/Ngũ Hành Sơn, Hội An, Mỹ Sơn, Bà Nà/điểm lớn. Không buộc ghép cụm xa trong một ngày.

- 100% ID/nguồn truy vết và đúng thực thể trước phục vụ.
- 100% có kết quả routing hoặc lý do chưa đủ điều kiện.
- ≥80% tập ưu tiên có lịch tuần/điều kiện tiếp cận đọc được.
- Mỗi điểm có duration profile hoặc fallback có nhãn; ≥80% điểm tham quan có hồ sơ riêng được đối soát/người duyệt đánh giá.
- Rating/count báo coverage riêng, không bịa để đủ 100%.
- Không có Results hoặc mâu thuẫn thực thể chưa giải quyết trong demo.
- Chưa đạt phải báo số thật và nguyên nhân; đây là mục tiêu, chưa phải kết quả.

## 7. Taxonomy và sở thích

Giữ mã cũ, thêm phố cổ, làng nghề, chợ, khu thiên nhiên, biểu diễn, nhà hàng, cà phê, khu ẩm thực. Một primary category và nhiều tags: lịch sử, văn hóa, nghệ thuật, tâm linh, thiên nhiên, gia đình, ngoài trời, trong nhà, chụp ảnh, ẩm thực, thư giãn.

Tách lọc danh sách, sở thích ưu tiên và chuyên đề. Chế độ ưu tiên cố có ít nhất một điểm phù hợp nếu khả thi, kết hợp loại khác; chế độ cân bằng tối đa hai điểm cùng primary category. Chuyên đề chỉ chọn loại cho phép. Loại bị loại trừ là ràng buộc cứng. Giới hạn category tham quan không tự cấm ăn/nghỉ. Không đáp ứng được chủ đề phải giải thích.

## 8. Thời lượng và đệm

Hồ sơ riêng gồm ngắn/thông thường/dài; nhanh/cân bằng/thư thả chọn mức tương ứng. Nguồn POI được ưu tiên hơn bảng fallback dưới đây (phút, hoàn toàn là giả định thiết kế):

| Loại | Ngắn | Thông thường | Dài |
|---|---:|---:|---:|
| Ngắm/chụp ảnh nhỏ | 15 | 30 | 45 |
| Di tích riêng lẻ | 20 | 45 | 75 |
| Đền/chùa | 20 | 45 | 90 |
| Bảo tàng | 30 | 60 | 120 |
| Công viên | 30 | 60 | 120 |
| Chợ | 30 | 60 | 90 |
| Phố cổ/làng nghề theo khối | 60 | 120 | 180 |
| Bãi biển | 45 | 90 | 150 |
| Khu lớn | 180 | 300 | 480 |

Không tự rút dwell để nhét đủ điểm. User override lưu riêng, backend tính lại; không khả thi thì nêu ràng buộc xung đột. Tách drive + access/parking + wait + visit + meal/break + reserve. Access thiếu dùng giả định công khai, không gọi là walking route thật. Reserve = 10% tổng lái xe, min 15 và max 45 phút/lịch; đây không phải mô hình tắc đường.

[Nghiên cứu thời lượng biến đổi](https://riunet.upv.es/server/api/core/bitstreams/313b444f-14bc-42c0-b9aa-8de4047261e2/content) là tham khảo; v2 chưa học dwell từ hành vi thật.

## 9. Fuzzy AHP + TOPSIS v2

### 9.1. Bốn tiêu chí

`preference_match` benefit; `place_quality` benefit; `drive_time` cost; `data_confidence` benefit. Cùng tên/thứ tự trong schema, API, web, evaluator.

Preference = 70% taxonomy/tags + 30% TF-IDF tên/alias/mô tả có nguồn. Không dùng tọa độ/rating/boilerplate/hành vi mô phỏng làm nội dung. Không có sở thích thì trung tính toàn pool.

### 9.2. Rating

`Q = (v*R + m*C)/(v+m)`, m=50 là tham số khởi đầu. R và v cùng nguồn/quan sát. C: cùng loại/thành phố nếu ≥10 mẫu → cùng loại hai thành phố → toàn tập hợp lệ. Không có rating toàn tập thì tiêu chí trung tính; không sinh sao để hiển thị. Review count không được thêm lần nữa thành tiêu chí popularity.

### 9.3. Tin cậy

Dựa bằng chứng đúng thực thể, tiếp cận/routing, giờ theo ngày, hoạt động đã kiểm tra trong 180 ngày. Công thức/điều kiện version hóa; không phải xác suất hoặc điểm trải nghiệm.

### 9.4. AHP/TOPSIS

Trọng số mặc định thiết kế: 0,40/0,30/0,20/0,10; không gọi chuyên gia. Ma trận mặc định từ tỷ lệ trọng số. Sáu phán đoán nâng cao; kiểm tra miền, reciprocal, hữu hạn, CR≤0,1. Fuzzy đối xứng, bất định riêng từng cặp; không cố làm khác crisp. Chung độ mờ có thể trùng crisp geometric mean và phải công bố.

TOPSIS dùng pool cố định, vector normalization, drive cost không đảo hai lần, cột hằng/0 không NaN, tie ID. Không so score giữa hai pool như thang tuyệt đối.

## 10. Planner v2

Pool ≤40 tham quan +20 ăn/nghỉ; có chủ đề, chất lượng và thuận tiện, không chỉ gần. Lọc thực thể/cha–con, routing có đi/về tới access point.

1. Xếp hạng, thử tối đa năm seed hạng cao.
2. Chèn mọi vị trí, xét lợi ích tăng thêm, đa dạng, drive/wait.
3. Chỉ giữ lịch không vi phạm giờ, dwell, hướng đường và hạn về.
4. Thử relocate/thay một điểm, tối đa 20 vòng.
5. Route thật và mô phỏng lại; chọn theo objective công bố.

Thư thả/cân bằng/nhanh giới hạn 3/4/5 điểm, không bắt buộc đủ. Bình thường ≥2; một điểm chỉ khi là điểm chính có typical≥180 phút và lịch tập trung vào điểm lớn đó.

Ăn bật mặc định: trưa 11:30–14:00, tối 18:00–20:00, 60 phút/bữa khi chuyến bao phủ cửa sổ. Nghỉ/cà phê tùy chọn 30 phút. Toàn bữa phải nằm trong giờ địa điểm nếu chọn POI. Không có nhà hàng tin cậy thì “ăn tự túc” với ID trống, vẫn chiếm thời gian, không POI giả.

Phố cổ/khu đi bộ: access point ô tô + một khối nội khu + dwell có nguồn/giả định; không vẽ ô tô xuyên phố cấm rồi gọi khả thi. [Tham khảo multimodal](https://arxiv.org/abs/2207.00097).

Trạng thái: ready theo kiểm tra dữ liệu; provisional nếu giờ/access còn chưa xác minh; insufficient_data khi không có lịch hợp lệ; routing_unavailable khi routing lỗi. Ready vẫn công bố dwell ước lượng và giới hạn giao thông.

## 11. API/web và tương thích

`POST /api/v2/itineraries`: chủ đề ưu tiên, loại loại trừ, chế độ chuyên đề, nhịp, ăn/nghỉ, điểm bắt buộc, dwell override, AHP bốn tiêu chí. Trả role attraction/meal/break, dwell và căn cứ, access/reserve, nguồn rating, lý do chọn/bỏ, dataset/model version.

Giữ API v1 đối chiếu, không đổi nghĩa categories cũ. Web tách list filter và trip preference; hiển thị sao/count/nguồn, giờ unknown, dwell nguồn/ước lượng/user, một điểm lớn, ăn/nghỉ và lý do thiếu điểm. Override luôn gửi backend, không sửa timeline frontend đơn thuần.

## 12. Đánh giá và kiểm thử

### 12.1. Dữ liệu

Đo identity precision, coordinate/access, giờ, rating/count cùng nguồn, duplicate, coverage, freshness, mâu thuẫn. Không gọi completeness là accuracy.

### 12.2. Thuật toán

16 kịch bản (8/thành phố), 4 development và 12 holdout. So nearby, equal weights, crisp, fuzzy cùng pool/data/planner. So planner giữ ranker để tách hiệu ứng. V1 chỉ so ca thuộc phạm vi v1, không dùng ca một điểm lớn để kết luận ranker v1 kém.

Phiếu ẩn phương pháp: sở thích, giá trị POI, đa dạng, dwell, vội, ăn/nghỉ, muốn sử dụng, lỗi/thay điểm. Ghi rõ chủ dự án chấm. AP/NDCG chỉ khi đủ nhãn toàn pool; không suy nhãn POI từ việc thích lịch. Chưa chấm phải NOT RUN.

### 12.3. Regression bắt buộc

- Soft category và chuyên đề; hard exclusion.
- Hai bảo tàng dwell khác; một điểm lớn; không ép ngắn dwell.
- Bữa ăn làm vượt giờ; không nhà hàng vẫn có ăn tự túc.
- Đóng cửa/nghỉ trưa/unknown; qua đêm và ngoại lệ.
- Rating cao ít review; thiếu rating/count; khác nguồn.
- Cha–con, đồng tên, viewport, ID rebuild.
- NoRoute, one-way, OSRM down; Route khác Table.
- Hoán vị AHP, CR sai, TOPSIS 0/hằng.
- API v1/v2 không đổi nghĩa lẫn nhau; web override tính lại backend.

## 13. Lịch 7 ngày

| Ngày | Công việc | Đầu ra |
|---|---|---|
| 1 | Inventory, freeze, workbook, pilot 60 | Manifest/pilot/template |
| 2 | Observations, matching, collector | Catalog trung gian/alias/conflicts |
| 3 | Ưu tiên 50+20 mỗi thành phố, taxonomy/hours/dwell | Chỉ tiêu thực đạt, hàng thiếu |
| 4 | Bốn tiêu chí, rating/AHP/TOPSIS | Core/tests |
| 5 | Planner, điểm lớn, ăn/nghỉ/đệm | API/fixtures |
| 6 | Web, scenarios, chủ dự án chấm | Phiếu/lỗi |
| 7 | Sửa, holdout, freeze | Báo cáo/demo |

Khi thiếu thời gian: đúng thực thể/nguồn → giờ → dwell riêng → sở thích/đa dạng → ăn/nghỉ → cải thiện tìm kiếm. Không bỏ dữ liệu để làm thuật toán phức tạp.

## 14. Checklist bàn giao

- [ ] Inventory toàn bộ nguồn đúng vai trò; workbook/backup không sửa.
- [ ] ID mapping và quan sát có lịch sử.
- [ ] Pilot có bằng chứng hoặc ghi chưa đạt; không tự chấm thay người.
- [ ] Workbook thủ công và validator.
- [ ] Demo không sai thực thể.
- [ ] Soft preference tách hard filter.
- [ ] Dwell không chỉ theo category; rating hiệu chỉnh có nguồn.
- [ ] Ăn/nghỉ, đường về, reserve và ca một điểm lớn.
- [ ] API/web/evaluator chung core v2.
- [ ] Tests, phiếu chấm, giới hạn và hướng dẫn demo.
- [ ] Không tuyên bố thực địa/vượt baseline khi thiếu chứng cứ.

Báo cáo dùng PASS/FAIL/NOT RUN. Giữ tài liệu và kết quả v1 để truy vết; việc lưu kế hoạch này không có nghĩa toàn bộ công việc đã hoàn thành.

## 15. Đặc tả kỹ thuật phải chốt trước khi coding

Phần này là hợp đồng triển khai. Tên bảng, tên trường và ý nghĩa trạng thái chỉ được đổi khi cập nhật tài liệu và migration tương ứng.

### 15.1. Cấu trúc module dự kiến

```text
where2go/
├── v2/
│   ├── models.py             # request/response và validation
│   ├── catalog.py            # đọc catalog hợp nhất, lọc ứng viên
│   ├── observations.py       # mô hình quan sát và provenance
│   ├── matching.py           # đối sánh thực thể, hàng ambiguous
│   ├── taxonomy.py           # primary category và experience tags
│   ├── hours.py              # lịch tuần, ngoại lệ, open/closed/unknown
│   ├── durations.py          # hồ sơ ngắn/thường/dài và user override
│   ├── ranking.py            # rating hiệu chỉnh, AHP, fuzzy, TOPSIS
│   ├── planner.py            # chèn điểm, ăn/nghỉ, local improvement
│   ├── explanations.py       # lý do chọn/bỏ và cảnh báo
│   └── service.py            # orchestration dùng chung API/evaluator
scripts/
├── inventory_sources_v2.py
├── create_manual_template_v2.py
├── validate_manual_data_v2.py
├── import_observations_v2.py
├── match_entities_v2.py
├── build_catalog_v2.py
├── prepare_google_pilot_v2.py
├── import_google_pilot_v2.py
└── evaluate_v2.py
tests/
├── test_v2_data.py
├── test_v2_matching.py
├── test_v2_ranking.py
├── test_v2_planner.py
└── test_v2_api.py
```

`service.py` là điểm gọi duy nhất cho API và evaluator. Notebook chỉ gọi service; không giữ bản sao thuật toán.

### 15.2. Schema SQLite tối thiểu

Catalog v2 dùng file riêng `data/catalog_v2.sqlite`; không migration trực tiếp `data/catalog.sqlite` của v1.

| Bảng | Khóa/chức năng chính |
|---|---|
| `source_files` | `source_file_id`, đường dẫn logic, SHA-256, vai trò, thời điểm nhận, quyền sử dụng |
| `source_records` | `source_record_id`, `source_file_id`, khóa dòng nguồn, raw payload, observed_at |
| `pois` | `poi_id`, trạng thái, tên hiển thị, địa phương hiện hành, parent POI |
| `source_links` | liên kết POI–record, phương pháp match, score, reviewer, trạng thái |
| `field_observations` | POI/record/field/value có kiểu, nguồn, observed/verified, phương pháp |
| `selected_fields` | giá trị catalog đang chọn, observation nguồn, selection reason, build version |
| `opening_intervals` | ngày tuần/ngày cụ thể, open/closed/unknown, khoảng giờ, qua nửa đêm |
| `duration_profiles` | short/typical/long, method, source observation, mức tin cậy |
| `access_points` | tọa độ tiếp cận, loại entrance/parking/manual, thời gian đệm, mức xác minh |
| `ratings` | provider, rating, review count, observed_at, cùng quan sát hay không |
| `poi_categories` | primary category và tags, nguồn ánh xạ taxonomy |
| `builds` | dataset version, model input hashes, thời điểm build và thống kê |

Yêu cầu bắt buộc:

- Raw payload lưu JSON để có thể đọc lại nhưng truy vấn phục vụ dùng cột đã chuẩn hóa.
- `unknown` dùng `NULL` hoặc trạng thái riêng theo schema; không dùng chuỗi rỗng/0 để thay thiếu.
- Mỗi foreign key bật kiểm tra; mỗi build chạy trong transaction và xuất sang file tạm rồi mới thay thế.
- Giá trị JSON không được chứa NaN/Infinity.
- Catalog build phải tái lập từ nguồn + curation; không sửa trực tiếp database sau build.

### 15.3. Quy tắc trạng thái dữ liệu

| Đối tượng | Trạng thái cho phép |
|---|---|
| POI | `usable`, `needs_review`, `excluded` |
| Đối sánh | `confirmed`, `ambiguous`, `unmatched`, `rejected` |
| Hoạt động | `open`, `temporarily_closed`, `permanently_closed`, `unknown` |
| Khoảng giờ | `open`, `closed`, `unknown` |
| Quyền sử dụng | `open_data`, `restricted_internal`, `manual_fact_with_source`, `unknown` |
| Tác vụ collector | `pending`, `running`, `completed`, `blocked`, `failed`, `needs_review` |

Chỉ POI `usable` với entity link `confirmed` được vào pool mặc định. `temporarily_closed` và `permanently_closed` không được xếp lịch. `unknown` không tự đổi thành mở cửa.

### 15.4. Hợp đồng request API v2

```json
{
  "start": {"latitude": 21.0285, "longitude": 105.8542},
  "date": "2026-09-20",
  "start_time": "08:00",
  "end_time": "18:00",
  "location": "Hà Nội",
  "interests": ["lịch sử", "ẩm thực"],
  "preferred_categories": ["museum", "historic"],
  "excluded_categories": [],
  "category_mode": "preferred",
  "pace": "balanced",
  "include_meals": true,
  "include_coffee_break": false,
  "radius_km": 30,
  "required_poi_ids": [],
  "duration_overrides": {},
  "ahp": {
    "criteria_order": ["preference_match", "place_quality", "drive_time", "data_confidence"],
    "comparisons": [1.333333, 2.0, 4.0, 1.5, 3.0, 2.0],
    "uncertainty": [1.2, 1.2, 1.2, 1.2, 1.2, 1.2]
  }
}
```

`comparisons` theo đúng thứ tự cặp `(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)`. API phải trả lỗi 422 có trường/cặp gây lỗi khi giá trị ngoài `[1/9, 9]`, không hữu hạn, không reciprocal sau dựng ma trận hoặc `CR > 0,1`.

Response có tối thiểu:

```text
status, reason, dataset_version, model_version, routing_version,
ranking, blocks, legs, geometry, return_time, reserve_minutes,
warnings, excluded_candidates, data_coverage
```

Mỗi `block` có `role`, thời gian bắt đầu/kết thúc, `poi_id` nullable, dwell/access/wait và nguồn thời lượng. Mỗi điểm bị loại phải có mã lý do ổn định để web/evaluator dùng chung.

### 15.5. Hàm mục tiêu planner

Không dùng một công thức ngầm trong code. Phiên đầu công bố:

```text
utility(route) =
    sum(TOPSIS_score của điểm tham quan)
  + diversity_bonus
  + preferred_theme_bonus
  - extra_drive_penalty
  - waiting_penalty
  - uncertainty_penalty
```

Ràng buộc thời gian, giờ mở cửa, điểm bắt buộc, loại bị cấm, đường đi/về, giới hạn số điểm và dwell là điều kiện bắt buộc; không chuyển thành penalty để thuật toán được phép vi phạm. Hệ số utility nằm trong config có version, được điều chỉnh bằng bốn kịch bản development và đóng băng trước khi chạy holdout.

`diversity_bonus` chỉ thưởng thêm nhóm trải nghiệm mới; không đủ mạnh để đưa một POI chất lượng rất thấp vào lịch. `preferred_theme_bonus` chỉ áp dụng ở chế độ ưu tiên. Chế độ chuyên đề dùng hard filter và không dùng bonus để lách điều kiện.

### 15.6. Mã lý do loại ứng viên

Tối thiểu gồm:

```text
wrong_location, excluded_category, thematic_filter, entity_unconfirmed,
business_closed, duplicate_or_child_overlap, outside_radius,
missing_access_point, no_outbound_route, no_return_route, snap_too_far,
closed_on_date, time_window_conflict, duration_conflict, stop_limit,
same_category_limit, required_poi_conflict, routing_unavailable
```

Chuỗi hiển thị tiếng Việt thuộc lớp web/explanation; evaluator lưu mã ổn định.

## 16. Thứ tự coding và phạm vi từng nhánh công việc

### Giai đoạn A — Nền dữ liệu, chưa đổi hành vi người dùng

1. Chạy baseline v1 và lưu kết quả kiểm thử hiện tại.
2. Inventory toàn bộ `data`, băm SHA-256, phân vai nguồn/đầu ra/fixture.
3. Tạo workbook nhập tay và validator; validator chạy được với workbook trống/mẫu lỗi.
4. Tạo schema observation và importer cho OSM/catalog v1, workbook Google cũ, manual workbook.
5. Tạo matching queue; chưa tự động nhập các bản ghi `Results`, viewport hoặc mâu thuẫn.
6. Build `catalog_v2.sqlite` độc lập và xuất coverage/conflict report.

Giai đoạn A hoàn thành khi cùng một input build hai lần cho cùng canonical ID và cùng giá trị chọn, ngoại trừ timestamp build.

### Giai đoạn B — Thu thập pilot

1. Sinh danh sách 60 seed có strata và lý do chọn.
2. Chạy collector trong thư mục raw riêng; lưu command, image/commit, log và checkpoint.
3. Import thành observations, không ghi thẳng selected fields.
4. Người kiểm duyệt chấm identity và trường dữ liệu; tính tỷ lệ từ phiếu đã chấm.
5. Chỉ mở rộng nếu đạt cổng 95%; nếu FAIL, giữ đầu ra để phân tích và sửa collector.

### Giai đoạn C — Core thuật toán

1. Hoàn thiện taxonomy, duration và hours engine.
2. Viết rating hiệu chỉnh và bốn tiêu chí.
3. Viết kiểm thử AHP/TOPSIS trước khi tích hợp planner.
4. Viết candidate generation và planner trên fixtures nhỏ, deterministic.
5. Nối OSRM và kiểm tra lại Route sau khi chọn phương án.

### Giai đoạn D — API, web và đánh giá

1. Thêm `/api/v2`, giữ v1 không đổi.
2. Web chuyển từng control sang request v2; thời lượng sửa phải round-trip backend.
3. Evaluator gọi `service.py`, chạy bốn phương pháp trên cùng pool.
4. Chạy 4 development, đóng băng config, sau đó mới chạy 12 holdout.
5. Viết báo cáo PASS/FAIL/NOT RUN và hướng dẫn demo.

## 17. Definition of Ready và Definition of Done

### 17.1. Sẵn sàng bắt đầu coding

- [x] Mục tiêu v2, phạm vi địa lý và giới hạn đã chốt.
- [x] Vai trò nguồn, nguyên tắc provenance và quyền sử dụng đã mô tả.
- [x] Taxonomy, duration profile, bốn tiêu chí và trạng thái lịch đã chốt ở mức đặc tả.
- [x] Schema tối thiểu, API request/response và mã lý do đã có.
- [x] Baseline v1 được chạy lại trên máy coding và kết quả ghi tại mục 18.1.
- [ ] Tạo nhánh/commit mốc trước v2 để có thể đối chiếu.
- [ ] Tạo workbook manual thực tế và validator đầu tiên.
- [ ] Chốt commit/image cụ thể của collector sau khi kiểm tra release hiện hành.

Ba mục đầu còn thiếu là công việc mở đầu ngày 1, không phải lý do trì hoãn phần schema/importer.

### 17.2. Hoàn thành một hạng mục code

Một hạng mục chỉ được đánh dấu DONE khi có:

- Code dùng chung, không sao chép logic sang notebook/web/evaluator.
- Kiểm thử có ý nghĩa cho hành vi và ca lỗi chính.
- Dữ liệu đầu ra có version/provenance và build lại được.
- Tài liệu cập nhật nếu schema/API/công thức thay đổi.
- Kết quả chạy ghi PASS/FAIL/NOT RUN; không suy PASS từ việc command không báo lỗi.

## 18. Lệnh chuẩn bị phiên coding

Chạy từ thư mục gốc dự án trong PowerShell:

```powershell
git status --short
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
docker ps --filter "name=where2go-osrm"
Invoke-RestMethod 'http://127.0.0.1:5001/route/v1/driving/105.85,21.03;105.84,21.04'
```

Sau khi có script ngày 1, thứ tự dự kiến:

```powershell
.venv\Scripts\python.exe scripts/inventory_sources_v2.py
.venv\Scripts\python.exe scripts/create_manual_template_v2.py
.venv\Scripts\python.exe scripts/validate_manual_data_v2.py data/manual/poi_enrichment_v2.xlsx
.venv\Scripts\python.exe scripts/import_observations_v2.py
.venv\Scripts\python.exe scripts/match_entities_v2.py
.venv\Scripts\python.exe scripts/build_catalog_v2.py
```

Tên lệnh ở khối thứ hai là hợp đồng dự kiến của kế hoạch; chúng chưa tồn tại cho đến khi bước coding tương ứng hoàn thành. README triển khai phải cập nhật trạng thái từng lệnh, không để người đọc hiểu nhầm là đã chạy được.

### 18.1. Baseline đã xác nhận ngày 17/09/2026

| Kiểm tra | Kết quả | Trạng thái |
|---|---|---|
| Test v1 | 23 test pass; 1 cảnh báo deprecation từ Starlette TestClient | PASS |
| Dependency | `pip check`: không có dependency hỏng | PASS |
| Container | `where2go-osrm` đang chạy tại `127.0.0.1:5001` | PASS |
| Tuyến thử | OSRM trả `Ok`, 2.868,4 m, 239,7 giây | PASS |
| Workbook manual v2 | Chưa tạo | NOT RUN |
| Collector pilot | Chưa chọn pin và chưa chạy | NOT RUN |
| Catalog/API/planner v2 | Chưa coding | NOT RUN |

Cảnh báo deprecation thuộc dependency kiểm thử hiện tại; chưa làm test thất bại. Khi bắt đầu coding cần giữ mốc 23 test v1 pass và thêm test v2 độc lập, tránh sửa test v1 để che regression.
