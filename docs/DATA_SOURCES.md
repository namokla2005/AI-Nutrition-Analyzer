# NGUỒN DỮ LIỆU VÀ CHẤT LƯỢNG DỮ LIỆU

Cập nhật: 2026-11-26 (UTC+07:00). Mọi con số dưới đây lấy từ truy vấn thật trên
`data/nutrition.db` và từ `scripts/check_data_quality.py`, không phải ước lượng.

---

## 1. Nguồn dữ liệu đang dùng

| Mã nguồn | Tên nguồn | Giấy phép | Bản ghi đã nhập |
|---|---|---|---:|
| `usda_foundation` | USDA FoodData Central – Foundation Foods (2024-10-31) | CC0 1.0 (phạm vi công cộng) | 68.867 |
| `openfoodfacts` | Open Food Facts – trích lọc có giới hạn | Open Database License (ODbL) 1.0 | 20.563 |
| `usda_sr_legacy` | USDA FoodData Central – SR Legacy (2018-04) | CC0 1.0 | 7.793 |
| `usda_fndds` | USDA FoodData Central – Survey/FNDDS (2022-10-28) | CC0 1.0 | 5.624 |
| `vn_fct` | Bảng thành phần dinh dưỡng thực phẩm Việt Nam 2007 (chưa nhập) | **Chưa rõ – không tái phân phối** | **0** (xem §6) |
| `manual` | Người vận hành nhập tay qua API, có khai báo nguồn | theo người nhập | 0 |
| **Tổng** | | | **102.847** |

Trích nguyên văn giấy phép USDA (đọc từ `https://fdc.nal.usda.gov/api-guide`):
> “USDA FoodData Central data are in the public domain and they are not copyrighted.
> They are published under CC0 1.0 Universal (CC0 1.0)” — “No permission is needed for
> their use, but we request that users list FoodData Central as the source of the data”.

Open Food Facts: “The Open Food Facts database is available under the Open Database
License (ODbL).” (`https://world.openfoodfacts.org/data`) → khi tái sử dụng phải ghi nguồn
và giữ nguyên tính mở của dữ liệu phái sinh.

**Đợt bổ sung sản phẩm Việt Nam ngày 2026-11-26:** API v2 với bộ lọc
`countries_tags=vietnam` báo 1.735 sản phẩm; lần thu thập lấy được **1.620 mã vạch duy nhất**,
trong đó importer thêm **563 bản ghi mới** và cập nhật 1.057 bản ghi đã có. Dữ liệu vẫn thuộc
**ODbL 1.0**. Tệp JSONL lưu tại `data/external/openfoodfacts/off_vietnam.jsonl`; chi tiết truy
xuất, giới hạn thu thập và kết quả nhập ở `data/reports/off_vietnam_import_report.md`.

Bảng thành phần dinh dưỡng thực phẩm Việt Nam 2007 có tình trạng giấy phép **chưa rõ**.
Dự án chỉ giữ mẫu nhập liệu, không chép và không tái phân phối nội dung bảng này cho đến khi
có nguồn hợp lệ và quyền sử dụng rõ ràng.

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
| Nhóm gần trùng theo tên ở nhiều nguồn | **213** (cùng một loại thực phẩm xuất hiện ở nhiều nguồn; giữ riêng để bảo toàn truy nguyên) |
| Lệch giữa cache `foods.energy_kcal_per_100g` và bảng chuẩn | **0** |
| Thực phẩm không có số liệu năng lượng | **69.198** (xem §6) |
| Năng lượng > 900 kcal/100 g | **55** (có ngoại lệ OFF sai rõ rệt như “Bún” 1.485 kcal/100 g và “Black olives” 2.000 kcal/100 g) |
| Tổng protein + carb + fat > 100 g/100 g | **199** (lỗi dữ liệu cộng đồng của OFF) |
| Natri > 40.000 mg/100 g | **24** (muối ~40.100 mg là hợp lý; một số sản phẩm OFF sai) |
| Giá trị âm | **0** |
| Độ phủ chất dinh dưỡng | 7,7 % (`energy_kj`) đến 36,9 % (`fat_g`) |
| Đối chiếu năng lượng đo với công thức Atwater (4/4/9) | 23 trong 30 dòng bị gắn cờ “lệch >25 %” có **sai khác tuyệt đối < 25 kcal/100 g** → đây là hệ quả toán học của thực phẩm ít năng lượng (mẫu số nhỏ làm sai số tương đối phóng đại), **không phải lỗi đơn vị**. Chỉ **7 dòng** vừa lệch >25 % vừa lệch ≥25 kcal/100 g là đáng rà lại; sai khác tuyệt đối lớn nhất trong bảng là 150,5 kcal/100 g |

