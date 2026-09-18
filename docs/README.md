# Tài liệu Where2Go DSS

Đọc theo thứ tự dưới đây để chuẩn bị báo cáo và buổi bảo vệ:

1. **[Báo cáo dự án POI](bao_cao_du_an_poi.md)** — tài liệu nội dung chính: bài toán, nguồn/crawler, EDA, toàn bộ công thức cốt lõi, thuật toán, thực nghiệm, hai paper và hướng phát triển.
2. **[Kịch bản bảo vệ](kich_ban_bao_ve.md)** — 18 slide, phần nói chính 27 phút, lời nói và hình nên dùng, demo ba phút, phụ lục và câu hỏi phản biện.
3. **[Hướng dẫn chạy](huong_dan_chay.md)** — môi trường, API/OSRM, dựng dữ liệu, notebook, kiểm thử và vận hành.

[Notebook có kết quả](../notebooks/phan_tich_du_lieu_poi.ipynb) · [14 biểu đồ PNG](assets/poi/) · [Bảng phân tích và kiểm chứng](../data/reports/analysis/) · [PDF nguồn](../paper/).

## Tài liệu cũ đã được hợp nhất

| Tài liệu đã xóa | Nội dung chuyển đến |
|---|---|
| `fuzzy_ahp.md` | Báo cáo §7–8: tiêu chí, công thức, hai planner và giới hạn |
| `huong_dan_trien_khai.md` | Hướng dẫn chạy: runtime, dữ liệu, kiểm tra và xử lý lỗi |
| `ket_qua_trien_khai_v2.md` | Báo cáo §5–6, §9: thu thập, EDA, thực nghiệm và mức bằng chứng |
| `du_lieu_hop_nhat_va_ban_do.md` | Báo cáo §4–5; hướng dẫn build, ảnh, publish/rollback và bản đồ |
| `ke_hoach_nang_cap_du_lieu_va_lich_trinh_v2.md` | Báo cáo §12–13: lựa chọn hiện tại và hướng phát triển có điều kiện |
| `trai_nghiem_lua_chon_lich_trinh.md` | Báo cáo §2–3, §8–9; hướng dẫn API và kịch bản demo |

Lịch sử bản cũ ở Git. `data/reports/v2/dataset/README.md` được giữ vì là mô tả bộ export do pipeline sinh. Báo cáo mới phân biệt **đã triển khai**, **số liệu paper**, **kết quả chạy** và **đề xuất**, tránh dùng kế hoạch cũ như bằng chứng đã hoàn thành.
