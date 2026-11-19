# Báo cáo nhập USDA FoodData Central

## Trạng thái

Đã xây dựng và kiểm chứng `scripts/import_usda.py` trên **bản sao tạm** của cơ sở dữ liệu ở revision Alembic `827db6071a8d`. Không chạy Alembic, không ghi vào `data/nutrition.db` và không thay đổi schema/model.

Cấu hình cơ sở dữ liệu mà tiến trình nhập đã in trước khi chạy:

- Engine URL: `sqlite+pysqlite:///D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/data/tmp_usda_import.db`
- File thực tế: `D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer\data\tmp_usda_import.db`
- Batch size: 2.000 bản ghi ghi dữ liệu
- Encoding CSV: `utf-8-sig`

Importer có chốt an toàn từ chối chạy trực tiếp nếu đích là `data/nutrition.db`.

## Cách nhập

- Đọc tuần tự bằng `csv.DictReader`; không nạp toàn bộ `food.csv` hoặc `food_nutrient.csv` vào RAM.
- Định danh món ăn bằng cặp duy nhất `(source_id, source_ref)`, trong đó `source_ref = fdc_id`.
- Dùng `FoodRepository.add_alias`, `upsert_nutrient` và `sync_energy_cache` để tái sử dụng logic chuẩn hóa/dedup/đồng bộ sẵn có.
- `name_vi = NULL`, `name_en = description`, `name_normalized = normalize_name(description)`.
- Danh mục ưu tiên bảng category của USDA; nếu không có thì dùng mệnh đề đầu của description; luôn giới hạn 80 ký tự.
- Trạng thái chế biến chỉ gán `raw`/`cooked` khi description có từ khóa rõ ràng; nếu đồng thời có cả hai hoặc không rõ thì giữ `unknown`.
- Chuỗi amount rỗng được chuyển thành `NULL`; giá trị `0.0` được giữ nguyên. Trong dữ liệu mục tiêu lần chạy này không có amount rỗng, nên số hàng `food_nutrients.amount_per_100g IS NULL` thực tế là 0. Chất không có hàng nguồn không bị tự điền thành 0.

## Kiểm tra khóa nối nutrient ở runtime

| Dataset | Số khóa USDA khác nhau quan sát được | Khớp `nutrient.id` | Khớp `nutrient_nbr` | Khóa được chọn |
|---|---:|---:|---:|---|
| SR Legacy | 149 | 149 | 0 | `id` |
| Foundation | 227 | 226 | 0 | `id` |
| Survey/FNDDS | 65 | 0 | 65 | `nutrient_nbr` |

Các số trên được tính trực tiếp khi importer quét `food_nutrient.csv`, không được hard-code. Kết quả xác nhận quy tắc nối khác nhau của Survey/FNDDS.

## Ánh xạ nutrient

Ánh xạ được suy ra từ cặp `(name, unit_name)`, sau đó đối chiếu với nutrient number mong đợi:

| Mã ứng dụng | USDA nutrient number | Tên USDA | Đơn vị nguồn | Đơn vị lưu |
|---|---:|---|---|---|
| `energy_kcal` | 208 | Energy | KCAL | kcal |
| `energy_kj` | 268 | Energy | kJ | kJ |
| `protein_g` | 203 | Protein | G | g |
| `fat_g` | 204 | Total lipid (fat) | G | g |
| `carbohydrate_g` | 205 | Carbohydrate, by difference | G | g |
| `fiber_g` | 291 | Fiber, total dietary | G | g |
| `sugar_g` | 269 | Sugars, Total / Total Sugars | G | g |
| `sodium_mg` | 307 | Sodium, Na | MG | mg |
| `moisture_g` | 255 | Water | G | g |
| `ash_g` | 207 | Ash | G | g |
| `cholesterol_mg` | 601 | Cholesterol | MG | mg |
| `calcium_mg` | 301 | Calcium, Ca | MG | mg |
| `iron_mg` | 303 | Iron, Fe | MG | mg |
| `potassium_mg` | 306 | Potassium, K | MG | mg |
| `vitamin_c_mg` | 401 | Vitamin C, total ascorbic acid | MG | mg |

Cả 15 ánh xạ được chọn đều khớp danh sách đối chiếu. Foundation còn có ứng viên tên `Sugars, Total`, id `1063`, nutrient number `269.3`; importer in mismatch này và chọn đúng hàng `Total Sugars`, id `2000`, nutrient number `269`.

