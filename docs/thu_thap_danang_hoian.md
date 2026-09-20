# Thu thập du lịch Đà Nẵng – Hội An

Phạm vi: Đà Nẵng cũ (đất liền), Hội An và Cù Lao Chàm. Giữ dữ liệu cũ; đợt này không thu thêm nơi thờ tự, café/nhà hàng đại trà, bar/pub, spa, đơn vị lữ hành hoặc hạ tầng phụ trợ như văn phòng quản lý, bãi đỗ xe, nhà vệ sinh.

Kết quả cập nhật: [báo cáo trước/sau](../data/reports/v2/danang_campaign/report.md), [trạng thái thu thập](../data/reports/v2/danang_campaign/collection.json). **Chỉ `saturated` mới nghĩa là hoàn thành điều kiện bão hòa đã định; `running`, `paused`, `interrupted`, `blocked`, `incomplete_queries` đều chưa hoàn tất.**

## Cách chạy

PowerShell ở gốc dự án, dùng `.venv` hiện có. Chỉ chạy một crawler tại một thời điểm.

```powershell
# Chuẩn bị ranh giới và baseline lần đầu; không ghi đè baseline của snapshot cũ.
.venv\Scripts\python.exe -X utf8 scripts\prepare_danang_campaign.py

# Pilot mới: 20 điểm thuộc 5 nhóm, ít nhất 19 điểm được chấp nhận.
.venv\Scripts\python.exe -X utf8 scripts\crawl_danang.py --pilot-only

# Tự tiếp tục từ checkpoint, không đặt quota tổng POI.
.venv\Scripts\python.exe -X utf8 scripts\crawl_danang.py

# Hoặc chạy trọn quy trình crawl -> kiểm tra ảnh -> staging/audit -> publish -> báo cáo.
.venv\Scripts\python.exe -X utf8 scripts\run_danang_campaign.py

# Chạy nền không mở cửa sổ, log và PID trong artifacts/danang_campaign*.
.venv\Scripts\python.exe -X utf8 scripts\run_danang_campaign.py --background
```

`--max-queries 6` giới hạn một phiên làm việc, không đánh dấu bão hòa. Muốn tạm dừng an toàn sau địa điểm đang thu:

```powershell
New-Item data\enrichment\danang_hoian\PAUSE -ItemType File -Force
```

Trước khi chạy tiếp, xóa đúng file `PAUSE`. Khi gặp chặn truy cập, crawler dừng; không tự đổi proxy, tài khoản hoặc vượt CAPTCHA. Chỉ dùng `--resume-after-block` sau khi đã khôi phục truy cập bình thường. Các lỗi tạm có tối đa ba lần thử cho cùng phiên bản collector; sửa collector tạo revision mới và giữ nguyên mọi quan sát cũ.

## Phạm vi và tìm điểm mới

Ranh giới trong `data/curation/danang_hoian_scope.geojson` được trích từ 19 xã/phường của file địa giới kế thừa, kèm SHA-256 và tên từng thành viên trong ZIP. Chưa xác minh độc lập nguồn xuất bản ban đầu của ZIP. Hoàng Sa và các xã/phường Quảng Nam cũ ngoài Hội An/Tân Hiệp không thuộc phạm vi này.

Sáu phường ven biển có dung sai hình học 25 m để nhận ghim bãi tắm nằm sát mép polygon. Đây là dung sai vận hành có ghi trong metadata, không phải điều chỉnh địa giới hành chính. Không mở rộng biên Hải Vân; điểm vượt ranh giới vẫn chờ duyệt.

Discovery chạy sáu nhóm luân phiên trên ô 2 km đô thị/ven biển, 5 km vùng thưa. Truy vấn tiếng Việt/Anh đổi qua từng vòng. Kết quả bị giới hạn được chia ô nhỏ đến 500 m; nếu vẫn thiếu thì ghi `limited`, không coi đã quét xong. Dừng cuộn vì không thay đổi DOM không đồng nghĩa đã hết kết quả.

