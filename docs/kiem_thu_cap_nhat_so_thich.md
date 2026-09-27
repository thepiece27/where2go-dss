# Kiểm thử đổi sở thích tại Đà Nẵng — 21/09/2026

> Bản ghi lịch sử của policy 1.1. Policy 3.0 đã thay hợp đồng ý định và được kiểm chứng riêng; không dùng số bên dưới như kết quả hiện hành.

Đã sửa lỗi chọn **tâm linh** nhưng nhóm mặc định loại hết đền/chùa trước khi xếp hạng. Đây là xung đột bộ lọc, không phải cache danh sách gợi ý. Local storage lưu nháp lựa chọn; mỗi lần bấm **Nhận gợi ý**, web gửi yêu cầu mới. Đổi tiêu chí xóa kết quả cũ và yêu cầu bấm nút để cập nhật.

## Thay đổi

- Với nhóm **Tham quan và ngoài trời**, chọn chủ đề/nhập cụm **tâm linh** sẽ cho phép thêm loại `temple` vào tập ứng viên; có hỗ trợ không dấu và chữ hoa.
- Chọn rõ **Loại hình ưu tiên** cũng cho phép xét loại đó dù bị loại bởi nhóm mặc định, ví dụ đền/chùa hoặc cà phê. Web hiển thị thông báo nhóm được xét thêm.
- Không đổi phạm vi tọa độ, bán kính, điều kiện ngày mở cửa, trạng thái hoạt động, hay việc loại POI đã chọn. Quy tắc thu thập dữ liệu và trang Khám phá giữ nguyên.
- Chính sách API chuyển từ `poi-recommendation-1.0` sang `poi-recommendation-1.1`.

## Ca đã chạy trên web thật

Chromium thao tác một phiên trình duyệt liên tục với API `http://127.0.0.1:8000`, catalog `v2-c3ad315d02c5356a`. Không mock kết quả/API. Tài nguyên ngoài localhost bị chặn để phép thử tập trung vào sở thích; **không dùng lần chạy này để kết luận ảnh tải tốt**.

Điều kiện ban đầu: Đà Nẵng, phạm vi `danang_hoian`, ngày đi 21/09/2026, tâm `(16.0544, 108.2022)`, bán kính 30 km, nhóm Tham quan và ngoài trời, ưu tiên Cân bằng. Các ca sau nối tiếp ca trước; những thay đổi cụ thể ghi trong bảng. Khi đổi chủ đề, bỏ chủ đề cũ rồi bật chủ đề mới; nút chủ đề cho phép chọn nhiều.

**Lưu ý địa lý:** phạm vi mặc định bao gồm Hội An, không phải chỉ Đà Nẵng cũ. Đối chiếu đa giác phát hiện P03/P05/P12 có 2 điểm Hội An, P06/P09 có 1, P08 có 4. Không dùng các ca này để tuyên bố toàn bộ kết quả ở Đà Nẵng. **P13** là ca tâm linh đã kiểm tra từng tọa độ, toàn bộ kết quả thuộc vùng `danang`.

