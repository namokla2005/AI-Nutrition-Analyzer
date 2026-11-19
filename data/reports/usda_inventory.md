# Kiểm kê dữ liệu USDA FoodData Central

- Thời điểm tạo báo cáo (UTC): `2026-11-18T20:16:44.978467Z`
- Phương pháp đếm CSV: đọc bằng `csv.reader` với `newline=''`; `data_rows` là số bản ghi CSV thực sau hàng tiêu đề, không suy đoán từ dung lượng. Báo cáo cũng lưu `physical_line_count` để kiểm tra số dòng vật lý.
- Phương pháp toàn vẹn: SHA-256 trên từng ZIP; `zipfile.ZipFile.testzip()` phải trả về `None`; tất cả thành viên giải nén phải hiện diện và có kích thước khớp metadata ZIP.

## Bằng chứng nguồn và phạm vi

Trang mô tả loại dữ liệu đã đọc: https://fdc.nal.usda.gov/data-documentation
> “Foundation Foods — Definition: Data and metadata on individual samples of commodity/commodity-derived minimally processed foods with insights into variability”
> “Food and Nutrient Database for Dietary Studies (FNDDS) — Definition: Data on nutrients and portion weights for foods and beverages reported in What We Eat in America, NHANES”
> “SR Legacy — Definition: Historic data on food components including nutrients derived from analyses, calculations, and published literature”

Tài liệu USDA về cơ sở 100 g đã đọc: https://fdc.nal.usda.gov/Foundation_Foods_Documentation
> “The gram weights in the food portion file can be used to calculate nutrient values for food portions from the values provided per 100 g of food.”
> “V = nutrient value per 100 g (Nutr_Val in the Nutrient Data file), and W = weight (in g) of portion (Gm_Wgt in the Weight file).”

Tài liệu trường đi kèm từng gói (tệp XLSX/PDF đã giải nén) xác nhận:
> “Amount of the nutrient per 100g of food. Specified in unit defined in the nutrient table.”
> “The standard unit of measure for the nutrient (per 100g of food)”

**Kết luận đơn vị:** `food_nutrient.amount` là lượng chất dinh dưỡng trên 100 g thực phẩm. Bản ghi `nutrient.id=1008` (`Energy`, `KCAL`) cho mục tiêu **kcal/100 g**; bản ghi `nutrient.id=1062` (`Energy`, `kJ`) cho kJ/100 g. kJ không phải một cột rộng riêng. Cột `food_nutrient.nutrient_id` của từng gói phải được kiểm tra thực tế vì bộ Survey dùng mã `nutrient_nbr`, còn hai bộ kia dùng `nutrient.id`.

## SR Legacy (2018-04)

- URL tải chính xác: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
- Thời điểm tải suy ra từ mtime của ZIP (UTC): `2026-11-18T20:04:03.935162Z`
- Kích thước tải: `6074592` byte
- SHA-256: `b80817294b8850530aaedf2e515c02593b1824f763a0ff356e5c2081643e6fd0`
- ZIP: `testzip=None`; `18` tệp; tổng dung lượng giải nén theo ZIP `39791883` byte
- Giải nén: `all_members_present=true`; `all_file_sizes_match_zip_metadata=true`
- `food.csv`: `7793` dòng dữ liệu

### Tệp đã giải nén, kích thước, số dòng và toàn bộ header CSV

