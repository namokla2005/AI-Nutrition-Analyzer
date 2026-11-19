# Báo cáo kiểm chứng importer Open Food Facts

## Phạm vi và nguồn dữ liệu

- Importer: `scripts/import_openfoodfacts.py`.
- Đầu vào: `data/external/openfoodfacts/off_subset.csv`, đọc theo kiểu streaming và commit mỗi 500 sản phẩm.
- CSV có **20.000** dòng dữ liệu và đúng **14** cột theo hợp đồng.
- Nguồn và ghi công: **Open Food Facts**.
- Giấy phép đã ghi trong `food_sources`: **Open Database License (ODbL) v1.0**.
- Khóa chống trùng: `(source_id, source_ref)`, trong đó `source_ref` là barcode OFF `code`.
- CSDL kiểm thử là bản sao tạm `data/tmp_off_import.db`, revision **827db6071a8d**. Không chạy Alembic và không chạy importer trên `data/nutrition.db`.
- Log importer xác nhận URL/path đã resolve tới:
  `D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer\data\tmp_off_import.db`.

## Kết quả lần nhập thứ nhất

| Chỉ số | Giá trị |
|---|---:|
| Dòng CSV đã đọc | 20.000 |
| Food thêm mới | 20.000 |
| Food cập nhật | 0 |
| Food bỏ qua | 0 |
| Lý do bỏ qua | Không có |
| Batch đã commit | 40 |
| Tổng `foods` của nguồn Open Food Facts | 20.000 |
| Tổng `food_nutrients` của nguồn | 140.000 |
| Tổng `food_aliases` của nguồn | 16.209 |
| Barcode trùng trong DB theo nguồn | 0 |

Có **759** dòng không có `product_name`; importer lưu `name_en = NULL` thay vì bịa tên. Các dòng này vẫn được nhập theo barcode; `name_normalized` dùng brand khi có brand. `category` được cắt tối đa 80 ký tự, các trường tên tối đa 240 ký tự và `cooking_state = 'processed'`.

## Giá trị thiếu theo nutrient code

Importer tạo đủ bảy dòng nutrient cho mỗi food. Ô trống được lưu là `NULL`, không đổi thành 0. Số lượng `NULL` kiểm tra trực tiếp bằng SQL trên DB tạm:

| Nutrient code | Số `NULL` |
|---|---:|
| `energy_kcal` | 0 |
| `protein_g` | 0 |
| `carbohydrate_g` | 0 |
| `fat_g` | 0 |
| `fiber_g` | 6.983 |
| `sugar_g` | 1.227 |
| `sodium_mg` | 1.878 |

Giá trị 0 có thật trong OFF vẫn được giữ là 0; chỉ chuỗi trống/thiếu mới thành `NULL`.

## Thống kê năng lượng

Trên **20.000** giá trị `energy_kcal` không NULL:

- Nhỏ nhất: **0 kcal/100 g**.
- Lớn nhất: **3.617,4 kcal/100 g**.
- Trung vị: **229 kcal/100 g**.

## Kiểm chứng chuyển đổi sodium

OFF cung cấp `sodium_100g` theo **g/100 g**, còn nutrient `sodium_mg` dùng **mg/100 g**. Importer nhân giá trị OFF với **1.000**. Ba mẫu dưới đây được đọc trực tiếp từ `off_subset.jsonl` rồi đối chiếu với SQL trên DB tạm:

| Barcode | Sản phẩm | OFF thô (g/100 g) | Đã lưu (mg/100 g) | Đối chiếu |
|---|---|---:|---:|---|
| `0003501660091` | THẠCH RAU CÂU HƯƠNG TRÁI CÂY TỔNG HỎ - ASSORT FAVOR MINI FRUITY GELS | 0,02 | 20 | Khớp |
| `0008968604368` | Mi Goreng Vị Sườn | 1,09875 | 1.098,75 | Khớp |
| `0014100047957` | Milano dark chocolate cookies | 0,190476190476188 | 190,476190476188 | Khớp |

## Năm sản phẩm mẫu sau import

| Barcode | Tên | kcal | Protein (g) | Carb (g) | Fat (g) | Sodium (mg) |
|---|---|---:|---:|---:|---:|---:|
| `0003501660091` | THẠCH RAU CÂU HƯƠNG TRÁI CÂY TỔNG HỎ - ASSORT FAVOR MINI FRUITY GELS | 120 | 0 | 29 | 0 | 20 |
| `0005903030004` | Mực Sống Cay Hàn | 168 | 9 | 11 | 9 | NULL |
| `0008968604368` | Mi Goreng Vị Sườn | 446,25 | 10,5 | 60 | 18,25 | 1.098,75 |
| `0014100047957` | Milano dark chocolate cookies | 523,80952380952 | 4,7619047619048 | 66,666666666667 | 28,571428571429 | 190,476190476188 |
| `0015000045203` | puffs strawberry apple grain snack | 0 | 0 | 6 | 0 | 0 |

## Kiểm chứng idempotency

Chạy lại importer lần hai trên cùng DB tạm cho kết quả:

- Dòng đọc: **20.000**.
- Thêm mới: **0**.
- Cập nhật: **20.000**.
- Bỏ qua: **0**.
- Sau lần hai vẫn có đúng **20.000 foods**, **140.000 food_nutrients**, **16.209 food_aliases** và **0 barcode trùng**.
- Snapshot các số liệu kiểm chứng trước/sau lần hai giống hệt nhau.

## Kiểm tra toàn vẹn và test

- `PRAGMA integrity_check`: **ok**.
- `PRAGMA foreign_key_check`: **0** vi phạm.
- Unit test riêng của importer: **4/4 passed** (NULL, sodium ×1.000, mapping/truncation và từ chối nutrient âm/không hữu hạn).
- `tests/unit/test_food_repository.py`: **17/17 passed**.
- DB tạm cùng các file `-wal`/`-shm` và script kiểm chứng tạm được xóa sau khi hoàn tất.