`energy_kcal` chỉ nhận hàng `Energy` KCAL số 208/id 1008 và được đánh dấu `data_quality='measured'`. Importer bỏ qua 608 hàng Foundation thuộc `Energy (Atwater General Factors)`/`Energy (Atwater Specific Factors)`; các giá trị dẫn xuất này không được dùng làm target và không ghi đè năng lượng đo. Hàng kJ được lưu riêng ở `energy_kj`, không trộn hoặc chuyển vào `energy_kcal`.

## Kết quả SQL trên cơ sở dữ liệu tạm

### Theo nguồn

| Nguồn | Foods | Có kcal đo | Thiếu kcal đo | Min kcal | Median kcal | Max kcal | Food nutrients | NULL nutrient |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `usda_sr_legacy` | 7.793 | 7.793 | 0 | 0 | 183 | 902 | 113.158 | 0 |
| `usda_foundation` | 68.867 | 135 | 68.732 | 12 | 148 | 833 | 34.400 | 0 |
| `usda_fndds` | 5.624 | 5.624 | 0 | 0 | 165 | 902 | 73.112 | 0 |
| **Tổng** | **82.284** | **13.552** | **68.732** | **0** | **174** | **902** | **220.670** | **0** |

Số CSV record được đếm bằng `DictReader` là 7.793 / 68.867 / 5.624. Chênh lệch với số dòng vật lý của file đến từ dòng header và các trường CSV có newline nhúng; importer đếm record CSV, không đếm dòng văn bản.

### Trạng thái chế biến

| Nguồn | Raw | Cooked | Unknown |
|---|---:|---:|---:|
| `usda_sr_legacy` | 1.407 | 2.093 | 4.293 |
| `usda_foundation` | 19.124 | 1.470 | 48.273 |
| `usda_fndds` | 116 | 788 | 4.720 |

### Toàn vẹn và idempotency

- Food aliases: 82.284.
- Trùng `(source_id, source_ref)`: 0.
- Trùng `(food_id, nutrient_id)`: 0.
- Trùng `(food_id, alias_normalized)`: 0.
- Sai lệch giữa `foods.energy_kcal_per_100g` và hàng chuẩn `energy_kcal`: 0.
- Trước lần chạy idempotency: 82.284 foods / 220.670 food nutrients / 82.284 aliases.
- Sau lần chạy thứ hai: 82.284 foods / 220.670 food nutrients / 82.284 aliases.
- Lần chạy thứ hai thêm 0 food và 0 alias ở cả ba nguồn.

## Năm hàng mẫu truy vấn từ DB tạm

| Nguồn | FDC ID | Tên | Danh mục | State | kcal | Protein g | Fat g | Carb g |
|---|---|---|---|---|---:|---:|---:|---:|
| SR Legacy | 167512 | Pillsbury Golden Layer Buttermilk Biscuits, Artificial Flavor, refrigerated dough | Baked Products | unknown | 307 | 5,88 | 13,24 | 41,18 |
| SR Legacy | 167513 | Pillsbury, Cinnamon Rolls with Icing, refrigerated dough | Baked Products | unknown | 330 | 4,34 | 11,27 | 53,42 |
| Foundation | 321358 | Hummus, commercial | Legumes and Legume Products | unknown | 229 | 7,35 | 17,1 | 14,9 |
| Foundation | 321359 | Milk, reduced fat, fluid, 2% milkfat, with added vitamin A and vitamin D | Dairy and Egg Products | unknown | 50 | 3,35 | 1,9 | 4,91 |
| Survey/FNDDS | 2340760 | Milk, human | Human milk | unknown | 70 | 1,03 | 4,38 | 6,89 |

## Kiểm thử

- Unit test tạm cho parse amount, cooking state, category, ánh xạ `(name, unit)`, chọn khóa nối và loại Atwater: **7 passed**.
- Toàn bộ bộ test dự án cùng test importer: **129 passed** (exit code 0).
- `py_compile scripts/import_usda.py`: thành công; không phát hiện mẫu secret/shell injection/eval/pickle/SQL f-string trong static scan. `ruff` không được cài trong virtualenv nên không chạy được lint này.
- Import hoàn tất trên DB tạm ở revision `827db6071a8d`.
- Chạy importer lần hai hoàn tất với exit code 0 và không tăng số lượng bản ghi.