| Tệp | Byte | data_rows | CSV records gồm header | Dòng vật lý | Header đầy đủ |
|---|---:|---:|---:|---:|---|
| `food_update_log_entry.csv` | 623888 | 7793 | 7794 | 7794 | `id`, `description`, `last_updated` |
| `sr_legacy_food.csv` | 130404 | 7793 | 7794 | 7794 | `fdc_id`, `NDB_number` |
| `Download & API Field Descriptions-2019-10-11-16-22.xlsx` | 447102 | — | — | — | — |
| `food_nutrient_source.csv` | 602 | 10 | 11 | 11 | `id`, `code`, `description` |
| `food_attribute_type.csv` | 331 | 5 | 6 | 6 | `id`, `name`, `description` |
| `measure_unit.csv` | 1955 | 122 | 123 | 123 | `id`, `name` |
| `food_nutrient_conversion_factor.csv` | 183104 | 10770 | 10771 | 10771 | `id`, `fdc_id` |
| `nutrient.csv` | 21464 | 474 | 475 | 475 | `id`, `name`, `unit_name`, `nutrient_nbr`, `rank` |
| `food_nutrient_derivation.csv` | 6853 | 64 | 65 | 65 | `id`, `code`, `description`, `source_id` |
| `food_attribute.csv` | 63688 | 1074 | 1075 | 1075 | `id`, `fdc_id`, `seq_num`, `food_attribute_type_id`, `name`, `value` |
| `food.csv` | 793104 | 7793 | 7794 | 7794 | `fdc_id`, `data_type`, `description`, `food_category_id`, `publication_date` |
| `food_protein_conversion_factor.csv` | 90043 | 6077 | 6078 | 6078 | `food_nutrient_conversion_factor_id`, `value` |
| `food_category.csv` | 997 | 28 | 29 | 29 | `id`, `code`, `description` |
| `all_downloaded_table_record_counts.csv` | 291 | 9 | 10 | 10 | `Table`, `Number of Records` |
| `food_nutrient.csv` | 36366059 | 644125 | 644126 | 644126 | `id`, `fdc_id`, `nutrient_id`, `amount`, `data_points`, `derivation_id`, `min`, `max`, `median`, `footnote`, `min_year_acquired` |
| `retention_factor.csv` | 13304 | 270 | 271 | 271 | `id`, `code`, `food_group_id`, `description` |
| `food_calorie_conversion_factor.csv` | 129904 | 4693 | 4694 | 4694 | `food_nutrient_conversion_factor_id`, `protein_value`, `fat_value`, `carbohydrate_value` |
| `food_portion.csv` | 918790 | 14449 | 14450 | 14450 | `id`, `fdc_id`, `seq_num`, `amount`, `measure_unit_id`, `portion_description`, `modifier`, `gram_weight`, `data_points`, `footnote`, `min_year_acquired` |

### Ghép `nutrient.csv` ↔ `food_nutrient.csv` cho năng lượng

Điều kiện ghép được chọn từ dữ liệu thực: `food_nutrient.nutrient_id = nutrient.id; group foods by nutrient.unit_name`; `149` mã phân biệt khớp `nutrient.id`, `0` mã khớp `nutrient.nutrient_nbr`. Chỉ đếm dòng có `amount` không rỗng; số thực phẩm là `COUNT(DISTINCT fdc_id)`.

| nutrient.id | Giá trị trong food_nutrient.nutrient_id | nutrient.name | nutrient.unit_name | nutrient_nbr | Dòng food_nutrient | Thực phẩm phân biệt |
|---:|---:|---|---|---:|---:|---:|
| 2047 | 2047 | `Energy (Atwater General Factors)` | `KCAL` | 957 | 0 | 0 |
| 2048 | 2048 | `Energy (Atwater Specific Factors)` | `KCAL` | 958 | 0 | 0 |
| 1008 | 1008 | `Energy` | `KCAL` | 208 | 7793 | 7793 |
| 1062 | 1062 | `Energy` | `kJ` | 268 | 7793 | 7793 |

**Tổng hợp theo đơn vị (hợp các nutrient ID, đếm thực phẩm phân biệt):**
- `KCAL`: `7793` thực phẩm; `7793` dòng năng lượng.
- `kJ`: `7793` thực phẩm; `7793` dòng năng lượng.
- ID dinh dưỡng được `food_nutrient` tham chiếu nhưng không có trong `nutrient.csv`: `0` — `[]`.

### Cột số cho thí nghiệm hồi quy calo

Các chất chính quan sát được trong `nutrient.csv`:
- `id=1003`, `name=Protein`, `unit_name=G`, `nutrient_nbr=203`
- `id=1004`, `name=Total lipid (fat)`, `unit_name=G`, `nutrient_nbr=204`
- `id=1005`, `name=Carbohydrate, by difference`, `unit_name=G`, `nutrient_nbr=205`
- `id=1008`, `name=Energy`, `unit_name=KCAL`, `nutrient_nbr=208`
- `id=1062`, `name=Energy`, `unit_name=kJ`, `nutrient_nbr=268`
- `id=1079`, `name=Fiber, total dietary`, `unit_name=G`, `nutrient_nbr=291`
- `id=2047`, `name=Energy (Atwater General Factors)`, `unit_name=KCAL`, `nutrient_nbr=957`
- `id=2048`, `name=Energy (Atwater Specific Factors)`, `unit_name=KCAL`, `nutrient_nbr=958`

