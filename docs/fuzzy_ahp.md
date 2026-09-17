# Phương pháp của phiên bản lịch trình Where2Go DSS

Tài liệu này mô tả đúng lõi `where2go/ranking.py` và `where2go/planner.py`. Mô hình hybrid hành vi trước đây được lưu ở [bản lịch sử](archive/fuzzy_ahp_legacy.md); hành vi mô phỏng không tham gia sản phẩm hiện tại.

## 1. Tiêu chí và tập ứng viên

Thứ tự cố định: `preference_match` (benefit), `drive_time` (cost, giây), `data_confidence` (benefit).

- Sở thích: bỏ dấu, chữ thường, tách token. Gọi Q là tập token sở thích, T là token tên + mô tả + từ khóa loại hình. Điểm bằng |Q ∩ T| / |Q|; Q rỗng cho điểm 1 cho tất cả. Đây là phép khớp từ đơn giản, chưa hiểu ngữ nghĩa; từ chung có thể làm điểm cao hơn mức phù hợp thực tế.
- Thời gian lái xe: OSRM Table từ xuất phát tới POI, không thay bằng Haversine.
- Độ tin cậy quy tắc: 0,6 cho bản ghi OSM đủ điều kiện cơ bản; +0,2 nếu lịch tuần phân tích được; +0,2 nếu có biên bản đối soát nguồn, tối đa 1. Không phải xác suất đúng hoặc điểm chất lượng trải nghiệm. Đối soát có hỗ trợ công cụ vẫn được ghi đúng loại, không giả là khảo sát thực địa.

Lọc địa phương, loại hình, chuỗi tìm kiếm, trạng thái usable và bán kính trước. Hợp nhất hai danh sách theo nội dung và khoảng cách thẳng, tối đa 40 ứng viên. Sau Table, loại điểm không có đường đi/về hoặc snap >300 m. Pool còn lại cố định cho mọi baseline và TOPSIS. Bán kính mặc định/các từ khóa/thời lượng nằm trong `config.py`; bản ghi chưa đối soát không được mô tả là đã xác minh.

## 2. AHP và nhất quán

Ba đầu vào a, b, c lần lượt là preference/drive, preference/confidence và drive/confidence. Mỗi giá trị thuộc [1/9, 9]; API dựng ma trận:

```text
A = [ 1    a    b ]
    [ 1/a  1    c ]
    [ 1/b  1/c  1 ]
```

Ma trận phải hữu hạn, dương, đường chéo 1 và a_ij × a_ji = 1. Với n=3:

```text
CI = (lambda_max(A) - 3) / 2
CR = CI / 0.58
```

Chỉ nhận CR ≤0,1. Mặc định a=b=c=1 là trọng số bằng nhau do thiết kế, không phải ý kiến chuyên gia.

## 3. Fuzzy geometric mean

Với gamma=1,2, ngoài đường chéo dùng số mờ tam giác (a_ij/gamma, a_ij, a_ij×gamma); đường chéo (1,1,1). Cặp nghịch đảo dùng (1/u, 1/m, 1/l), áp dụng nhất quán kể cả phán đoán bằng nhau.

```text
g_i = ((product_j l_ij)^(1/3), (product_j m_ij)^(1/3), (product_j u_ij)^(1/3))
w_tilde_i = (g_i,l / sum_k g_k,u,
             g_i,m / sum_k g_k,m,
             g_i,u / sum_k g_k,l)
d_i = (w_tilde_i,l + w_tilde_i,m + w_tilde_i,u) / 3
w_i = d_i / sum_k d_k
```

