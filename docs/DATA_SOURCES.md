# NGUỒN DỮ LIỆU VÀ CHẤT LƯỢNG DỮ LIỆU

Cập nhật: 2026-11-19 (UTC+07:00). Mọi con số dưới đây lấy từ truy vấn thật trên
`data/nutrition.db` và từ `scripts/check_data_quality.py`, không phải ước lượng.

---

## 1. Nguồn dữ liệu đang dùng

| Mã nguồn | Tên nguồn | Giấy phép | Bản ghi đã nhập |
|---|---|---|---:|
| `usda_foundation` | USDA FoodData Central – Foundation Foods (2024-10-31) | CC0 1.0 (phạm vi công cộng) | 68.867 |
| `openfoodfacts` | Open Food Facts – trích lọc có giới hạn | Open Database License (ODbL) 1.0 | 20.000 |
| `usda_sr_legacy` | USDA FoodData Central – SR Legacy (2018-04) | CC0 1.0 | 7.793 |
| `usda_fndds` | USDA FoodData Central – Survey/FNDDS (2022-10-28) | CC0 1.0 | 5.624 |
| `vn_fct` | Bảng thành phần dinh dưỡng thực phẩm Việt Nam (nhập thủ công) | chưa xác định – không tự ý tái phân phối | **0** (xem §6) |
| `manual` | Người vận hành nhập tay qua API, có khai báo nguồn | theo người nhập | 0 |
| **Tổng** | | | **102.284** |

Trích nguyên văn giấy phép USDA (đọc từ `https://fdc.nal.usda.gov/api-guide`):
> “USDA FoodData Central data are in the public domain and they are not copyrighted.
> They are published under CC0 1.0 Universal (CC0 1.0)” — “No permission is needed for
> their use, but we request that users list FoodData Central as the source of the data”.

Open Food Facts: “The Open Food Facts database is available under the Open Database
License (ODbL).” (`https://world.openfoodfacts.org/data`) → khi tái sử dụng phải ghi nguồn
và giữ nguyên tính mở của dữ liệu phái sinh.

## 2. Tệp nguồn gốc đã tải (đã kiểm tra sha256)

| Tệp | Kích thước | sha256 |
|---|---:|---|
| `FoodData_Central_sr_legacy_food_csv_2018-04.zip` | 6.074.592 B | `b8081729…e6fd0` |
| `FoodData_Central_foundation_food_csv_2024-10-31.zip` | 3.258.886 B | `8587f941…9edf44` |
| `FoodData_Central_survey_food_csv_2022-10-28.zip` | 4.427.502 B | `e9a10d13…37b958` |
| `en.openfoodfacts.org.products.csv.gz` (dump gốc) | 1.540.715.029 B | 302 → S3 (xem `data/reports/openfoodfacts_inventory.md`) |

Số dòng thật của các CSV USDA (đếm thật, không ước lượng):
SR Legacy `food.csv` 7.794 / `food_nutrient.csv` 644.126 / `nutrient.csv` 475;
Foundation 68.877 / 149.616 / 478; Survey 5.625 / 365.561 / 475.

## 3. Quy tắc đơn vị (bắt buộc)

- Mọi giá trị trong `food_nutrients` là **trên 100 g** phần ăn được (dữ liệu USDA ghi rõ:
  “Amount of the nutrient per 100g of food”).
- **Natri của Open Food Facts là g/100 g** → đã nhân 1.000 để lưu thành `sodium_mg`.
  Ví dụ đã đối chiếu: 0,02 g → 20 mg; 1,09875 g → 1.098,75 mg.
- Năng lượng: chỉ dùng `Energy [KCAL]` (USDA nutrient_nbr 208 / id 1008) làm giá trị đo.
  Cột kJ **không** được trộn vào kcal và **không** dùng làm feature.
- Giá trị thiếu lưu là **NULL**, tuyệt đối không lưu 0 (0 = “đã đo và bằng 0”).

## 4. Cách nạp lại (đã chạy thật)

```bat
.venv\Scripts\python.exe scripts\import_usda.py --allow-production
.venv\Scripts\python.exe scripts\import_openfoodfacts.py
.venv\Scripts\python.exe scripts\import_vn_fct.py --input data\external\vn_fct_template.csv
.venv\Scripts\python.exe scripts\check_data_quality.py --out data\reports\data_quality_report.md
```
Cả ba importer đều **idempotent** (khử trùng theo `source_id + source_ref`, đã có ràng buộc
UNIQUE): chạy lần hai không tạo bản ghi trùng. `import_usda.py` mặc định **từ chối** ghi vào
database chính thức, phải bật cờ `--allow-production`.

**Bẫy kỹ thuật đã phát hiện và xử lý:** `food_nutrient.nutrient_id` khớp `nutrient.id` với
SR Legacy (149/149) và Foundation (226/227), nhưng khớp `nutrient.nutrient_nbr` với
Survey/FNDDS (65/65 so với 0/65). Phải chọn khóa join theo từng bộ dữ liệu.

## 5. Kết quả kiểm toán chất lượng dữ liệu (thật)

Xem chi tiết trong `data/reports/data_quality_report.md`. Tóm tắt:

| Hạng mục | Kết quả |
|---|---|
| Trùng chính xác (`source_id + source_ref`) | **0** |
| Nhóm gần trùng theo tên ở nhiều nguồn | **210** (cùng một loại thực phẩm xuất hiện ở SR Legacy/Foundation/FNDDS — có chủ đích, vì mỗi nguồn là một nguồn riêng) |
| Lệch giữa cache `foods.energy_kcal_per_100g` và bảng chuẩn | **0** |
| Thực phẩm không có số liệu năng lượng | **68.732** (xem §6) |
| Năng lượng > 900 kcal/100 g | **54** (chủ yếu là dầu/mỡ ~902 kcal — hợp lý; một số bản ghi Open Food Facts sai rõ rệt, ví dụ “gg” có tổng đa lượng 183 g/100 g) |
| Tổng protein + carb + fat > 100 g/100 g | **198** (lỗi dữ liệu cộng đồng của OFF) |
| Natri > 40.000 mg/100 g | **22** (muối ~40.100 mg là hợp lý; một số sản phẩm OFF sai) |
| Giá trị âm | **0** |
| Độ phủ chất dinh dưỡng | 7,8 % (`energy_kj`) đến 37,0 % (`fat_g`) |
| Đối chiếu năng lượng đo với công thức Atwater (4/4/9) | 23 trong 30 dòng bị gắn cờ “lệch >25 %” có **sai khác tuyệt đối < 25 kcal/100 g** → đây là hệ quả toán học của thực phẩm ít năng lượng (mẫu số nhỏ làm sai số tương đối phóng đại), **không phải lỗi đơn vị**. Chỉ **7 dòng** vừa lệch >25 % vừa lệch ≥25 kcal/100 g là đáng rà lại; sai khác tuyệt đối lớn nhất trong bảng là 150,5 kcal/100 g |

**Kết luận về chất lượng:** phiên bản dữ liệu này **dùng được** cho tra cứu và tính khẩu phần
(sai khác cache = 0, không có giá trị âm, không trùng chính xác), nhưng **không được coi là
sạch tuyệt đối**: còn 54 giá trị năng lượng >900 kcal và 198 dòng có tổng đa lượng >100 g/100 g
— hầu hết đến từ dữ liệu cộng đồng của Open Food Facts. Hướng xử lý đề xuất: rà soát theo
`id` trong `data/reports/data_quality_report.md` rồi sửa hoặc loại ở nguồn, **không sửa tay
trong database** (sẽ làm mất dấu vết truy nguyên).

Đây là dữ liệu thật nhiều nguồn ghép lại nên độ phủ thưa là **thực tế**, không phải lỗi:
68.732 thực phẩm thiếu năng lượng phần lớn thuộc Foundation Foods — bộ dữ liệu lấy mẫu,
chỉ có số liệu chi tiết cho một phần nhỏ thực phẩm.

## 6. Hạn chế đã biết (ghi rõ để không hiểu sai kết quả)

1. **Nhóm Foundation Foods thưa số liệu.** Chúng vẫn có mặt trong database (để tra cứu nhóm
   thực phẩm) nhưng phần lớn không có năng lượng đo được; giao diện sẽ hiển thị
   “chưa có dữ liệu” chứ không hiển thị 0.
2. **Năng lượng Atwater bị loại có chủ đích.** Foundation Foods công bố năng lượng dạng
   “Atwater General/Specific Factors” (được tính từ chính các đa lượng). Nếu đưa giá trị đó
   vào làm **nhãn huấn luyện** thì mô hình sẽ học được đáp án (rò rỉ dữ liệu). Vì vậy 608
   bản ghi Atwater đã bị loại khỏi nhãn; đổi lại các thực phẩm chỉ có Atwater sẽ thiếu
   năng lượng đo.
3. **Dữ liệu Việt Nam hiện trống (0 bản ghi), và `name_vi` = 0.** Bảng thành phần dinh dưỡng
   Việt Nam có bản quyền không rõ ràng nên **không thể tự ý sao chép**; ngoài ra bộ lọc Open
   Food Facts chỉ giữ sản phẩm đóng gói nên tên thực phẩm trong database **hoàn toàn là tiếng
   Anh và các ngôn ngữ khác** (kiểm tra thật: `select count(*) from foods where name_vi is not
   null and name_vi <> ''` → **0**). Đã chuẩn bị sẵn:
   - `data/external/vn_fct_template.csv` – mẫu 17 cột, có dòng chú thích đơn vị, quy định
     rõ “giá trị chưa biết để trống, tuyệt đối không điền 0”;
   - `scripts/import_vn_fct.py` – importer kiểm tra nghiêm ngặt (khoảng giá trị hợp lệ,
     bắt buộc khai nguồn từng dòng, từ chối cả tệp nếu có vi phạm).
   Người vận hành chỉ cần điền dữ liệu thật vào mẫu rồi chạy importer.
   **Hệ quả hiện tại:** tra cứu bằng tiếng Việt chỉ tìm được trong số tên tiếng Việt có
   trong Open Food Facts và bản ghi nhập tay (ví dụ “Ức Gà Ăn Liền”); các món Việt thuần
   như “cơm trắng” chưa có trong database.
4. **Ảnh huấn luyện.** Food-101 chỉ phủ **chính xác 4/15** lớp món ăn mục tiêu; 5 món Việt
   phải thu thập riêng từ Wikimedia Commons với 41–100 ảnh/lớp — vì vậy độ chính xác của
   lớp `pho_bo` (46 ảnh) thấp hơn hẳn các lớp 100 ảnh (xem `data/reports/image_experiment.md`).
5. **Giấy phép ảnh.** Ảnh Food-101 thuộc Foodspotting, chỉ dùng cho mục đích học thuật
   (scientific fair use); không được tuyên bố giấy phép mở bao trùm cho toàn bộ dataset.