- `food.csv` — `fdc_id`: Khóa thực phẩm để ghép và nhận diện quan sát; description/data_type dùng làm nhãn phân loại, không phải biến số liên tục.
- `nutrient.csv` — `id`, `nutrient_nbr`, `rank`: id hoặc nutrient_nbr là khóa ghép với food_nutrient.nutrient_id tùy gói; unit_name và name xác định ý nghĩa/đơn vị của biến.
- `food_nutrient.csv` — `fdc_id`, `nutrient_id`, `amount`, `data_points`, `min`, `max`, `median`, `min_year_acquired`: amount là giá trị số trên 100 g; pivot theo nutrient_id để tạo X (protein, fat, carbohydrate, v.v.) và y (energy KCAL). Các cột thống kê có thể dùng kiểm soát chất lượng.
- `food_portion.csv` — `fdc_id`, `amount`, `gram_weight`, `data_points`: Quy đổi giữa khẩu phần và cơ sở 100 g; không cần nếu mô hình giữ toàn bộ dữ liệu trên 100 g.
- `food_calorie_conversion_factor.csv` — `food_nutrient_conversion_factor_id`, `protein_value`, `fat_value`, `carbohydrate_value`: Hệ số tính năng lượng từ các chất đa lượng; hữu ích làm đặc trưng hoặc kiểm tra công thức năng lượng.
- `food_protein_conversion_factor.csv` — `food_nutrient_conversion_factor_id`, `value`: Hệ số chuyển nitơ thành protein; đặc trưng phụ/kiểm tra nguồn protein.
- Mục tiêu khuyến nghị: food_nutrient.nutrient_id=1008, joined to nutrient.id=1008, name=Energy, unit_name=KCAL; inspect nutrient.id 2047/2048 separately because they are alternate Atwater calculations.
- Ghi chú kJ: Không có cột rộng tên kJ. kJ tồn tại ở cùng cột food_nutrient.amount khi food_nutrient.nutrient_id=1062, ghép tới nutrient.id=1062 và nutrient.unit_name='kJ'.

## Foundation Foods (2024-10-31)

- URL tải chính xác: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2024-10-31.zip
- Thời điểm tải suy ra từ mtime của ZIP (UTC): `2026-11-18T20:04:09.243448Z`
- Kích thước tải: `3258886` byte
- SHA-256: `8587f941ec252bd9aaf7b85a18a42980fb540f509b34300ed8dd4d10ca9edf44`
- ZIP: `testzip=None`; `25` tệp; tổng dung lượng giải nén theo ZIP `27184066` byte
- Giải nén: `all_members_present=true`; `all_file_sizes_match_zip_metadata=true`
- `food.csv`: `68875` dòng dữ liệu

### Tệp đã giải nén, kích thước, số dòng và toàn bộ header CSV