| Ca | Thao tác và kết quả quan sát sau sửa | Ý nghĩa |
| --- | --- | --- |
| P01 | Chưa khai báo sở thích: 10 gợi ý, không có đền/chùa | Bộ lọc mặc định vẫn hoạt động |
| P02 | Chọn thiên nhiên: 8 công viên, 2 bãi biển | Tập kết quả phù hợp nhóm thiên nhiên trong ca này |
| P03 | Bỏ thiên nhiên, chọn tâm linh: **10 đền/chùa**, đầu tiên Chùa Thuận Thành | Trước sửa, cùng thao tác trả **8 bãi biển, 1 điểm tham quan, 1 khu vui chơi**, không có đền/chùa |
| P04 | Bỏ tâm linh, chọn lại thiên nhiên: đúng danh sách và thứ tự P02 | Không giữ nhầm kết quả tâm linh; kết quả lặp lại cho cùng yêu cầu là hợp lệ |
| P05 | Bỏ thiên nhiên, nhập `TAM LINH`: 10 đền/chùa | Ô nhập tự do nhận từ khóa không dấu, chữ hoa |
| P06 | Xóa ô nhập, chọn loại hình đền/chùa: 10 nơi thờ tự | Lựa chọn loại hình không còn bị nhóm mặc định vô hiệu hóa |
| P07 | Đổi loại hình thành cà phê: 10 quán cà phê, đầu tiên Trình cà phê | Cùng lỗi xung đột được sửa cho lựa chọn loại hình cụ thể |
| P08 | Đổi loại hình thành bảo tàng: 10 bảo tàng, đầu tiên Bảo tàng Mỹ thuật Đà Nẵng | Thay loại hình có tác động rõ lên kết quả |
| P09 | Bỏ loại hình, bật tâm linh, đổi sang Đi gần: 10 nơi thờ tự; thứ tự thay đổi | Cùng tập Top-10 có thể đổi thứ tự khi thay trọng số, không phải cache |
| P10 | Giữ tâm linh/Đi gần, thu bán kính 1 km: chỉ Công viên 29 tháng 3 | **Hạn chế:** không có đền/chùa đủ điều kiện trong bán kính; hệ thống vẫn đưa phương án gần với điểm khớp sở thích 0 |
| P11 | Giữ 1 km, đổi tâm sang `(16.0630, 108.2450)`: 1 nơi thờ tự, 1 công viên, 1 chợ, 2 biển | Đứng đầu là Tượng Phật Quan Âm - Chùa Mỹ Khê; vị trí làm đổi tập ứng viên, những phương án sau chưa khớp tâm linh |
| P12 | Giữ tâm gần Mỹ Khê và Đi gần, mở lại 30 km, màn hình 390 px: 8 nơi thờ tự, 2 biển | Sở thích là ưu tiên mềm; khoảng cách và chất lượng vẫn tác động. Không tràn ngang trên màn hình thử |
| P13 | Trở lại tâm `(16.0544, 108.2022)`, Cân bằng, tâm linh, bán kính 15 km: **6 nơi thờ tự, 2 công viên, 1 chợ, 1 biển** | Cả 10 tọa độ thuộc Đà Nẵng; 6 kết quả đầu đều là nơi thờ tự. Vẫn có phương án bổ sung không khớp tâm linh |

Tất cả 13 ca nhận HTTP 200, danh sách DOM khớp ID trong phản hồi, tôn trọng bán kính và không phát sinh lỗi JavaScript. Sau sửa sở thích, danh sách cũ được xóa trước khi bấm gửi lại. P03 tăng số POI đủ điều kiện từ **126 lên 137**, chỉ bổ sung 11 nơi thờ tự đủ điều kiện; không mở toàn bộ nhà hàng/cà phê cùng lúc.

Các ca P01–P09, P12–P13 dùng khoảng cách đường chim bay vì không có ma trận đường đi đầy đủ cho toàn bộ tập ứng viên. P10–P11 dùng thời gian đường đi. Không diễn giải khoảng cách đường chim bay thành thời gian lái xe.

## Xác minh và bằng chứng

- **134 test Python PASS**, gồm 5 ca hồi quy mới. Cả 5 ca mới đã FAIL trước sửa và PASS sau sửa; kiểm tra thêm rằng mở nhóm đền/chùa không bỏ qua phạm vi, bán kính, đóng cửa hoặc điểm đã chọn.
- Ruff, kiểm tra cú pháp `web/recommend.js` và `git diff --check`: PASS.
- [Bằng chứng trước sửa](../artifacts/preference_updates/before/report.json), [bằng chứng sau sửa](../artifacts/preference_updates/after/report.json): có request, phản hồi đầy đủ, loại hình và kết quả kiểm tra từng ca.
- [Ảnh tâm linh trước sửa](../artifacts/preference_updates/before/spiritual.png), [sau sửa](../artifacts/preference_updates/after/spiritual.png), [màn hình nhỏ](../artifacts/preference_updates/after/spiritual-mobile.png).

Chạy lại từ thư mục gốc khi API đã bật:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\verify_preference_updates.py
.venv\Scripts\python.exe -X utf8 -m pytest -q
```

Script nằm tại [scripts/verify_preference_updates.py](../scripts/verify_preference_updates.py). Bằng chứng thực thi trong `artifacts/` là tệp cục bộ, có thể không có trong bản clone Git khác.

Kết luận giới hạn ở lỗi bộ lọc và sự cập nhật kết quả. Không cam kết mọi gợi ý đều đúng sở thích: thuật toán còn trộn các tiêu chí, chưa hiểu phủ định như người thật, và vẫn có thể trả phương án không khớp khi điều kiện hẹp. Đây là thao tác trình duyệt tự động mô phỏng người dùng, không phải khảo sát người dùng độc lập.
