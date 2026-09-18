# Where2Go DSS — POI Recommendation System

Hệ gợi ý POI **dựa trên nội dung và ngữ cảnh, kết hợp ra quyết định đa tiêu chí** tại Hà Nội/Đà Nẵng. Nhập sở thích, vị trí, ngày đi và mẫu ưu tiên để nhận Top-10 có giải thích. Có thêm trang khám phá toàn quốc và lập lịch cho tối đa 12 địa điểm đã chọn.

Ba trang: **Gợi ý POI `/` → Khám phá `/explore` → Lịch trình `/itinerary`**. Danh sách đã chọn dùng chung, nháp lưu theo địa phương trên trình duyệt. Giao diện sáng, responsive, không cần Node build.

Thuật toán: taxonomy + TF-IDF/cosine → ứng viên từ ba nguồn → AHP–TOPSIS trên sở thích, chất lượng, di chuyển và bằng chứng. OSRM đầy đủ dùng giây; thiếu dữ liệu dùng km đường chim bay cho toàn pool và ghi rõ. Chưa học từ lịch sử tương tác. Fuzzy AHP mặc định trùng AHP thường, không được coi là cải thiện đã chứng minh.

Đã có 96 lượt đối chiếu trên 16 bối cảnh và notebook có output. **Phiếu relevance của nhóm chưa chấm; chất lượng gợi ý với người dùng chưa được kiểm chứng.**

## Tài liệu cho báo cáo và bảo vệ

| Tài liệu | Nội dung |
|---|---|
| **[Báo cáo dự án hoàn chỉnh](docs/bao_cao_du_an_poi.md)** | Bài toán, kiến trúc, nguồn/crawl/ghép dữ liệu, chất lượng, công thức, lý do lựa chọn, thực nghiệm và đối chiếu hai paper |
| **[Hướng dẫn chạy](docs/huong_dan_chay.md)** | Chạy từ catalog có sẵn, dựng mới, OSRM, notebook, kiểm thử, thu thập và xử lý lỗi |
| **[Kịch bản bảo vệ 25–30 phút](docs/kich_ban_bao_ve.md)** | 18 slide, 27 phút, lời nói, demo, phụ lục và câu hỏi phản biện |
| **[Notebook đã thực thi](notebooks/phan_tich_du_lieu_poi.ipynb)** | Phân tích dữ liệu thực, 14 biểu đồ, bảng kết quả và kiểm chứng toán |
| [Biểu đồ PNG](docs/assets/poi/) · [Bảng/JSON phân tích](data/reports/analysis/) | Tài nguyên đưa vào báo cáo/slide, checksum đầu vào |
| [Hai bài báo gốc](paper/) | LORE 2014 và Contextualized Point-of-Interest Recommendation 2020 |

## Chạy nhanh khi đã có dữ liệu runtime

Python **3.13**, PowerShell tại thư mục gốc:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.lock.txt
.venv\Scripts\python.exe -m uvicorn where2go.api:app --host 127.0.0.1 --port 8000
```

Mở **http://127.0.0.1:8000**; OpenAPI tại **http://127.0.0.1:8000/docs**. Cần `data/catalog_v2.sqlite`; Git clone mới có thể chưa có file này. Muốn tạo lịch có đường đi, cần OSRM và manifest đúng snapshot:

```powershell
# Cần Docker Desktop/WSL2; lần đầu tải và tiền xử lý PBF.
.venv\Scripts\python.exe scripts\setup_osrm.py --download
```

OSRM dùng **127.0.0.1:5001**. Hướng dẫn dựng catalog đầy đủ và khôi phục runtime ở [đây](docs/huong_dan_chay.md). Frontend tĩnh không cần bước build Node.

## Chạy lại phân tích dữ liệu

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
.venv\Scripts\python.exe -X utf8 scripts\run_analysis.py
```

Notebook đọc CSV và artifact thực nghiệm đã xuất, không cần Docker/API/crawl. Snapshot **`v2-ae66988a1053d0de`**: 16.018 POI, 15.245 khám phá được, 1.475 qua cổng chất lượng trên toàn catalog; luồng gợi ý hai địa bàn có 1.235 POI trước lọc ngày/bán kính. Chỉ 86 POI có rating–review hợp lệ. Đây là dữ liệu prototype có giới hạn, chưa được xác minh thực địa đầy đủ.

## Cấu trúc

```text
where2go/              API, mô hình chung, routing, lõi v1 còn được dùng
  v2/                  Catalog, chất lượng, ranking, planner và luồng chọn lịch
web/                   HTML/CSS/JS và Leaflet
scripts/               Build, audit, export, collection, evaluation, smoke
tests/                 Kiểm thử thuật toán, dữ liệu, routing và API
data/curation/         Quy tắc, ID và quyết định đối chiếu
data/reports/v2/       Dataset xuất và báo cáo nghiên cứu tình huống
data/reports/analysis/ Bảng, checksum và kết quả notebook
notebooks/             Phân tích có output
docs/                  Báo cáo, hướng dẫn, kịch bản và biểu đồ
paper/                 Hai PDF tham khảo
artifacts/             Đầu ra kiểm tra tạm, không theo dõi trong Git
```

API chính dùng `/api/v2/recommendations` và `/api/v2/trip-suggestions`. `/api/v2/trip-recommendations` giữ vai trò tương thích. Endpoint `/api/v2/itineraries` giữ planner nghiên cứu để đối chiếu. Không xóa lõi v1 tùy tiện: v2 còn dùng model, TOPSIS, chuẩn hóa, routing và catalog nền.

## Kiểm tra

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m ruff check where2go scripts tests
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
node --check web\common.js
node --check web\recommend.js
node --check web\explore.js
node --check web\app.js
node --check web\map.js
node --check web\dataset.js
```

Các bài kiểm tra dùng dữ liệu local cần các fixture/runtime tương ứng. Evaluator với OSRM thật và smoke trình duyệt được hướng dẫn riêng; kiểm thử phần mềm không thay đánh giá người dùng. Kết quả lần làm sạch nằm trong [bản ghi kiểm chứng](data/reports/analysis/verification.json).

Giữ bất biến các workbook nguồn/backup, PBF, địa giới, curation và quan sát cần tái lập. Catalog là dữ liệu phục vụ; CSV/XLSX trong `data/reports/v2/dataset/` là dẫn xuất. Dữ liệu Google giữ **`restricted_internal`**; không coi export nội bộ là dataset được phép phát hành. Dữ liệu OSM giữ attribution và ODbL 1.0.