| Tệp | Byte | data_rows | CSV records gồm header | Dòng vật lý | Header đầy đủ |
|---|---:|---:|---:|---:|---|
| `food_update_log_entry.csv` | 4163525 | 68875 | 68876 | 68877 | `id`, `description`, `last_updated` |
| `agricultural_samples.csv` | 38059 | 810 | 811 | 811 | `fdc_id`, `acquisition_date`, `market_class`, `treatment`, `state` |
| `Download API Field Descriptions.xlsx` | 31584 | — | — | — | — |
| `input_food.csv` | 296745 | 5493 | 5494 | 5494 | `id`, `fdc_id`, `fdc_of_input_food`, `seq_num`, `amount`, `ingredient_code`, `ingredient_description`, `unit`, `portion_code`, `portion_description`, `gram_weight`, `retention_code` |
| `food_attribute_type.csv` | 331 | 5 | 6 | 6 | `id`, `name`, `description` |
| `lab_method_code.csv` | 3998 | 192 | 193 | 193 | `lab_method_id`, `code` |
| `measure_unit.csv` | 1955 | 122 | 123 | 123 | `id`, `name` |
| `food_nutrient_conversion_factor.csv` | 194720 | 11428 | 11429 | 11429 | `id`, `fdc_id` |
| `nutrient.csv` | 21566 | 477 | 478 | 478 | `id`, `name`, `unit_name`, `nutrient_nbr`, `rank` |
| `sub_sample_food.csv` | 1119651 | 57112 | 57113 | 57113 | `fdc_id`, `fdc_id_of_sample_food` |
| `market_acquisition.csv` | 767613 | 7032 | 7033 | 7033 | `fdc_id`, `brand_description`, `expiration_date`, `label_weight`, `location`, `acquisition_date`, `sales_type`, `sample_lot_nbr`, `sell_by_date`, `store_city`, `store_name`, `store_state`, `upc_code` |
| `food_attribute.csv` | 362415 | 5087 | 5088 | 5088 | `id`, `fdc_id`, `seq_num`, `food_attribute_type_id`, `name`, `value` |
| `sample_food.csv` | 33618 | 3534 | 3535 | 3535 | `fdc_id` |
| `food.csv` | 5730243 | 68875 | 68876 | 68877 | `fdc_id`, `data_type`, `description`, `food_category_id`, `publication_date` |
| `food_protein_conversion_factor.csv` | 4781 | 317 | 318 | 318 | `food_nutrient_conversion_factor_id`, `value` |
| `lab_method.csv` | 12287 | 283 | 284 | 284 | `id`, `description`, `technique` |
| `sub_sample_result.csv` | 4534420 | 116324 | 116325 | 116325 | `food_nutrient_id`, `adjusted_amount`, `lab_method_id`, `nutrient_name` |
| `food_category.csv` | 997 | 28 | 29 | 29 | `id`, `code`, `description` |
| `lab_method_nutrient.csv` | 7968 | 567 | 568 | 568 | `lab_method_id`, `nutrient_id` |
| `food_nutrient.csv` | 8828421 | 149615 | 149616 | 149616 | `id`, `fdc_id`, `nutrient_id`, `amount`, `data_points`, `derivation_id`, `min`, `max`, `median`, `footnote`, `min_year_acquired` |
| `acquisition_samples.csv` | 144347 | 7816 | 7817 | 7817 | `fdc_id_of_sample_food`, `fdc_id_of_acquisition_food` |
| `food_calorie_conversion_factor.csv` | 9860 | 341 | 342 | 342 | `food_nutrient_conversion_factor_id`, `protein_value`, `fat_value`, `carbohydrate_value` |
| `food_component.csv` | 158565 | 3066 | 3067 | 3067 | `id`, `fdc_id`, `name`, `pct_weight`, `is_refuse`, `gram_weight`, `data_points`, `min_year_acqured` |
| `foundation_food.csv` | 15554 | 316 | 317 | 317 | `fdc_id`, `NDB_number`, `footnote` |
| `food_portion.csv` | 700843 | 10678 | 10679 | 10679 | `id`, `fdc_id`, `seq_num`, `amount`, `measure_unit_id`, `portion_description`, `modifier`, `gram_weight`, `data_points`, `footnote`, `min_year_acquired` |

### Ghép `nutrient.csv` ↔ `food_nutrient.csv` cho năng lượng

Điều kiện ghép được chọn từ dữ liệu thực: `food_nutrient.nutrient_id = nutrient.id; group foods by nutrient.unit_name`; `226` mã phân biệt khớp `nutrient.id`, `0` mã khớp `nutrient.nutrient_nbr`. Chỉ đếm dòng có `amount` không rỗng; số thực phẩm là `COUNT(DISTINCT fdc_id)`.

| nutrient.id | Giá trị trong food_nutrient.nutrient_id | nutrient.name | nutrient.unit_name | nutrient_nbr | Dòng food_nutrient | Thực phẩm phân biệt |
|---:|---:|---|---|---:|---:|---:|
| 2047 | 2047 | `Energy (Atwater General Factors)` | `KCAL` | 957 | 309 | 309 |
| 2048 | 2048 | `Energy (Atwater Specific Factors)` | `KCAL` | 958 | 299 | 299 |
| 1008 | 1008 | `Energy` | `KCAL` | 208 | 135 | 135 |
| 1062 | 1062 | `Energy` | `kJ` | 268 | 135 | 135 |

