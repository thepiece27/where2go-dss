# Bản nộp Where2Go DSS

Giải nén ZIP, mở terminal tại thư mục `where2go-dss` rồi chạy bằng Python 3.13:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.lock.txt
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Mở http://127.0.0.1:8000. Không cần Node build.

- Bản nộp giữ cả hai catalog SQLite, dữ liệu nguồn/backup, báo cáo, notebook có output, paper, bản đồ local và bằng chứng kiểm tra hiện có.
- Báo cáo tổng hợp: `docs/tong_hop_khoa_hoc_poi_rs.md`. Bốn ảnh giao diện: `docs/assets/screenshots/`.
- Không đóng gói lịch sử `.git`, môi trường Python, cache kiểm thử/biên dịch, hồ sơ trình duyệt hay thư mục dữ liệu riêng tư.
- **Docker container/volume OSRM và PBF gốc không nằm trong ZIP này.** Manifest định tuyến không thay thế dữ liệu đường đi. Trên máy mới, muốn tính lịch trình phải chuẩn bị Docker và OSRM đúng snapshot theo `docs/setup_va_khoi_dong_demo.md`; không cần sửa manifest để bỏ qua kiểm tra. Khi chưa có OSRM, gợi ý POI có thể dùng khoảng cách địa lý và lịch trình chưa hoạt động đầy đủ.
- Ảnh POI và lớp bản đồ online cần kết nối mạng; ảnh có thể hiện ô dự phòng khi nguồn ngoài không tải được.
- Dữ liệu có nguồn Google được giữ cho bài nộp nội bộ; không coi đây là quyền phát hành dataset công khai. Giữ attribution và giấy phép của nguồn tương ứng.

Để tạo lại ZIP sau khi sửa bài, chạy `python scripts/package_submission.py`. ZIP mới nằm trong `submission/`; không nén lồng thư mục này vào một ZIP khác. Script kiểm tra CRC và các tệp bắt buộc sau khi đóng gói; không thay đổi nội dung dữ liệu hoặc báo cáo.
