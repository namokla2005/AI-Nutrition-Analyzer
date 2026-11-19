# Lớp nhập liệu VN FCT và kiểm toán chất lượng dữ liệu

## Phạm vi

Đã bổ sung hai công cụ, không thay đổi schema, `app/models/**`, `app/core/**`, `app/main.py` hay `data/nutrition.db`:

1. `scripts/import_vn_fct.py`: đọc CSV nhập tay VN FCT, bỏ qua hàng chú thích có trường đầu bắt đầu bằng `#`, kiểm tra đúng 17 cột, kiểm tra từng giá trị và chỉ nhập các hàng hợp lệ.
2. `scripts/check_data_quality.py`: mở SQLite bằng `mode=ro` và `PRAGMA query_only=ON`, in báo cáo tiếng Việt và ghi cùng nội dung báo cáo vào `data/reports/data_quality_report.md`.

Dòng chú thích đầu của `data/external/vn_fct_template.csv` đã được đặt trong một trường CSV có dấu nháy kép; tiêu đề 17 cột được giữ nguyên.

## Quy tắc của bộ nhập

- Bắt buộc có `food_name_vi` để tạo `source_ref` ổn định bằng slug và bắt buộc có `source_name` để truy xuất nguồn.
- Dedupe/upsert theo `(source_id, source_ref)`, trong đó nguồn có mã `vn_fct`.
- `cooking_state` chỉ nhận `raw`, `cooked`, `processed`, `unknown`.
- Giới hạn: năng lượng 0..1000 kcal; protein/fat/carbohydrate/fiber/sugar/moisture/ash 0..100 g; natri 0..40000 mg; phần ăn được 0..100%.
- Ô trống được ghi `NULL`, không đổi thành 0. Khi nhập lại một hàng, ô đã xóa cũng cập nhật giá trị cũ về `NULL`.
- Nếu năng lượng trống nhưng đủ protein/carbohydrate/fat, công cụ tính 4/4/9, gắn `data_quality='estimated'` và liệt kê thực phẩm trong báo cáo nhập.
- Năng lượng cache được đồng bộ bằng `FoodRepository.sync_energy_cache()`.
- Tên nguồn, URL, ghi chú nguồn và phần ăn được được giữ trong `foods.data_note`.
- Mọi vi phạm đều được liệt kê theo số dòng; có vi phạm thì tiến trình trả mã 1.

## Fixture kiểm thử

`data/external/vn_fct_fixture_test.csv` gồm 20 hàng thật trích từ USDA FoodData Central Foundation Foods (hàng đầu là FDC ID 321358, “Hummus, commercial”). Tất cả tên đều có tiền tố `TEST USDA`, nguồn mang nhãn `TEST FIXTURE`, và ghi chú nêu rõ đây **không phải dữ liệu Bảng thành phần thực phẩm Việt Nam**. Fixture chỉ dùng để chứng minh đường nhập hoạt động khi biểu mẫu VN FCT thật chưa có dữ liệu.

## CSDL thử nghiệm và kết quả nhập thực tế

CSDL dùng duy nhất cho kiểm thử:

`sqlite+pysqlite:///D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/data/tmp_qc.db`

Alembic tạo revision `827db6071a8d`; seed thực tế:

```text
[OK] nutrients: +15 mới, tổng 15
[OK] food_sources: +6 mới, tổng 6
```

Công cụ in URL đã giải quyết trước khi truy cập CSDL. Kết quả với template trống:

```text
[DB] sqlite+pysqlite:///D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/data/tmp_qc.db
- Dòng hợp lệ: 0
- Dòng thêm mới: 0
- Dòng cập nhật: 0
- Vi phạm/lỗi: 0
```

Kết quả với fixture:

```text
[DB] sqlite+pysqlite:///D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/data/tmp_qc.db
- Dòng hợp lệ: 20
- Dòng thêm mới: 20
- Dòng cập nhật: 0
- Vi phạm/lỗi: 0
```

Một CSV lỗi tạm thời được chạy để kiểm tra nhánh từ chối. Công cụ trả mã 1 và báo đủ 12 vi phạm: thiếu `source_name`, trạng thái `fried`, edible portion 101, energy 1001, protein -1, fat/carb/fiber/sugar/moisture 101, sodium 40001 và ash -1.

## Khuyết tật được cấy và kết quả kiểm toán thực tế

Sau 20 hàng fixture, đã cấy đúng ba khuyết tật vào CSDL tạm:

```text
planted duplicate_food=1 cache_mismatch=1 implausible_energy=1
total_foods 23
```

Kết quả thực tế từ `scripts/check_data_quality.py`:

```text
Tổng thực phẩm: 23
Trùng chính xác source_id + source_ref: 0 nhóm
Gần trùng name_normalized ở nhiều nguồn: 1 nhóm
  test usda 321358 hummus commercial | 2 hàng | 2 nguồn | vn_fct,manual
Cache năng lượng khác canonical: 1
  id 22 | PLANTED cache mismatch | cache 123.0 | canonical 100.0
Không có năng lượng ở cả cache lẫn canonical: 0
Năng lượng > 900 kcal/100 g: 1
  id 23 | PLANTED implausible 2000 kcal | 2000.0
Tổng ba macro > 100 g/100 g: 0
Giá trị âm: 0
Natri > 40000 mg/100 g: 0
cooking_state='unknown': 23/23 (100.0%)
Atwater: 21 thực phẩm; sai khác tuyệt đối trung bình 9.160 kcal/100 g; lệch >25%: 0
Tổng kết: WARN — trùng lặp, cache năng lượng không đồng bộ, giá trị phi lý.
```

Hồ sơ thiếu được tính trên đủ 15 nutrient code. Ví dụ thực tế: `energy_kcal` có 23, NULL 0; `fiber_g` có 10, NULL 13; `sugar_g`, `energy_kj`, `calcium_mg`, `cholesterol_mg`, `iron_mg`, `potassium_mg`, `vitamin_c_mg` đều có 0, NULL 23 và được ghi rõ là thưa.

Các số trên cũng có trong `data/reports/data_quality_report.md`, gồm bảng ví dụ tối đa 30 hàng cho từng nhóm.

## Xác minh chỉ đọc và hồi quy

Hash CSDL trước và sau khi chạy auditor giống hệt nhau:

```text
sha256_before=a21bfa710fc1574bb6e8526e95c6a6599ba5aa1b63a03c3c23af0f08d8347de1
sha256_after=a21bfa710fc1574bb6e8526e95c6a6599ba5aa1b63a03c3c23af0f08d8347de1
```

Các kiểm tra tự động cho validator/auditor và toàn bộ `tests/unit` đều qua:

```text
.......................................... [100%]
```

CSDL `data/tmp_qc.db`, các file WAL/SHM, CSV lỗi, script cấy lỗi và test tạm đã được xóa; vì vậy toàn bộ hàng cấy cũng đã được loại bỏ. `data/nutrition.db` không được truy cập hoặc sửa đổi.