**Tổng hợp theo đơn vị (hợp các nutrient ID, đếm thực phẩm phân biệt):**
- `KCAL`: `340` thực phẩm; `743` dòng năng lượng.
- `kJ`: `135` thực phẩm; `135` dòng năng lượng.
- ID dinh dưỡng được `food_nutrient` tham chiếu nhưng không có trong `nutrient.csv`: `1` — `['2066']`.

### Cột số cho thí nghiệm hồi quy calo

Các chất chính quan sát được trong `nutrient.csv`:
- `id=1003`, `name=Protein`, `unit_name=G`, `nutrient_nbr=203`
- `id=1004`, `name=Total lipid (fat)`, `unit_name=G`, `nutrient_nbr=204`
- `id=1005`, `name=Carbohydrate, by difference`, `unit_name=G`, `nutrient_nbr=205`
- `id=1008`, `name=Energy`, `unit_name=KCAL`, `nutrient_nbr=208`
- `id=1062`, `name=Energy`, `unit_name=kJ`, `nutrient_nbr=268`
- `id=1079`, `name=Fiber, total dietary`, `unit_name=G`, `nutrient_nbr=291`
- `id=2047`, `name=Energy (Atwater General Factors)`, `unit_name=KCAL`, `nutrient_nbr=957`
- `id=2048`, `name=Energy (Atwater Specific Factors)`, `unit_name=KCAL`, `nutrient_nbr=958`

- `food.csv` — `fdc_id`: Khóa thực phẩm để ghép và nhận diện quan sát; description/data_type dùng làm nhãn phân loại, không phải biến số liên tục.
- `nutrient.csv` — `id`, `nutrient_nbr`, `rank`: id hoặc nutrient_nbr là khóa ghép với food_nutrient.nutrient_id tùy gói; unit_name và name xác định ý nghĩa/đơn vị của biến.
- `food_nutrient.csv` — `fdc_id`, `nutrient_id`, `amount`, `data_points`, `min`, `max`, `median`, `min_year_acquired`: amount là giá trị số trên 100 g; pivot theo nutrient_id để tạo X (protein, fat, carbohydrate, v.v.) và y (energy KCAL). Các cột thống kê có thể dùng kiểm soát chất lượng.
- `food_portion.csv` — `fdc_id`, `amount`, `gram_weight`, `data_points`: Quy đổi giữa khẩu phần và cơ sở 100 g; không cần nếu mô hình giữ toàn bộ dữ liệu trên 100 g.
- `food_calorie_conversion_factor.csv` — `food_nutrient_conversion_factor_id`, `protein_value`, `fat_value`, `carbohydrate_value`: Hệ số tính năng lượng từ các chất đa lượng; hữu ích làm đặc trưng hoặc kiểm tra công thức năng lượng.
- `food_protein_conversion_factor.csv` — `food_nutrient_conversion_factor_id`, `value`: Hệ số chuyển nitơ thành protein; đặc trưng phụ/kiểm tra nguồn protein.
- Mục tiêu khuyến nghị: food_nutrient.nutrient_id=1008, joined to nutrient.id=1008, name=Energy, unit_name=KCAL; inspect nutrient.id 2047/2048 separately because they are alternate Atwater calculations.
- Ghi chú kJ: Không có cột rộng tên kJ. kJ tồn tại ở cùng cột food_nutrient.amount khi food_nutrient.nutrient_id=1062, ghép tới nutrient.id=1062 và nutrient.unit_name='kJ'.

## Survey/FNDDS (2022-10-28)

- URL tải chính xác: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_survey_food_csv_2022-10-28.zip
- Thời điểm tải suy ra từ mtime của ZIP (UTC): `2026-11-18T20:04:14.304515Z`
- Kích thước tải: `4427502` byte
- SHA-256: `e9a10d13a975bf45087f70306fc6ce1077fe538599843f028329a8b11c37b958`
- ZIP: `testzip=None`; `14` tệp; tổng dung lượng giải nén theo ZIP `42187417` byte
- Giải nén: `all_members_present=true`; `all_file_sizes_match_zip_metadata=true`
- `food.csv`: `5624` dòng dữ liệu

### Tệp đã giải nén, kích thước, số dòng và toàn bộ header CSV

