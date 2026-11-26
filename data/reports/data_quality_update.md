# Cập nhật chất lượng dữ liệu sau đợt Open Food Facts Việt Nam

- Ngày kiểm tra: 2026-11-26 (UTC+07:00)
- CSDL: `data/nutrition.db`
- Báo cáo chi tiết được tạo lại bằng chính script dự án:

```text
D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/Scripts/python.exe scripts/check_data_quality.py --out data/reports/data_quality_report.md
[DB] sqlite+pysqlite:///D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/data/nutrition.db
[REPORT] D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer\data\reports\data_quality_report.md
```

Script mở CSDL ở chế độ chỉ đọc (`mode=ro`, `PRAGMA query_only=ON`). Không có giá trị dinh dưỡng nào bị sửa trong đợt rà soát này.

## 1. So sánh trước và sau

Mốc “trước” lấy từ báo cáo cũ trong git và bản sao lưu ngay trước đợt nhập OFF Việt Nam: `data/backups/nutrition_20261126_070649_pre_off_vietnam.db`. Mốc “sau” lấy từ CSDL hiện tại và báo cáo vừa chạy lại.

| Chỉ số | Trước | Sau | Thay đổi |
|---|---:|---:|---:|
| Tổng thực phẩm | 102.284 | 102.847 | +563 |
| Có năng lượng đo được | 33.552 | 33.649 | +97 |
| Thiếu năng lượng | 68.732 | 69.198 | +466 |
| Không có tên ở cả `name_vi`, `name_en`, `name_normalized` | 390 | 626 | +236 |
| Năng lượng > 900 kcal/100 g | 54 | 55 | +1 |
| Tổng protein + carbohydrate + fat > 100 g/100 g | 198 | 199 | +1 |
| Natri > 40.000 mg/100 g | 22 | 24 | +2 |
| Nhóm gần trùng tên ở nhiều nguồn | 210 | 213 | +3 |
| Dòng `food_nutrients` | 360.670 | 364.611 | +3.941 |
| Tên thay thế | 98.493 | 98.721 | +228 |

Ghi chú: “không có tên” được đếm bằng điều kiện cả ba trường tên sau khi `trim` đều rỗng/NULL. Chỉ số tổng đa lượng dùng cùng phép dựng pivot và ngưỡng `> 100` như `scripts/check_data_quality.py`.

## 2. Ngoại lệ mới so với trước đợt nhập

So sánh theo khóa ổn định `(food_sources.code, foods.source_ref)` giữa CSDL hiện tại và bản sao lưu trước nhập cho thấy **4 bản ghi mới lọt vào ít nhất một ngưỡng cảnh báo**, không có ngoại lệ cũ nào biến mất:

| ID hiện tại | Tên | Nguồn | `source_ref` | Năng lượng | Tổng đa lượng | Natri | Lý do mới |
|---:|---|---|---|---:|---:|---:|---|
| 102.725 | *(không tên)* | `openfoodfacts` | `5359902009068` | NULL | 0 | 100.000 mg | natri > 40.000 mg |
| 102.510 | Raspberry yoghurt crispy wafers | `openfoodfacts` | `80001928` | 533,333 | 189,333 g | 426,667 mg | tổng đa lượng > 100 g |
| 102.339 | Bơ thực vật Trường An | `openfoodfacts` | `8936035100403` | 606 | 0,07 g | 536.000 mg | natri > 40.000 mg |
| 102.604 | Bún | `openfoodfacts` | `8936199400203` | 1.485 | 9,54 g | NULL | năng lượng > 900 kcal |

`Black olives` (2.000 kcal/100 g) vẫn là ngoại lệ nghiêm trọng nhưng **không phải ngoại lệ mới**: bản ghi đã có cùng giá trị trong bản sao lưu trước nhập.

## 3. Mười ngoại lệ năng lượng lớn nhất

Danh sách được sắp giảm dần theo `foods.energy_kcal_per_100g`; tất cả đều đến từ `openfoodfacts`.

