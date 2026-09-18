# Dataset Where2Go DSS v2

Phiên bản: `v2-ae66988a1053d0de`

Sinh lúc: `2026-09-18T08:05:16.805404+00:00`

- `pois.csv`: catalog phẳng, một dòng cho mỗi POI.
- `opening_hours.csv`: các khoảng giờ cấu trúc; `day_of_week` dùng 0=Thứ Hai đến 6=Chủ Nhật.
- `ratings.csv`: rating và số review theo cùng quan sát khi `same_observation=1`.
- `duration_profiles.csv`: ba mức thời lượng; `category_default` chỉ là fallback thiết kế.
- `access_points.csv`: tọa độ tiếp cận; `verified=0` nghĩa chưa được xác minh thủ công.
- `sources.csv`: nguồn, checksum, vai trò và quyền sử dụng.
- `summary.json`: coverage toàn catalog và tập ưu tiên 70 POI mỗi thành phố.

Catalog chuẩn vẫn là `data/catalog_v2.sqlite`, chứa provenance chi tiết. Quan sát Google đang chờ kiểm duyệt được xuất riêng tại `data/private/google_enrichment_v2.csv` và `data/private/google_opening_hours_v2.csv`; hai file này bị Git bỏ qua. Dữ liệu Google Maps có trạng thái `restricted_internal`; không coi thư mục xuất này là dataset công khai được phép tái phân phối.