| Tệp | Byte | data_rows | CSV records gồm header | Dòng vật lý | Header đầy đủ |
|---|---:|---:|---:|---:|---|
| `all_downloaded_table_record_counts.csv` | 210 | 8 | 9 | 9 | `Table`, `Number of Records` |
| `Download & API Field Descriptions Oct 2022.pdf` | 148996 | — | — | — | — |
| `fndds_ingredient_nutrient_value.csv` | 15767387 | 122330 | 122331 | 122331 | `ingredient code`, `Ingredient description`, `Nutrient code`, `Nutrient value`, `Nutrient value source`, `FDC ID`, `Derivation code`, `SR AddMod year`, `Foundation year acquired`, `Start date`, `End date` |
| `food.csv` | 480637 | 5624 | 5625 | 5625 | `fdc_id`, `data_type`, `description`, `food_category_id`, `publication_date` |
| `food_attribute.csv` | 1667715 | 26919 | 26920 | 26920 | `id`, `fdc_id`, `seq_num`, `food_attribute_type_id`, `name`, `value` |
| `food_nutrient.csv` | 20095825 | 365560 | 365561 | 365561 | `id`, `fdc_id`, `nutrient_id`, `amount`, `data_points`, `derivation_id`, `min`, `max`, `median`, `footnote`, `min_year_acquired` |
| `food_portion.csv` | 1541319 | 22710 | 22711 | 22711 | `id`, `fdc_id`, `seq_num`, `amount`, `measure_unit_id`, `portion_description`, `modifier`, `gram_weight` |
| `input_food.csv` | 2147896 | 19308 | 19309 | 19309 | `id`, `fdc_id`, `fdc_of_input_food`, `seq_num`, `amount`, `sr_code`, `sr_description`, `unit`, `portion_code`, `portion_description`, `gram_weight`, `retention_code`, `survey_flag` |
| `survey_fndds_food.csv` | 303765 | 5624 | 5625 | 5625 | `fdc_id`, `food_code`, `wweia_category_number`, `start_date`, `end_date` |
| `fndds_derivation.csv` | 4838 | 49 | 50 | 50 | `SR 28 derivation code`, `SR 28 derivation description` |
| `food_attribute_type.csv` | 331 | 5 | 6 | 6 | `id`, `name`, `description` |
| `measure_unit.csv` | 1955 | 122 | 123 | 123 | `id`, `name` |
| `nutrient.csv` | 21464 | 474 | 475 | 475 | `id`, `name`, `unit_name`, `nutrient_nbr`, `rank` |
| `wweia_food_category.csv` | 5079 | 171 | 172 | 172 | `wweia_food_category`, `wweia_food_category_description` |

### Ghép `nutrient.csv` ↔ `food_nutrient.csv` cho năng lượng

Điều kiện ghép được chọn từ dữ liệu thực: `food_nutrient.nutrient_id = nutrient.nutrient_nbr; group foods by nutrient.unit_name`; `0` mã phân biệt khớp `nutrient.id`, `65` mã khớp `nutrient.nutrient_nbr`. Chỉ đếm dòng có `amount` không rỗng; số thực phẩm là `COUNT(DISTINCT fdc_id)`.

| nutrient.id | Giá trị trong food_nutrient.nutrient_id | nutrient.name | nutrient.unit_name | nutrient_nbr | Dòng food_nutrient | Thực phẩm phân biệt |
|---:|---:|---|---|---:|---:|---:|
| 2047 | 957 | `Energy (Atwater General Factors)` | `KCAL` | 957 | 0 | 0 |
| 2048 | 958 | `Energy (Atwater Specific Factors)` | `KCAL` | 958 | 0 | 0 |
| 1008 | 208 | `Energy` | `KCAL` | 208 | 5624 | 5624 |
| 1062 | 268 | `Energy` | `kJ` | 268 | 0 | 0 |

**Tổng hợp theo đơn vị (hợp các nutrient ID, đếm thực phẩm phân biệt):**
- `KCAL`: `5624` thực phẩm; `5624` dòng năng lượng.
- `kJ`: `0` thực phẩm; `0` dòng năng lượng.
- ID dinh dưỡng được `food_nutrient` tham chiếu nhưng không có trong `nutrient.csv`: `0` — `[]`.

### Cột số cho thí nghiệm hồi quy calo

