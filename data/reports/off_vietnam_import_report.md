# Báo cáo nhập sản phẩm Việt Nam từ Open Food Facts

## Tóm tắt

- Thời gian thu thập (UTC): `2026-11-26T07:13:41.521385+00:00` – `2026-11-26T07:30:15.522853+00:00`.
- Endpoint: `https://world.openfoodfacts.org/api/v2/search`, bộ lọc `countries_tags=vietnam`, `page_size=100`.
- User-Agent: `AI-Nutrition-Analyzer/1.0 (academic nutrition research; contact: review@example.com)`.
- API báo tổng cộng **1.735** sản phẩm; lấy được **1.620 mã vạch duy nhất** (**93,37%**) qua **29 yêu cầu trang thành công**.
- Database trước/sau: **102.284 → 102.847** thực phẩm.
- Nguồn `openfoodfacts` trước/sau: **20.000 → 20.563** thực phẩm.
- Importer đọc **1.620** dòng: **563 thêm mới**, **1.057 cập nhật theo `(source_id, source_ref)`**, **0 bỏ qua**, **0 lỗi dữ liệu**.
- Trong tập 1.620 sản phẩm vừa xử lý, **1.154** có năng lượng: **71,23%**.
- Toàn database sau import có **33.649 / 102.847** bản ghi có năng lượng: **32,72%**.

## Tệp và bằng chứng

- JSONL trung gian: `data/external/openfoodfacts/off_vietnam.jsonl` — 1.620 dòng — SHA-256 `16d1e734b592f9a5cfab018f8d5257178b5eb92b9a56e7ccbf52b15d70462b21`.
- CSV dùng cho đường nhập hiện có: `data/external/openfoodfacts/off_vietnam.csv` — 1.620 dòng dữ liệu — SHA-256 `8d8916e73c2c62d5c618c5d25251da3e48942dfe69ab3c2dbf72e6276725c301`.
- Bằng chứng thu thập chi tiết: `data/reports/off_vietnam_fetch_evidence.json` (thời gian, trang, cửa sổ sắp xếp, lỗi HTTP, tổng API và SHA-256).
- Bản sao lưu trước khi ghi: `data/backups/nutrition_20261126_070649_pre_off_vietnam.db` — SHA-256 `1f216d09696b33918f3d499188626d90529ccb383a8acd736d801f7a9ab3144d` — `PRAGMA integrity_check = ok`.

## Nguồn, giấy phép và tính toàn vẹn

- `openfoodfacts`: `license='ODbL v1.0'`, `license_url='https://opendatacommons.org/licenses/odbl/1-0/'`; citation ghi rõ Open Food Facts contributors và truy vấn API v2 cho Việt Nam.
- `usda_foundation`, `usda_sr_legacy`, `usda_fndds`: `license='CC0 1.0'`, `license_url='https://creativecommons.org/publicdomain/zero/1.0/'`.
- `vn_fct`: giữ nguyên giấy phép NULL và bổ sung ghi chú `Giấy phép: chưa rõ.`.
- Mã vạch OFF được dùng làm `source_ref`; kiểm tra sau import có **0** nhóm `(source_id, source_ref)` trùng.
- Trường dinh dưỡng không có trong OFF được ghi rỗng trong CSV và importer lưu `amount_per_100g = NULL`, không thay bằng 0. Kiểm tra tập vừa xử lý thấy **4.911** hàng chất dinh dưỡng NULL.
- Nếu `sodium_100g` thiếu nhưng OFF có `salt_100g`, sodium được suy ra theo quy ước OFF `salt / 2,5`; nếu cả hai thiếu thì để NULL.

## Bản ghi bỏ qua và giới hạn thu thập

- Importer bỏ qua: **0**.
- Chưa thu thập được: **115** sản phẩm so với tổng 1.735 mà API báo tại thời điểm chạy.
- OFF giới hạn cửa sổ phân trang sâu; đã dùng các cửa sổ sắp xếp `default`, `last_modified_t`, `created_t`, `product_name`, nghỉ 2 giây giữa yêu cầu và khử trùng theo barcode. API trả HTTP 503 kéo dài tại `last_modified_t` trang 7 và `created_t` trang 4 sau các lần thử lại. Không vượt CAPTCHA hay cơ chế bảo vệ.
- Vì vậy đây là tập 1.620/1.735 sản phẩm có thể lấy bằng các yêu cầu API thành công trong lần chạy này, không phải bản sao đầy đủ tuyệt đối của OFF Việt Nam.

## Kiểm chứng API ứng dụng thật

Máy chủ ban đầu không lắng nghe tại `127.0.0.1:8000` (WinError 10061), nên đã khởi động đúng ứng dụng bằng Python của dự án rồi đăng nhập tài khoản kiểm thử. Đăng nhập trả HTTP 200; ba truy vấn đều trả HTTP 200:

| Truy vấn | Tổng kết quả | Ba tên đầu tiên |
|---|---:|---|
| `phở` | 48 | `Pho`; `Pho sa dec`; `Phool Makhana` |
| `bún` | 135 | `Bún bò huê’ (Rice noodle)`; `Bun Gao Lut`; `Rice vermicelli` |
| `sữa` | 65 | `Sữa Fami Canxi hộp 200ml`; `sữa kun trái cây KUN hương nho`; `Milk without sugar` |

## 20 sản phẩm mẫu

1. THẠCH RAU CÂU HƯƠNG TRÁI CÂY TỔNG HỎ - ASSORT FAVOR MINI FRUITY GELS
2. Mực Sống Cay Hàn
3. Mi Goreng Vị Sườn
4. Milano dark chocolate cookies
5. puffs strawberry apple grain snack
6. Certified Angus Beef - One Percenter - Burgers
7. Postick snack 70
8. Buffalo Jerky Vị Tiêu - Pepper
9. Coconut Milk
10. Whole Cashews
11. Pure milk Low Fat
12. Organic biscotti
13. Thực phẩm dinh dưỡng y học Ensure dạng lỏng hương vani
14. Gold Strength Pro
15. Strawberry Ice Cream
16. Dầu Hào
17. Pizza Meat Feast
18. Instant Noodles
19. Mozarella cheese
20. Caramelle menta

## Hạn chế

- OFF chủ yếu mô tả sản phẩm đóng gói do cộng đồng đóng góp, không đại diện đầy đủ cho món Việt nấu chín hoặc bảng thành phần thực phẩm chuẩn hóa.
- Tên, danh mục và số liệu dinh dưỡng có thể thiếu hoặc do người dùng nhập; giá trị thiếu được giữ NULL.
- Bộ lọc quốc gia phản ánh nhãn quốc gia trên OFF, không khẳng định sản phẩm được sản xuất tại Việt Nam.
- 115 sản phẩm còn lại không được kiểm chứng hoặc nhập trong lần chạy này vì giới hạn/lỗi dịch vụ API nêu trên.
