# Kết quả tăng cường dữ liệu Đà Nẵng – Hội An

Catalog: `v2-c3ad315d02c5356a`.
Trạng thái crawl: **paused**. Đạt bão hòa: **chưa**.
Phạm vi: Đà Nẵng cũ, Hội An, Cù Lao Chàm; 2625 POI so với 2545 ở baseline.

Các tổng catalog bao gồm dữ liệu cũ. Số quan sát không phải số địa điểm mới.

| Loại | Trước | Sau | Chênh lệch | Ảnh hợp lệ | Đủ điều kiện gợi ý |
|---|---:|---:|---:|---:|---:|
| attraction | 49 | 63 | 14 | 24 | 25 |
| beach | 16 | 33 | 17 | 23 | 21 |
| bridge | 0 | 5 | 5 | 5 | 5 |
| cafe | 1106 | 1106 | 0 | 5 | 147 |
| campground | 0 | 2 | 2 | 2 | 2 |
| craft_village | 5 | 5 | 0 | 3 | 3 |
| gallery | 4 | 4 | 0 | 0 | 1 |
| historic | 25 | 26 | 1 | 3 | 3 |
| market | 51 | 58 | 7 | 24 | 15 |
| museum | 21 | 25 | 4 | 14 | 14 |
| nature_area | 17 | 19 | 2 | 4 | 4 |
| old_quarter | 1 | 1 | 0 | 1 | 1 |
| park | 36 | 51 | 15 | 17 | 17 |
| performance_venue | 1 | 1 | 0 | 0 | 0 |
| playground | 0 | 2 | 2 | 2 | 2 |
| restaurant | 1084 | 1084 | 0 | 5 | 272 |
| temple | 116 | 116 | 0 | 15 | 11 |
| theme_park | 5 | 6 | 1 | 3 | 5 |
| trailhead | 0 | 1 | 1 | 1 | 1 |
| viewpoint | 7 | 9 | 2 | 2 | 2 |
| walking_street | 0 | 3 | 3 | 3 | 3 |
| water_park | 0 | 2 | 2 | 2 | 2 |
| waterfall | 0 | 2 | 2 | 2 | 2 |
| zoo | 1 | 1 | 0 | 0 | 0 |

## Tính đầy đủ

Trạng thái truy vấn: `{'complete': 7, 'unresolved': 2, 'pending': 1479}`.
Lý do chờ duyệt/loại: `{'outside_scope_or_missing_identity': 4, 'ambiguous_catalog_match': 6, 'unknown_category': 23, 'excluded_service': 18, 'source_location_conflict': 1, 'generic_name_needs_review': 1, 'excluded_category': 2, 'place_of_worship': 4}`.
Không quy đổi kết quả Maps thành cam kết đã thu mọi điểm ngoài thực tế. Ảnh hợp lệ nghĩa là URL đã được kiểm tra nội dung và gắn với trang thực thể, không phải xác minh thực địa.

## Tiếp tục và tái lập

Xem `docs/thu_thap_danang_hoian.md`; checkpoint trong `data/enrichment/danang_hoian/`, CSV/XLSX quan sát trong `data/private/danang_hoian/`.