Điều kiện bão hòa: mọi truy vấn hoàn thành, đã thử đủ biến thể song ngữ, hai vòng liên tiếp mỗi nhóm có tỷ lệ danh tính mới dưới 1%, không còn thực thể bị lỗi thu thập. Không khẳng định danh mục bao phủ mọi địa điểm tồn tại ngoài thực tế.

## Xác nhận và nhập catalog

Mỗi trang phải có danh tính Google và tọa độ thực thể trong phạm vi. Tọa độ tâm bản đồ không được sử dụng. Tên tiếng Anh được đối chiếu bằng alias; cùng tên nhưng khác vị trí không tự ghép. Nhãn Google nguyên bản, URL, thời điểm quan sát và lý do quyết định đều được lưu.

Nguồn Google có thể tự mâu thuẫn. `data/curation/danang_campaign_reviews.json` giữ quyết định chờ đối chiếu; ví dụ trang tên cảng Hòn Tằm nhưng địa chỉ Đà Nẵng và website bán vé Nha Trang không được chấp nhận chỉ vì ghim nằm trong ranh giới.

Giữ các điểm mới có bằng chứng Google dù chưa tồn tại trong OSM. Ghép với catalog theo external ID hoặc tên/loại/tọa độ; trường hợp mơ hồ chờ duyệt. Cổng chất lượng gợi ý không giảm. Thiếu giờ, giá vé, mô tả hay rating phải để thiếu. Thời lượng mặc định là ước lượng.

Ảnh lấy từ trang thực thể: tối đa bốn URL, kiểm tra nội dung/kích thước, loại avatar/logo/ảnh dùng chung đáng ngờ. Không tạo ảnh giả cho địa điểm. URL ảnh có thể hết hạn và cần kiểm tra lại. Quan sát Google giữ `restricted_internal`.

## File kết quả

| File/thư mục | Nội dung |
|---|---|
| `data/enrichment/danang_hoian/checkpoint.json` | Truy vấn, candidate, vòng quét, pilot và trạng thái |
| `data/enrichment/danang_hoian/observations.json` | Mọi lần thu thập và tái duyệt, có thời điểm/revision |
| `data/enrichment/danang_hoian/queries_round_*.json` | Truy vấn các vòng đã hoàn thành |
| `data/enrichment/danang_hoian/review_queue.json` | Lỗi, ngoài phạm vi, loại bị loại hoặc cần duyệt |
| `data/enrichment/accepted-danang-hoian.json` | Quan sát được chấp nhận để build |
| `data/private/danang_hoian/` | CSV/XLSX quan sát nội bộ |
| `data/reports/v2/danang_campaign/` | Baseline, coverage CSV, báo cáo Markdown/JSON |

## Publish và kiểm chứng

Sau khi crawler dừng, có thể chỉ chạy hoàn thiện snapshot:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\run_danang_campaign.py --finalize-only
```

Quy trình kiểm tra ảnh từ các quan sát đã chấp nhận trước khi build để tránh build hai lần. Catalog được audit trên staging, có backup trước publish. API phiên bản mới tự nạp catalog khi file active được thay; server đang chạy mã cũ cần khởi động lại một lần để nhận thay đổi này. Bản đồ nền/OSRM tiếp tục dùng PBF hiện có; thêm POI không phải cập nhật mạng đường.

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check where2go scripts tests
.venv\Scripts\python.exe -X utf8 scripts\report_danang_campaign.py
```

Các tài liệu nghiên cứu baseline giữ số liệu lịch sử và nhãn snapshot riêng. Khi publish snapshot mới, chạy lại các evaluator trước notebook; không bỏ assertion kiểm tra version để trộn dữ liệu. Kiểm thử phần mềm và độ phủ nguồn không thay cho đánh giá chất lượng gợi ý bằng người dùng.