**Kết luận về chất lượng:** phiên bản dữ liệu này **dùng được** cho tra cứu và tính khẩu phần
(sai khác cache = 0, không có giá trị âm, không trùng chính xác), nhưng **không được coi là
sạch tuyệt đối**: còn 55 giá trị năng lượng >900 kcal và 199 dòng có tổng đa lượng >100 g/100 g
— hầu hết đến từ dữ liệu cộng đồng của Open Food Facts. Hướng xử lý đề xuất: rà soát theo
`id` trong `data/reports/data_quality_report.md` rồi sửa hoặc loại ở nguồn, **không sửa tay
trong database** (sẽ làm mất dấu vết truy nguyên).

Đây là dữ liệu thật nhiều nguồn ghép lại nên độ phủ thưa là **thực tế**, không phải lỗi:
69.198 thực phẩm thiếu năng lượng phần lớn thuộc Foundation Foods — bộ dữ liệu lấy mẫu,
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
3. **Nguồn `vn_fct` hiện trống (0 bản ghi), và `name_vi` = 0.** Bảng thành phần dinh dưỡng
   Việt Nam 2007 có giấy phép chưa rõ nên **không sao chép hoặc tái phân phối**. Đợt OFF Việt
   Nam đã bổ sung sản phẩm đóng gói có tên tiếng Việt, nhưng importer lưu tên nguồn vào trường
   tên chung/tiếng Anh; kiểm tra thật `select count(*) from foods where name_vi is not null and
   trim(name_vi) <> ''` vẫn cho **0**. Đã chuẩn bị sẵn:
   - `data/external/vn_fct_template.csv` – mẫu 17 cột, có dòng chú thích đơn vị, quy định
     rõ “giá trị chưa biết để trống, tuyệt đối không điền 0”;
   - `scripts/import_vn_fct.py` – importer kiểm tra nghiêm ngặt (khoảng giá trị hợp lệ,
     bắt buộc khai nguồn từng dòng, từ chối cả tệp nếu có vi phạm).
   Người vận hành chỉ cần điền dữ liệu thật vào mẫu rồi chạy importer.
   **Hệ quả hiện tại:** tra cứu bằng tiếng Việt chỉ tìm được trong số tên tiếng Việt có
   trong Open Food Facts và bản ghi nhập tay (ví dụ “Ức Gà Ăn Liền”); các món Việt thuần
   như “cơm trắng” chưa có trong database.
4. **Ảnh huấn luyện (cập nhật 28/11/2026).** Tập ảnh có **1.784 ảnh / 29 lớp**, mọi đường dẫn
   trong manifest đều tồn tại thật, **không có đường dẫn trùng**; ảnh sai chủ đề đã chuyển sang
   `data/raw/images/_rejected/`. Thành phần: **865 ảnh món Việt từ Wikimedia Commons** (CC0, CC BY,
   CC BY-SA, Public domain; truy nguyên ở `data/reports/commons_provenance.json`), **119 ảnh món Việt
   từ Openverse** (Flickr/Wikimedia qua Openverse API; giấy phép chỉ gồm CC0/CC BY/CC BY-SA — **0 ảnh
   ngoài danh sách**; truy nguyên đủ 7 trường cho 259 ảnh tải về ở
   `data/reports/openverse_provenance.json`) và **800 ảnh Food-101** (fair use).
   Kiểm toán bằng mắt phát hiện nhiều lớp từng lẫn ảnh sai chủ đề rất nặng — ví dụ `canh_chua`:
   23/28 ảnh là vườn, chùa, cây cảnh (không có ảnh món ăn nào), nên chỉ số F1 = 1,0000 của lớp này
   trong model 24 lớp **không có giá trị**. Ngược lại có lớp bị **loại oan**: `banh_khot` 17/20 ảnh
   bị loại nhưng đúng là bánh khọt → đã khôi phục 14 ảnh. Đợt Openverse cũng được soi lại: `bun_dau_mam_tom`
   loại 20/20 đúng, `banh_beo` loại 18/20 đúng, `pho_ga` và `bun_thit_nuong` giữ 20/20 đúng.
   Vì vậy lần huấn luyện đang dùng (**v8**) giữ **25 lớp / 1.688 ảnh** (17 món Việt + 8 lớp Food-101,
   chia 1.181 / 257 / 250); bốn lớp dưới ngưỡng 34 ảnh sạch bị loại: `canh_chua` 27 · `banh_beo` 22 ·
   `banh_khot` 33 · `bun_dau_mam_tom` 14 — cần ảnh do người dùng tự chụp.
   Lưu ý quy trình: `training/image/prepare_dataset.py` từng đổi tên ảnh Openverse (`ov_<hex>`) thành
   `commons_<nhóm số đầu>` nên nhiều ảnh khác nhau ghi đè lẫn nhau (**mất 19 ảnh**, đã khôi phục và
   sửa mã) — chi tiết ở `BAO_CAO_KIEM_THU.md` §7.8.