Các chất chính quan sát được trong `nutrient.csv`:
- `id=1003`, `name=Protein`, `unit_name=G`, `nutrient_nbr=203`
- `id=1004`, `name=Total lipid (fat)`, `unit_name=G`, `nutrient_nbr=204`
- `id=1005`, `name=Carbohydrate, by difference`, `unit_name=G`, `nutrient_nbr=205`
- `id=1008`, `name=Energy`, `unit_name=KCAL`, `nutrient_nbr=208`
- `id=1062`, `name=Energy`, `unit_name=kJ`, `nutrient_nbr=268`
- `id=1079`, `name=Fiber, total dietary`, `unit_name=G`, `nutrient_nbr=291`
- `id=2047`, `name=Energy (Atwater General Factors)`, `unit_name=KCAL`, `nutrient_nbr=957`
- `id=2048`, `name=Energy (Atwater Specific Factors)`, `unit_name=KCAL`, `nutrient_nbr=958`

- `food.csv` — `fdc_id`: Khóa thực phẩm để ghép và nhận diện quan sát; description/data_type dùng làm nhãn phân loại, không phải biến số liên tục.
- `nutrient.csv` — `id`, `nutrient_nbr`, `rank`: id hoặc nutrient_nbr là khóa ghép với food_nutrient.nutrient_id tùy gói; unit_name và name xác định ý nghĩa/đơn vị của biến.
- `food_nutrient.csv` — `fdc_id`, `nutrient_id`, `amount`, `data_points`, `min`, `max`, `median`, `min_year_acquired`: amount là giá trị số trên 100 g; pivot theo nutrient_id để tạo X (protein, fat, carbohydrate, v.v.) và y (energy KCAL). Các cột thống kê có thể dùng kiểm soát chất lượng.
- `food_portion.csv` — `fdc_id`, `amount`, `gram_weight`: Quy đổi giữa khẩu phần và cơ sở 100 g; không cần nếu mô hình giữ toàn bộ dữ liệu trên 100 g.
- `fndds_ingredient_nutrient_value.csv` — `Nutrient code`, `Nutrient value`, `FDC ID`: Giá trị dinh dưỡng thành phần FNDDS trên 100 g; chỉ có ở bộ Survey này.
- Mục tiêu khuyến nghị: food_nutrient.nutrient_id=208, joined to nutrient.id=1008, name=Energy, unit_name=KCAL; inspect nutrient.id 2047/2048 separately because they are alternate Atwater calculations.
- Ghi chú kJ: Không có cột rộng tên kJ. kJ tồn tại ở cùng cột food_nutrient.amount khi food_nutrient.nutrient_id=268, ghép tới nutrient.id=1062 và nutrient.unit_name='kJ'.

## Tải bổ sung bộ Full

- URL: https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_csv_2026-10-29.zip
- Kích thước: `484700676` byte
- SHA-256: `23747de62bb5ad1bce2365c96397a152419accbb3044b1db02954e96eea316c1`
- ZIP: `testzip=None`; `35` tệp; `3288834752` byte chưa nén
- Đã giải nén: `false`. Đã thử tải sau khi ba bộ nhỏ thành công; chỉ ba bộ nhỏ thuộc phạm vi bắt buộc giải nén/kiểm kê chi tiết.

## Giấy phép, trích dẫn và quyền tái sử dụng

Trang điều khoản/cấp phép FDC đã đọc: https://fdc.nal.usda.gov/api-guide
> “USDA FoodData Central data are in the public domain and they are not copyrighted. They are published under CC0 1.0 Universal (CC0 1.0)”
> “No permission is needed for their use, but we request that users list FoodData Central as the source of the data, and when possible, notify us of the product that uses the data so we may better track how FDC is being used in the public domain.”
> “U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, 2019. fdc.nal.usda.gov.”

**Diễn giải tái sử dụng:** dữ liệu FDC thuộc phạm vi công cộng, không có bản quyền và được phát hành theo CC0 1.0; không cần xin phép để dùng, sao chép, sửa đổi, phân phối hoặc dùng thương mại. USDA **đề nghị** (request, không phải điều kiện xin phép) ghi FoodData Central là nguồn và, nếu có thể, thông báo sản phẩm sử dụng dữ liệu. Khi trích dẫn một phiên bản cụ thể, nên cập nhật năm/số bản phát hành thay vì giữ nguyên ví dụ 2019.

## Tệp bằng chứng máy đọc

Toàn bộ số liệu, header, danh sách tệp, kết quả ghép và hash ở trên được lưu trong `data/reports/usda_inventory.json`.