| Hạng | ID | Tên | Nguồn | `source_ref` | kcal/100 g |
|---:|---:|---|---|---|---:|
| 1 | 101.424 | Chorizo Rieti Campesino | `openfoodfacts` | `7707300312712` | 3.617,4 |
| 2 | 86.502 | Det Glutenfrie Verksted Søt Bakemiks Økologisk | `openfoodfacts` | `7070848071671` | 3.522 |
| 3 | 92.707 | Topping Syrup Maple Flavour | `openfoodfacts` | `5010115900589` | 3.160 |
| 4 | 88.304 | Chicken Stock Cubes | `openfoodfacts` | `5901135013130` | 2.250 |
| 5 | 94.354 | Black olives | `openfoodfacts` | `0053800026312` | 2.000 |
| 6 | 100.713 | *(không tên)* | `openfoodfacts` | `0076026035531` | 1.828 |
| 7 | 102.604 | Bún | `openfoodfacts` | `8936199400203` | 1.485 |
| 8 | 88.787 | MINI EGGS | `openfoodfacts` | `8000300439625` | 1.430 |
| 9 | 97.964 | Granola Nature Valley Marca Exclusiva Barra Sabores Surtidos | `openfoodfacts` | `0016000264809` | 1.424,8 |
| 10 | 92.859 | *(không tên)* | `openfoodfacts` | `0265891310038` | 1.348 |

## 4. Kiểm chứng số bản ghi theo nguồn bằng SQL

Kết quả lệnh thật:

```text
sources= [('usda_foundation', 68867), ('openfoodfacts', 20563), ('usda_sr_legacy', 7793), ('usda_fndds', 5624), ('manual', 0), ('vn_fct', 0)]
total= 102847
missing_energy= 69198
no_name= 626
high_energy= 55
macro_over_100= 199
```

Tổng theo nguồn khớp 102.847. Nguồn `vn_fct` vẫn có **0** thực phẩm.

## 5. Sao lưu và metadata `vn_fct`

Trước khi sửa metadata, đã chạy `scripts/backup_db.py --keep 9999 --label pre_vn_fct_metadata`:

```text
[v] Đã sao lưu: D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer\data\backups\nutrition_20261126_090926_pre_vn_fct_metadata.db
Kích thước: 76910592 B
integrity_check: ok
sha256: 44615ab7ac38f5d78a1e25a7324cd5197c3ae522f9f1ddb11f3d96d32c335056
File -wal/-shm: không (bản sao tự chứa)
```

Trường metadata `food_sources.note` của `code='vn_fct'` được cập nhật (cùng dấu thời gian kiểm toán `updated_at`) thành:

> Bản in 2007, giấy phép chưa rõ, không tái phân phối; dùng mẫu data/external/vn_fct_template.csv để nhập khi có nguồn hợp lệ

Kiểm tra sau ghi: `license=NULL`, `license_url=NULL`, `vn_fct_foods=0`. Việc để giấy phép NULL là có chủ đích vì chưa xác định được giấy phép; ghi chú cấm tái phân phối thể hiện giới hạn sử dụng hiện tại.

## 6. Kiểm chứng ứng dụng đang chạy

### Trang trạng thái

```text
GET http://127.0.0.1:8000/status -> HTTP 200
Database SQLite: hoạt động
102847 thực phẩm · 6 nguồn dữ liệu · 2 tài khoản · 13 bữa ăn
```

Trang trạng thái đã hiển thị đúng tổng mới **102.847**, không còn số cũ. Endpoint `GET /api/v1/health` cũng trả HTTP 200 và `database.ok=true`.

### Đăng nhập và tra cứu API

```text
POST /api/v1/auth/login -> HTTP 200 (review@example.com)
GET /api/v1/foods?q=phở -> HTTP 200, total=48, returned=20
GET /api/v1/foods?q=bún -> HTTP 200, total=135, returned=20
GET /api/v1/foods?q=sữa -> HTTP 200, total=65, returned=20
```

`returned=20` là số phần tử của trang đầu theo `limit` mặc định; `total` là tổng số kết quả khớp.

## 7. Kết luận

Đợt nhập bổ sung 563 thực phẩm và tăng số bản ghi có năng lượng thêm 97, nhưng cũng làm tăng dữ liệu thiếu tên, thiếu năng lượng và bốn ngoại lệ thuộc các ngưỡng kiểm toán. Dữ liệu Open Food Facts là dữ liệu cộng đồng nên có thể chứa sai đơn vị hoặc giá trị nhập nhầm. Báo cáo chỉ ghi nhận và truy nguyên theo nguồn/barcode; **không sửa tay bất kỳ giá trị dinh dưỡng nào trong database**. Các ngoại lệ cần được đối chiếu và sửa tại nguồn hoặc qua một quy trình hiệu chỉnh có lịch sử, không ghi đè âm thầm trong CSDL.