**Giới hạn toán học cần công bố:** gamma chung và cùng số phần tử ngoài đường chéo khiến g_i,l = gamma^(-2/3) g_i,m và g_i,u = gamma^(2/3) g_i,m. Hệ số giải mờ chung triệt tiêu khi chuẩn hóa, nên trọng số cuối bằng geometric-mean crisp AHP trong biến thể này. Fuzzy vẫn có biểu diễn số mờ, nhưng không tạo lợi ích khác biệt về thứ hạng; không được dùng tên phương pháp để khẳng định tốt hơn. Muốn thể hiện bất định thực cần thu thập mức bất định riêng cho từng phán đoán, xây thang reciprocal và đánh giá độc lập, ngoài phạm vi phiên bản này.

Kiểm thử hoán vị cả hàng/cột, ánh xạ trọng số về thứ tự gốc phải cho kết quả như nhau. Baseline crisp đặt gamma=1.

## 4. TOPSIS

```text
r_ij = x_ij / sqrt(sum_k x_kj^2)
v_ij = w_j × r_ij
D_i+ = sqrt(sum_j (v_ij - best_j)^2)
D_i- = sqrt(sum_j (v_ij - worst_j)^2)
C_i = D_i- / (D_i+ + D_i-)
```

Benefit chọn best=max, cost chọn best=min; worst ngược lại. Không đảo thời gian rồi lại áp dụng cost. Cột chuẩn bằng 0 được đặt 0; khi hai khoảng cách đều 0, điểm là 0,5. Cột hằng không phân biệt các ứng viên. Tie-break bằng ID canonical. Điểm là tương đối trong pool, không phải xác suất hài lòng và không so trực tiếp giữa các request khác pool.

## 5. Chèn tham lam có ràng buộc thời gian

Duyệt theo xếp hạng, thử mọi vị trí chèn. Mô phỏng các chặng có hướng, chờ mở cửa, thời lượng ghé, và đường quay về. Toàn lượt ghé phải nằm trong một khoảng mở cửa; không ghép hai nửa giờ qua thời gian nghỉ trưa.

Chọn vị trí hợp lệ có thời gian lái xe tăng ít nhất; hòa thì về sớm hơn rồi chỉ số chèn nhỏ hơn. Sau mỗi chèn, duyệt lại điểm chưa chọn; tối đa 5 điểm, tối thiểu 2. Route API tạo hình học, thời gian từng chặng Route được dùng để kiểm tra lại lịch thay vì giả định bằng Table.

Duration/distance null hoặc âm là cạnh không dùng được. Lỗi dịch vụ là `routing_unavailable`, không tạo tuyến giả. Giờ thiếu/không parse/ngoại lệ lễ chưa giải được làm `provisional`. Giờ biết nhưng đóng cửa phải bị loại. Bản đồ vẽ đường thật, chưa mô hình hóa bãi đỗ, đi bộ hay giao thông trực tiếp.

Độ phức tạp planner với N ứng viên, K≤5 chủ yếu O(N×K³) khi mô phỏng mọi vị trí qua các lượt; ma trận routing O(N²). Giới hạn N=40 để kiểm soát chi phí. Không có chứng minh tối ưu toàn cục.

## 6. Đánh giá

Bốn phương pháp: nearby (thời gian từ gốc tăng dần), weighted sum đều trên vector chuẩn hóa với dấu âm cho cost, crisp AHP+TOPSIS, fuzzy AHP+TOPSIS. Chúng gọi cùng retrieval, pool và planner.

```text
AP@K = sum_{i=1..K}(Precision@i × relevant_i) / min(K, tổng relevant của tập nhãn)
DCG@K = sum_{i=1..K}((2^rel_i - 1) / log2(i+1))
NDCG@K = DCG@K / IDCG@K
```

IDCG lấy thứ tự lý tưởng từ toàn tập nhãn, không chỉ các kết quả trả về. Khi chưa có nhãn độc lập, metrics là null; không tự sinh nhãn từ điểm mô hình. File nhãn phải bao phủ pool được đánh giá. Các query tình huống được viết trước khi chạy, không sinh từ POI đáp án. Đây vẫn chưa phải khảo sát người dùng độc lập.
