# TIẾN ĐỘ DỰ ÁN – AI NUTRITION ANALYZER

**Cập nhật lần cuối:** 2026-11-19 03:45 (UTC+07:00)
**Giai đoạn hiện tại:** **GIAI ĐOẠN 1 (dữ liệu) + GIAI ĐOẠN 3 (backend) song song** — ML đã bắt đầu ở luồng riêng
**Thư mục dự án:** `D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer`

---

## 1. Bảng trạng thái 7 giai đoạn

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 0 | Khảo sát môi trường | ✅ **Hoàn thành** – xem `docs/ENVIRONMENT_REPORT.md` |
| 1 | Database và dữ liệu | 🔵 **Đang làm** – schema/migration/seed/importer đã có; chờ chạy importer trên DB thật và kiểm tra chất lượng dữ liệu |
| 2 | Machine Learning (ảnh + 3 thuật toán hồi quy) | 🔵 **Đang làm** – pipeline huấn luyện ảnh đã chạy thử (dữ liệu tổng hợp); thực nghiệm hồi quy do luồng riêng đang chạy |
| 3 | Backend FastAPI | 🟢 **Gần xong** – 23 đường dẫn API, 142 bài kiểm thử qua |
| 4 | Frontend (9 trang, tiếng Việt) | ⬜ Chưa bắt đầu |
| 5 | Tích hợp Qwen qua Ollama | 🟢 **Đã chạy thật** – Qwen trả lời đúng số liệu từ database, có grounding + ghi lịch sử |
| 6 | Kiểm thử và hoàn thiện | ⬜ Chưa bắt đầu |

## 2. Đã hoàn thành (kèm bằng chứng)

### Giai đoạn 0
- Khảo sát phần cứng, ổ đĩa, Python, GPU/CUDA, Ollama/Qwen, mạng, công cụ hỗ trợ GPT → `docs/ENVIRONMENT_REPORT.md`.
- Xác định 7 vấn đề tương thích và cách xử lý (đã ghi trong báo cáo môi trường).

### Giai đoạn 1 (phần lõi)
- Tạo cấu trúc thư mục dự án đúng §10 (có bổ sung `data/reports`).
- `.venv` với **155 gói**, Python 3.12.8, gồm `torch 2.15.0+cpu`, `torchvision 0.29.2+cpu`, `scikit-learn 1.9.1`, `pandas 3.1.1`, `fastapi 0.165.0`, `SQLAlchemy 2.1.9`, `alembic 1.20.1`, `argon2-cffi 25.1.0`.
- **14 bảng** SQLAlchemy 2.0 (Mapped/mapped_column) + `alembic_version` = **15 bảng**, **31 index**:
  `users, user_profiles, food_sources, foods, nutrients, food_nutrients, food_aliases, food_images, meals, meal_items, model_versions, predictions, chat_sessions, chat_messages`.
- Khóa ngoại có `ON DELETE CASCADE/SET NULL/RESTRICT` phù hợp; ràng buộc `CHECK` cho `cooking_state`, `meal_type`, `role`, giá trị dinh dưỡng ≥ 0; ràng buộc `UNIQUE` cho `(food_id, nutrient_id)` và `(source_id, source_ref)`.
- Alembic: revision đầu tiên `827db6071a8d_init_schema`, `render_as_batch=True` (SQLite), `compare_type=True`.
- Seed danh mục: **15 chất dinh dưỡng**, **6 nguồn dữ liệu**; script idempotent (chạy lại: `+0 mới`).
- Kiểm chứng: `PRAGMA foreign_keys = 1`, `journal_mode = wal`.
- File khởi chạy website: `START_WEBSITE.bat`, `run.py`, `scripts/setup_env.bat`, `scripts/init_db.bat`.
- Kiểm chứng chạy thật: `GET /api/v1/health` → 200 với `database.ok = true`; `GET /docs` → 200.

### Nghiệp vụ lõi (không phụ thuộc nguồn dữ liệu)
- `app/services/nutrition.py`: công thức khẩu phần theo §5.3 (`kcal = kcal/100g × g / 100`), cộng dồn nhiều dòng có **báo rõ chất nào bị thiếu dữ liệu**, phân bổ năng lượng 4/4/9, ước lượng Atwater (chỉ dùng khi nguồn không có sẵn năng lượng), tỷ lệ đạt mục tiêu. Chất thiếu luôn trả `None`, **không bao giờ tự điền 0**.
- `app/repositories/food_repository.py`: tìm kiếm **tiếng Việt có dấu và không dấu** (dùng `name_normalized` + bảng `food_aliases`), lọc theo nhóm/trạng thái chế biến/khoảng calo, phân trang, đếm theo nguồn, `upsert_nutrient` (không tạo bản ghi trùng), `sync_energy_cache` (đồng bộ theo TD-04).
- `scripts/backup_db.py`: sao lưu bằng API `sqlite3.Connection.backup` (an toàn cả khi DB đang ghi), **checkpoint + chuyển về chế độ DELETE để bản sao là một file tự chứa**, in `integrity_check` + `sha256`, xoay vòng bản sao cũ theo `--keep`, chế độ `--verify`.
- Kiểm thử: `pytest.ini` + **142 bài kiểm thử** (8 file: đơn vị + tích hợp + ML) — tất cả chạy qua; 1 bài gọi Qwen thật chỉ chạy khi đặt `ANA_LIVE_OLLAMA=1`.

### Dữ liệu thật đã thu thập và **đã xác minh lại độc lập** (Giai đoạn 1)
| Nguồn | Kết quả xác minh của tôi (không chỉ tin báo cáo subagent) |
|---|---|
| USDA SR Legacy 2018-04 | 6.074.592 B, **sha256 khớp** `b8081729…e6fd0`; `food.csv` 7.794 dòng, `food_nutrient.csv` 644.126 dòng, `nutrient.csv` 475 dòng |
| USDA Foundation Foods 2024-10-31 | 3.258.886 B, **sha256 khớp** `8587f941…9edf44`; `food.csv` 68.877, `food_nutrient.csv` 149.616, `nutrient.csv` 478 |
| USDA Survey/FNDDS 2022-10-28 | 4.427.502 B, **sha256 khớp** `e9a10d13…37b958`; `food.csv` 5.625, `food_nutrient.csv` 365.561, `nutrient.csv` 475 |
| Open Food Facts | `off_subset.csv` **đúng 20.000 dòng**, 14 cột, **20.000/20.000 dòng có đủ 4 macro**, 1.132 dòng liên quan Việt Nam |
| Năng lượng đo được | SR Legacy: id 1008/nbr 208 `Energy [KCAL]` trên 7.793 thực phẩm (kJ trên đúng 7.793); Foundation: 135 (kJ 135) + 2 biến thể Atwater 309/299; Survey: 5.624 (kJ **0**) |
| **Bẫy join của Survey** | Đã tự kiểm chứng: `food_nutrient.nutrient_id` khớp `nutrient.id` 148/148 (SR Legacy), 179/180 (Foundation) nhưng **0/65** ở Survey; khớp `nutrient.nbr` **65/65** ở Survey. Bắt buộc chọn khóa join theo từng bộ dữ liệu |
| Giấy phép | USDA: **CC0 1.0, phạm vi công cộng** (trích nguyên văn trong `data/reports/usda_inventory.md`); Open Food Facts: **ODbL**; Food-101: chỉ dùng cho nghiên cứu/scientific fair use |
| Bản đồ 15 lớp ảnh | Food-101 chỉ phủ **chính xác 4/15** lớp (pizza, hamburger, sushi, steak); 6 lớp gần đúng; **5 món Việt không có** → phải thu thập riêng từ Wikimedia Commons |
| Wikimedia Commons | 438 tệp trong 7 chuyên mục, cả 438 có giấy phép tự do (CC0/CC BY/CC BY-SA/Public domain); script thu thập đã chạy thật, tải được 2 ảnh + 2 tệp sidecar |

### Kết quả huấn luyện (2 luồng ML do subagent thực hiện, tôi đã kiểm chứng lại)

**Kiểm chứng artifact trên đĩa (không chỉ tin báo cáo):**
- 16/16 tệp tồn tại, `models/regression/random_forest.joblib` thật là **53.563.091 B**.
- `image_dataset_manifest.csv`: **đúng 1.208 dòng**, 15 lớp, chia `train 847 / val 181 / test 180`; **cả 1.208 đường dẫn đều tồn tại thật trên đĩa** và `data/raw/images` có đúng 1.208 ảnh `.jpg` — khớp chính xác lời khai của subagent.
- `models/regression/*_metadata.json` là **sklearn `Pipeline`** (ColumnTransformer: 6 feature số + 2 feature phân loại) → tầng suy luận nhận DataFrame thô.

**Thực nghiệm hồi quy năng lượng (dữ liệu USDA thật, 7.928 dòng):**
| Model | MAE (test) | RMSE (test) | R² (test) |
|---|---|---|---|
| **Random Forest** (được chọn) | **5,2003** | **10,2751** | **0,9965** |
| Linear Regression | 5,3624 | 9,3263 | 0,9971 |
| Gradient Boosting | 6,7506 | 12,5023 | 0,9948 |
| Baseline (dự đoán trung bình) | 135,2988 | 173,5449 | −0,0014 |

- Chọn model theo **RMSE trên tập validation** (RF 10,2175 < Linear 10,8351) — ghi rõ trong metadata.
- **Kiểm soát leakage**: chỉ dùng `Energy [KCAL]` nguồn số 208 làm target; loại 608 bản ghi năng lượng Atwater (957/958) và 205 thực phẩm chỉ có Atwater; loại cả cột kJ khỏi feature.
- Chia tập theo nhóm mô tả chuẩn hóa (`GroupShuffleSplit`) → giao nhóm giữa các tập bằng 0; tiền xử lý chỉ học từ tập train.
- Feature thiếu: `fiber_g` 638 dòng và `ash_g` 3 dòng được điền bằng trung vị **học từ tập train** (0,3 và 1,15) — có ghi lại trong metadata; target thiếu thì **loại dòng, không nội suy**.
- **Kiểm chứng tích hợp**: tôi nạp lại model vào `app/ml/regression_model.py`, dự đoán cho cơm trắng chín (giá trị thật 130 kcal/100 g) → **126,9 kcal/100 g**, nằm trong sai số MAE 5,2 của model.

**Nhận diện ảnh — đã huấn luyện thật xong** (`training/image/train.py`, 713,6 giây trên CPU):
- 15 lớp, transfer learning MobileNetV3-Small, 847 ảnh train / 181 validation / 180 test.
- **Accuracy trên tập test 0,7889 · macro F1 0,763**; epoch tốt nhất là 13/15.
- Lớp yếu nhất: `banh_xeo` F1 0,444 (chỉ 6 mẫu test), `pho_bo` 0,5 (7 mẫu), `pasta` 0,615 —
  đúng những lớp thiếu ảnh nhất. Lớp 100 ảnh đạt 0,73–0,95.
- **Kiểm chứng qua API thật**: ảnh `pizza` → pizza 96,9 %; `sushi` → sushi 98,1 %;
  `banh_mi` → bánh mì 99,1 %; ảnh `pho_bo` → salad 60,8 % (sai, phù hợp với F1 0,5 của lớp này).
- Máy chủ giữ model trong bộ nhớ: 7,8 giây cho lần gọi đầu, sau đó 23–27 ms.

### Giao diện (Giai đoạn 4) – phần khung do tôi làm, 7 trang do 5 luồng song song
- `app/templates/base.html` + `base_auth.html`: bố cục sidebar 7 mục, topbar, vùng flash/toast, favicon, đăng xuất dùng chung; responsive (dưới 860 px thì sidebar trượt).
- `app/static/css/app.css`: hệ thống thiết kế dùng biến CSS (có dark mode theo hệ điều hành), lưới/thẻ/bảng/nút/nhãn trạng thái/skeleton/empty-state.
- `app/static/js/api.js`: lớp gọi API dùng chung `ANA` — bọc `fetch`, xử lý lỗi tiếng Việt (kể cả mảng lỗi validate của FastAPI), `ANA.num()` hiển thị **"chưa có dữ liệu"** thay vì số 0 cho giá trị `null`, trạng thái đang tải, toast/flash, `ANA.chart()` có cảnh báo khi Chart.js không tải được.
- `app/pages.py`: 9 tuyến trang + `/status` (trang trạng thái cũ chuyển từ `/` sang `/status`); mọi trang cần đăng nhập đều chuyển hướng về `/login?next=…`; trang nào chưa có template thì hiển thị thông báo trung thực thay vì lỗi 500.
- **Lỗi thật đã sửa**: script trong trang chạy trước `api.js` (do `defer`) → handler không được gắn → biểu mẫu đăng nhập tự submit kiểu GET và **đưa mật khẩu lên URL**. Đã nạp `api.js` đồng bộ và thêm `method="post"` cho các biểu mẫu xác thực. Kiểm chứng lại bằng trình duyệt thật: sai mật khẩu → hiện thông báo tiếng Việt; đăng ký → chuyển tới `/dashboard` với sidebar 7 mục.
- Kiểm thử: `tests/integration/test_pages.py` – **21 bài** (chuyển hướng khi chưa đăng nhập, vào được khi đã đăng nhập, tiêu đề trang riêng, tài nguyên tĩnh).

### Giai đoạn 3 – Backend (đã chạy)
- `app/core/deps.py`: xác thực qua cookie phiên ký; `user_id` **luôn** lấy từ phiên server, không nhận từ client.
- `app/api/v1/auth.py`: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/session`; cookie `HttpOnly` + `SameSite=Lax`.
- `app/api/v1/users.py`: `GET/PUT /users/me`, `PUT /users/me/password`, `DELETE /users/me` (bắt buộc gõ `DELETE` để xác nhận, xóa theo CASCADE toàn bộ dữ liệu liên quan).
- `app/api/v1/foods.py`: `GET /foods` (tra cứu có dấu/không dấu, lọc, phân trang), `GET /foods/filters`, `GET /foods/{id}`, `GET /foods/{id}/portion`, `POST /foods` (cần đăng nhập + bắt buộc khai nguồn).
- `app/api/v1/meals.py`: `POST /meals`, `GET /meals` (lọc theo ngày/loại bữa, phân trang), `GET /meals/{id}`, `PUT /meals/{id}`, `DELETE /meals/{id}`. Mọi truy vấn lọc theo `user_id` từ phiên → người khác nhận 404.
- `app/api/v1/statistics.py`: `GET /statistics/daily` (tổng ngày + chia theo bữa + % mục tiêu), `GET /statistics/weekly` (chuỗi 7 ngày Thứ Hai→Chủ Nhật), `GET /statistics/monthly` (chuỗi theo số ngày thực của tháng).
- `app/core/timeutil.py`: quy đổi UTC → giờ Việt Nam cho mốc ngày (TD-08); có kiểm thử riêng cho ranh giới 18:00 UTC = 01:00 hôm sau giờ Việt Nam.
- `app/services/meal_service.py`: tính và **lưu snapshot** từng món khi ghi bữa ăn (§7.4), năng lượng ưu tiên số đo và ghi rõ `estimated_atwater` khi phải ước lượng.
- `app/ml/`: `ImageClassifier` (MobileNetV3-Small, hợp đồng file `models/image/best.pt` + `latest.json`) và `RegressionModel` (joblib + `latest.json`), nạp model một lần, chạy CPU. **Nếu chưa có model thì `is_available=False` và API trả 503 kèm lý do — không bao giờ trả nhãn/số giả.**
- `app/services/upload_service.py`: kiểm tra ảnh **nhiều lớp** trước khi lưu — giới hạn dung lượng, chữ ký nhị phân (magic bytes), Pillow phải mở + `verify()` được ảnh, kích thước tối thiểu, chặn đuôi file thực thi/script, và **tên file lưu trên đĩa do hệ thống sinh** (không dùng tên người dùng gửi lên → chống đường dẫn thoát). Có `purge_expired()` theo chính sách lưu trữ.
- `app/api/v1/predict.py`: `GET /predict/models` (nói thật model nào chưa có), `POST /predict/image` (Top-3 + confidence + `needs_confirmation` khi dưới ngưỡng + gợi ý món khớp nhãn), `GET /predict/images/{id}` (chỉ chủ sở hữu), `POST /predict/nutrition` (**số liệu đo trong DB luôn được ưu tiên**; chỉ khi thiếu mới dùng model và nói rõ là giá trị ước lượng, kèm MAE/RMSE/R² của model).
- `app/integrations/ollama_client.py` + `app/services/assistant_service.py` + `app/api/v1/assistant.py`: trợ lý AI. Backend dựng ngữ cảnh từ database (tổng hôm nay, mục tiêu, chi tiết bữa, tổng tuần, và **tự tìm món được nhắc trong câu hỏi kể cả khi gõ không dấu**), rồi Qwen chỉ diễn giải. `think=false` để không đốt token vào phần suy luận. `POST /assistant/chat`, `GET /assistant/history`, `GET /assistant/status`. Mọi phản hồi trả kèm `context_used` để người dùng tự kiểm chứng con số.
- `training/image/train.py`: huấn luyện MobileNetV3-Small bằng transfer learning trên CPU, đọc manifest `data/processed/image_dataset_manifest.csv` (hoặc tự quét `data/raw/images/<lớp>/`), data augmentation, AdamW + CosineAnnealingLR, early stopping, lưu `models/image/best.pt` + `latest.json` **đúng hợp đồng mà `app/ml/image_classifier.py` đọc**, và tự sinh `data/reports/image_experiment.md` + biểu đồ đường cong/ma trận nhầm lẫn. Mọi số liệu trong báo cáo do chính lần chạy sinh ra.
- Trang `/`: thêm favicon inline (hết lỗi 404 `/favicon.ico` trong log trình duyệt).
- `app/services/auth_service.py` (Argon2id, chống dò email qua thời gian phản hồi, rehash tự động), `app/services/food_service.py` (báo rõ chất thiếu dữ liệu, ước lượng Atwater chỉ khi nguồn không có số đo, và nói rõ là ước lượng).
- **Kiểm chứng trên server thật** (`http://127.0.0.1:8010`, DB thật): đăng ký tên tiếng Việt → 201, `GET /users/me` → 200, trùng email → 409, tạo thực phẩm có nguồn → 201, tra cứu `q=pho bo` → 1 kết quả, `q=Phở` → 1 kết quả, khẩu phần 150 g → **142,5 kcal** (= 95 × 150/100) với `kcal_source=measured` và thiếu `fiber_g/sugar_g/sodium_mg` được báo đúng, khối lượng 0 g → 422, đổi mật khẩu → 200, đăng xuất → 200 rồi `GET /users/me` → 401, đăng nhập mật khẩu cũ → 401 / mật khẩu mới → 200, xóa tài khoản → 200. Dữ liệu kiểm thử đã được **dọn sạch** khỏi DB.

## 3. Đang thực hiện

Ba luồng thu thập dữ liệu chạy song song bằng subagent (không dùng dữ liệu giả):
1. **USDA FoodData Central** – tải 3 bộ CSV bulk → `data/external/usda/` + `data/reports/usda_inventory.md`.
2. **Open Food Facts** – trích lọc có giới hạn (~20.000 dòng) từ dump 1,54 GB → `data/external/openfoodfacts/` + báo cáo kiểm kê.
3. **Nguồn dữ liệu Việt Nam + ảnh** – xác minh nguồn có thể tải của bảng thành phần dinh dưỡng Việt Nam; đối chiếu Food-101 với 15 lớp mục tiêu; đếm ảnh thật có giấy phép trên Wikimedia Commons; viết `scripts/collect_vn_images.py`.

## 4. Chưa thực hiện (kế hoạch gần)

- `scripts/import_usda.py`, `scripts/import_openfoodfacts.py`, `scripts/import_vn_fct.py` + chuẩn hóa đơn vị + phát hiện trùng.
- `scripts/check_data_quality.py` (dữ liệu trùng/thiếu/sai đơn vị; đối chiếu `foods.energy_kcal_per_100g` với `food_nutrients`).
- `docs/DATA_SOURCES.md` (nguồn, đơn vị, giấy phép, thời điểm nhập).
- Thu thập ảnh cho các lớp món Việt Nam; chốt danh sách lớp huấn luyện thực tế.
- Kết thúc Giai đoạn 1 khi database chạy và các kiểm tra cốt lõi đạt (đúng điều kiện chuyển giai đoạn §14).

## 5. Lỗi đã gặp và cách xử lý

| # | Lỗi | Nguyên nhân | Cách xử lý | Trạng thái |
|---|---|---|---|---|
| 1 | `UnicodeDecodeError: 'charmap' codec ... 0x8d` khi chạy Alembic | `alembic.ini` chứa chữ tiếng Việt, `configparser` đọc bằng cp1252 | Chuyển nội dung `alembic.ini` sang ASCII thuần + ghi chú lý do | ✅ Đã sửa |
| 2 | `sqlalchemy.exc.ArgumentError: Executable SQL or text() construct expected, got None` khi seed | Đoạn mã chết còn sót trong script seed | Xóa đoạn mã thừa, chạy lại | ✅ Đã sửa |
| 3 | Câu trả lời của Qwen rỗng (`content = ""`) | Model thinking đốt hết token vào trường `thinking` | Đưa `OLLAMA_THINK=false`, `OLLAMA_NUM_PREDICT=400` vào cấu hình | ✅ Đã xử lý ở tầng cấu hình |
| 4 | `torch.cuda.is_available() == False` | PyTorch CPU + GPU Pascal sm_61 không còn được build | Chốt phương án CPU, ghi vào TD-03 | ✅ Đã quyết định |
| 5 | Kiểm thử `test_khong_them_alias_trung` **thất bại** (`assert 2 == 1`) — thêm "Phở Bò" và "pho bo" sinh 2 alias trùng khóa tìm kiếm | `SessionLocal` đặt `autoflush=False`, nên `SELECT` kiểm tra trùng không thấy bản ghi vừa `add()` | Thêm `db.flush()` sau khi thêm alias và sau `upsert_nutrient` | ✅ Đã sửa |
| 6 | Bản sao lưu SQLite sinh thêm file `.db-wal`/`.db-shm` → bản sao không tự chứa, có nguy cơ thiếu dữ liệu khi phục hồi | DB nguồn ở chế độ WAL nên bản sao cũng mang chế độ WAL | Sau khi backup: `PRAGMA wal_checkpoint(TRUNCATE)` + `PRAGMA journal_mode=DELETE`, xóa file phụ và **kiểm tra lại** rằng không còn file phụ (nếu còn thì báo lỗi) | ✅ Đã sửa |
| 7 | `POST /api/v1/foods` trả `source_code = null` (kiểm thử tích hợp phát hiện) | Router gọi `serialize_food(food)` mà không truyền nguồn dữ liệu | Trả về `get_food_detail()` để luôn kèm thông tin nguồn | ✅ Đã sửa |
| 8 | `curl -d '{...tiếng Việt...}'` → HTTP 400 `"There was an error parsing the body"` | `curl.exe` trên Windows nhận tham số dòng lệnh qua bảng mã ANSI nên chuỗi UTF-8 bị hỏng (cùng byte đó ghi ra file và gửi bằng `--data-binary @file` thì thành công; `python.exe` nhận tham số UTF-8 đúng) | Dùng file UTF-8 + `--data-binary @file` khi payload có tiếng Việt | ✅ Đã xác định nguyên nhân |
| 9 | Bản ghi `foods` do tài khoản kiểm thử tạo vẫn còn lại sau khi xóa tài khoản | Xóa user CASCADE tới `meals`/`chat` nhưng `foods` là dữ liệu tham chiếu dùng chung (FK `RESTRICT`) | Xóa tường minh bản ghi kiểm thử; đã dọn sạch DB (users=0, foods=0, food_nutrients=0) | ✅ Đã dọn |
| 10 | Mở `http://127.0.0.1:8010/` chỉ thấy `{"detail":"Not Found"}` | Chưa có route cho `/` (giao diện chính thức thuộc Giai đoạn 4) nên FastAPI trả 404 — máy chủ vẫn hoạt động bình thường | Thêm trang trạng thái tại `/` (hiển thị tình trạng database, số bản ghi thật, kết nối Ollama) và **đổi cổng mặc định sang 8000** theo yêu cầu | ✅ Đã sửa |
| 11 | `/favicon.ico` liên tục 404 trong log trình duyệt | Trang chưa khai báo icon | Nhúng favicon SVG bằng `data:` URI ngay trong trang (không cần file rời) | ✅ Đã sửa |
| 12 | Kiểm thử `test_png_hop_le` thất bại: ảnh 40×30 bị từ chối | **Lỗi ở bài kiểm thử**, không phải ở code: quy tắc tối thiểu 32×32 là hợp lý, ảnh mẫu của tôi cao 30 px | Sửa ảnh mẫu thành 40×36 | ✅ Đã sửa |
| 13 | Khi chưa có model hồi quy, `POST /predict/nutrition` trả thông báo chung chung, không nói thực phẩm thiếu feature gì | Hàm lấy danh sách feature từ metadata model; metadata chưa có nên danh sách rỗng → không phát hiện được feature thiếu | Dùng danh sách feature mặc định khi chưa có metadata, tách rõ 2 trường hợp và trả `missing_features` cụ thể | ✅ Đã sửa |

## 6. Kết quả kiểm thử đã chạy

| Kiểm thử | Lệnh | Kết quả |
|---|---|---|
| Migration | `alembic upgrade head` | ✅ `Running upgrade -> 827db6071a8d` |
| Bảng & index trong SQLite | truy vấn `sqlite_master` | ✅ 15 bảng, 31 index |
| Khóa ngoại | `PRAGMA foreign_keys` qua engine | ✅ `1` |
| Chế độ ghi | `PRAGMA journal_mode` | ✅ `wal` |
| Seed idempotent | chạy `seed_reference_data.py` 2 lần | ✅ lần 2: `+0` bản ghi mới |
| Health API | `GET /api/v1/health` | ✅ 200, `database.ok = true` |
| Tài liệu API | `GET /docs` | ✅ HTTP 200 |
| Codex CLI GPT-5.6-Sol | `codex exec --sandbox read-only -m gpt-5.6-sol -c model_reasoning_effort=high "..."` | ✅ trả đúng chuỗi yêu cầu, 3.003 token |
| Bộ kiểm thử đơn vị | `.venv\Scripts\python.exe -m pytest` | ✅ **40 passed in 1.41s**, exit code 0 |
| Bộ kiểm thử đầy đủ (đơn vị + tích hợp API) | `.venv\Scripts\python.exe -m pytest` | ✅ **98 passed in 22.67s**, exit code 0 |
| Nhật ký ăn uống trên server thật | HTTP thật: tạo bữa trưa 200 g + bữa sáng 100 g | ✅ bữa trưa = **260 kcal** (130 × 200/100), phân bổ 4/4/9 = 8,6 % / 89,3 % / 2,1 %; danh sách = 2 bữa |
| Thống kê ngày | `GET /statistics/daily?day=2026-11-18` | ✅ **390 kcal**, mục tiêu 2000 → 19,5 %, còn lại 1610 kcal; chia theo bữa: breakfast 130, lunch 260 |
| Thống kê tuần | `GET /statistics/weekly?any_day=2026-11-18` | ✅ 2026-11-16 → 2026-11-22 (7 ngày), 1 ngày có dữ liệu, TB 55,71 kcal/ngày |
| Thống kê tháng | `GET /statistics/monthly?year=2026&month=11` | ✅ đúng **30 ngày**, tổng 390 kcal |
| Sửa/xóa bữa ăn | `PUT /meals/{id}` (300 g) rồi `DELETE /meals/{id}` | ✅ 200 rồi 204, danh sách về 0 |
| Snapshot không đổi theo dữ liệu nguồn | đổi năng lượng thực phẩm 130 → 500 kcal sau khi đã ghi bữa ăn | ✅ lịch sử vẫn là 130 kcal (đúng §7.4) |
| Cách ly dữ liệu giữa người dùng | tài khoản B đọc/sửa/xóa bữa ăn của A | ✅ tất cả trả 404; thống kê của B = 0 món |
| Kiểm thử đầy đủ (đơn vị + tích hợp) | `.venv\Scripts\python.exe -m pytest` | ✅ **122 passed in 31.30s**, exit code 0 |
| Chặn tệp nguy hiểm | đổi tên PNG thành `virus.exe`; script `#!/bin/sh` đổi đuôi `.jpg` | ✅ cả hai đều bị từ chối HTTP 400, **không lưu file nào** (thư mục `uploads/` rỗng) |
| Chưa có model thì báo thật | `POST /predict/image` khi chưa huấn luyện | ✅ HTTP 503 kèm hướng dẫn; `GET /predict/models` trả `available=false` + lý do cụ thể |
| Ưu tiên số liệu đo hơn model | `POST /predict/nutrition` với thực phẩm có 130 kcal/100 g | ✅ `source=database`, 250 g → **325,0 kcal** (không gọi model) |
| Không bịa khi thiếu dữ liệu | thực phẩm thiếu năng lượng + thiếu feature | ✅ `source=unavailable`, `kcal=None`, liệt kê đúng `missing_features` |
| Luồng huấn luyện nhận diện ảnh | `pytest tests/ml/test_training_smoke.py -v` (dữ liệu tổng hợp 3 lớp × 12 ảnh) | ✅ **5 passed in 65.08s**, exit 0 — model lưu ra nạp lại được bằng `ImageClassifier`, top-3 đúng nhãn/giảm dần; tôn trọng cột `split` của manifest; thiếu dữ liệu → exit 2 + không sinh file model; 1 lớp → từ chối phân loại |
| Toàn bộ bộ kiểm thử | `.venv\Scripts\python.exe -m pytest` | ✅ **142 passed, 1 skipped in 72.15s**, exit code 0 (bài bị skip là bài gọi Qwen thật, xem dòng dưới) |
| **Qwen thật qua Ollama** | `ANA_LIVE_OLLAMA=1 pytest tests/integration/test_assistant_ollama_live.py -v -s` | ✅ 1 passed in 13.11s — Qwen trả lời: *"Theo dữ liệu cung cấp, hôm nay bạn đã ăn 260.0 kcal (từ bữa lunch)."* (10.645 ms, 24 token) |
| Trợ lý AI trên server thật | hỏi tổng calo + mục tiêu, rồi hỏi về một món | ✅ *"Bạn đã ăn 390.0 kcal hôm nay, đạt 19.5% của mục tiêu 2000.0 kcal. Còn thiếu khoảng 1610.0 kcal"* — **khớp chính xác số liệu trong DB**; câu 2: *"Trong 100g Cơm trắng chín, bạn đã ăn 130.0 kcal."* (1.645 ms khi model đã nạp sẵn) |
| Lịch sử trò chuyện | `GET /assistant/history` | ✅ 1 phiên, 4 tin nhắn (2 câu hỏi + 2 trả lời) |
| Chu trình xác thực trên server thật | HTTP thật tới `127.0.0.1:8010` (đăng ký/đăng nhập/đổi mật khẩu/xóa tài khoản) | ✅ 16 bước, mã trạng thái đúng như mong đợi (201/200/409/422/401/200) |
| Tra cứu không dấu trên dữ liệu thật | `GET /foods?q=pho bo` và `q=Phở` | ✅ mỗi truy vấn trả đúng 1 bản ghi |
| Tính khẩu phần trên dữ liệu thật | `GET /foods/{id}/portion?weight_g=150` | ✅ `kcal = 142.5`, `kcal_source = measured`, báo thiếu `fiber_g, sugar_g, sodium_mg` |
| Sao lưu database | `.venv\Scripts\python.exe scripts\backup_db.py --keep 10 --label ...` | ✅ `integrity_check = ok`, không còn file `-wal`/`-shm`, 200.0 KB |
| Phục hồi từ bản sao lưu | mở file backup bằng engine riêng, so sánh với DB đang dùng | ✅ 15 bảng giống nhau, revision `827db6071a8d` giống nhau, số bản ghi từng bảng giống nhau, đọc được bằng SQLAlchemy |
| File khởi chạy `.bat` | `cmd /c START_WEBSITE.bat --no-browser --port 8011` | ✅ tự kiểm tra `.venv`/`.env`/database/Ollama → server lên, `GET /api/v1/health` → 200 OK |

## 7. File đã tạo/thay đổi

```
AI-Nutrition-Analyzer/
├── .env                     (đã sinh SECRET_KEY ngẫu nhiên 64 ký tự, không commit)
├── .env.example             (mẫu cấu hình, không chứa secret thật)
├── .gitignore
├── requirements.txt
├── alembic.ini              (ASCII-only)
├── run.py                   (điểm khởi chạy, tự mở trình duyệt, tự chọn cổng)
├── pytest.ini               (cấu hình kiểm thử, pythonpath = .)
├── START_WEBSITE.bat        ← NHẤP ĐÚP ĐỂ CHẠY WEBSITE
├── app/
│   ├── main.py              (FastAPI app + /api/v1/health, error handler)
│   ├── core/{config,database,security,utils}.py
│   ├── models/{base,user,food,meal,ml,chat,__init__}.py
│   ├── services/nutrition.py       (công thức khẩu phần §5.3, cộng dồn, ước lượng Atwater)
│   └── repositories/food_repository.py  (tìm kiếm có dấu/không dấu, lọc, upsert)
├── migrations/{env.py,script.py.mako,versions/827db6071a8d_init_schema.py}
├── scripts/{setup_env.bat,init_db.bat,seed_reference_data.py,backup_db.py}
├── tests/unit/{test_nutrition.py,test_food_repository.py}   (40 bài kiểm thử)
└── docs/{ENVIRONMENT_REPORT.md,TECHNICAL_DECISIONS.md,PROJECT_PROGRESS.md}
```

## 8. Quyết định kỹ thuật trong giai đoạn này

Xem `docs/TECHNICAL_DECISIONS.md`: TD-01 (modular monolith), TD-02 (Python 3.12), TD-03 (torch CPU), TD-04 (nguồn chuẩn dinh dưỡng), TD-05 (thiếu = NULL), TD-06 (snapshot bữa ăn), TD-07 (cookie phiên + Argon2id), TD-08 (UTC), TD-09 (FK + WAL), TD-10 (alembic ASCII), TD-11 (Qwen tắt thinking), TD-12 (Codex CLI GPT-5.6-Sol), TD-13 (chính sách ảnh), TD-14 (tách nguồn dữ liệu).

## 9. Bước tiếp theo

1. Chờ 5 luồng đang chạy: 3 importer (USDA, Open Food Facts, bảng Việt Nam + kiểm tra chất lượng dữ liệu), pipeline hồi quy calo, và chuẩn bị dataset ảnh.
2. **Kiểm tra lại bằng chứng** của từng luồng (đếm dòng thật, sha256, giấy phép) trước khi tin.
3. Chạy tuần tự 3 importer trên DB thật (không chạy song song để tránh tranh chấp ghi SQLite), rồi chạy `scripts/check_data_quality.py` và ghi `docs/DATA_SOURCES.md`.
4. Huấn luyện thật: `training/image/train.py` trên dataset ảnh đã chuẩn bị, ghi kết quả vào `data/reports/image_experiment.md`; kiểm tra `models/regression/latest.json` có khớp hợp đồng mà `app/ml/regression_model.py` đọc hay không.
5. Giai đoạn 4: 9 trang giao diện tiếng Việt (Chart.js cho dashboard/thống kê).
6. Giai đoạn 5: tích hợp Qwen với `think=false`, ngữ cảnh do backend dựng, và kiểm tra trường hợp Ollama không chạy.
7. Giai đoạn 6: kiểm thử toàn hệ thống, README, báo cáo thực nghiệm.

## 10. Buổi kiểm thử toàn website (19/11/2026)

Trạng thái: **website đã đủ 9 trang, mọi chức năng chính đã kiểm thử trên hệ thống đang chạy.**
Chi tiết kèm ảnh chụp từng trang: `BAO_CAO_KIEM_THU.md` (ảnh trong `data/reports/figures/`).

### Đã hoàn thành 2 trang còn thiếu — tự làm trong phiên, không qua subagent
Batch 5 luồng dựng giao diện đã tạo được 7 trang, nhưng luồng phụ trách `statistics` **thất bại vì
`HTTP 429 – hết hạn mức ChatGPT/Codex`** (hạn mức reset 07:49), và trang `profile` cũng không
được tạo. Lần giao lại 2 luồng mới cũng chết sau 8–9 giây vì đúng lỗi hạn mức đó. Do đó tôi tự
viết 2 trang này trong phiên:
- `app/templates/statistics.html` (28 KB): 3 chế độ Ngày/Tuần/Tháng, điều hướng kỳ trước/sau,
  biểu đồ theo từng chế độ, bảng số liệu, và **ngày thiếu dữ liệu là khoảng trống chứ không vẽ 0**.
- `app/templates/profile.html` (17 KB): thông tin tài khoản (quy đổi UTC → giờ Việt Nam), sửa hồ sơ
  và **đọc lại từ máy chủ để xác nhận đã lưu**, đổi mật khẩu, vùng xoá tài khoản có bắt gõ `DELETE`.

### Kết quả kiểm thử (số liệu thật)
| Hạng mục | Lệnh | Kết quả |
|---|---|---|
| Bộ kiểm thử đơn vị + tích hợp | `.venv\Scripts\python.exe -m pytest` | ✅ **168 passed, 1 skipped** in 53,73 s (bài bỏ qua là bài gọi Qwen thật, cần `ANA_LIVE_OLLAMA=1`) |
| Kiểm thử chức năng toàn hệ thống | `.venv\Scripts\python.exe scripts\e2e_web_test.py` | ✅ **92 đạt / 0 hỏng / 0 ghi nhận** (báo cáo: `data/reports/e2e_web_test.md`) |
| Kiểm thử 9 tuyến trang | `pytest tests/integration/test_pages.py` | ✅ 21 passed |
| Trình duyệt thật | 9 trang + khổ điện thoại 390 px | ✅ không lỗi JS; biểu đồ vẽ thật, số liệu khớp API |

### Lỗi thật phát hiện và sửa trong buổi kiểm thử
| # | Lỗi | Cách sửa |
|---|---|---|
| 14 | Trang nhận diện trả `suggested_foods` rỗng vì chưa thực phẩm nào gắn nhãn ảnh | Thêm bước tìm theo tên nhãn (`pho_bo` → `pho bo`) khi chưa có bản ghi gắn nhãn |
| 15 | **Ước lượng calo bằng model luôn báo thiếu feature**: danh sách dự phòng dùng `moisture_g` trong khi model huấn luyện với `water_g` | Sửa danh sách theo đúng tên model + thêm bảng tên thay thế (`moisture_g` ↔ `water_g`) cho cả 2 đường gọi API. Sau khi sửa: ước lượng thật ra **123,8 kcal** |
| 16 | Tra cứu xếp hạng kém: 759 bản ghi không tên và tên tiếng Bulgaria/Thái chiếm trang đầu | Xếp hạng 3 mức: có tên → tên đọc được → không có tên; ưu tiên bản ghi có số liệu năng lượng |
| 17 | Tìm 2 ký tự ("gà") trả về bản ghi khớp giữa từ ("Grow & gain") | Thêm xếp hạng độ liên quan: khớp đúng tên > khớp đầu tên > khớp đầu từ > khớp giữa > khớp nhờ tên phụ |
| 18 | Cột Danh mục bị cắt không tooltip, nhãn "Chế biến sẵn" xuống 3 dòng | Thêm `nowrap` cho nhãn, giới hạn 260 px + `title` cho cột danh mục |
| 19 | `GET /predict/models` và `GET /assistant/status` **không cần đăng nhập** (lộ cấu hình Ollama, thông số model) | Bắt buộc đăng nhập; đã xác minh trả 401 khi chưa đăng nhập |
| 20 | Ghi bữa ăn với `food_id` không tồn tại trả 400, không thống nhất với các endpoint khác | Trả **404** kèm thông báo tiếng Việt |
| 21 | `/favicon.ico` trả 404 | Thêm tuyến trả chính tệp SVG |
| 22 | 3 bài kiểm thử cũ phụ thuộc trạng thái máy (đang có model thì đổi hành vi) | Chuyển thành tự lập: ép trạng thái "chưa có model" bằng thư mục rỗng |
| 23 | Trợ lý AI tự mâu thuẫn ("1105 kcal cao hơn mục tiêu 2000" + "ăn quá nhiều… còn thiếu 895 kcal") và nhắc món không có trong câu hỏi | Thêm 5 quy tắc vào prompt hệ thống (tự tính trước khi so sánh, đúng chiều; chỉ nhắc thực phẩm trong dữ liệu; không dùng từ đánh giá; từ chối kết luận với câu hỏi đánh giá). Kiểm chứng lại bằng đúng 2 câu hỏi cũ: cả hai trả lời đúng |

### Hạn chế còn lại (không giấu)
- **Dữ liệu chưa có tên món Việt**: `name_vi` = 0 bản ghi; tên thực phẩm là tiếng Anh/ngôn ngữ khác
  (một số ít sản phẩm đóng gói có tên tiếng Việt nằm trong trường `name_en`, ví dụ "Sữa Fami Canxi").
  Vì vậy tra cứu "gà" ra sản phẩm nước ngoài chứ không ra món gà Việt. Cách xử lý đã chuẩn bị sẵn:
  điền `data/external/vn_fct_template.csv` rồi chạy `scripts/import_vn_fct.py`.
- **Lớp `pho_bo` nhận diện sai** (F1 0,5 vì chỉ có 46 ảnh); các lớp 100 ảnh đạt 0,73–0,95.
- **Model hồi quy là bản huấn luyện trên dữ liệu hiện có**; chỉ dùng khi thực phẩm thiếu số đo và
  API luôn nói rõ giá trị là ước lượng.
- **GPT-5.6-Sol qua Codex CLI và subagent không dùng được đến ~07:49** do hạn mức ChatGPT/Codex
  đã cạn (HTTP 429), nên 2 trang cuối do tôi tự viết.

---

## 26/11/2026 — vòng nâng cấp nhận diện ảnh: 15 → 24 lớp

| Lần chạy | Lớp | Món Việt | Ảnh | Accuracy test | Macro F1 |
|---|---:|---:|---:|---:|---:|
| 19/11/2026 (bản cũ) | 15 | 7 | 1.208 (847/181/180) | 0,7889 | 0,763 |
| 26/11/2026 v2 | 29 | 21 | 1.711 (1.198/260/253) | 0,6640 | 0,7217 |
| 26/11/2026 v3 (**đang dùng**) | 24 | 16 | 1.577 (1.103/240/234) | 0,7521 | 0,7619 |

- Nhiễu dữ liệu: cổng lọc ảnh cũ nhận ảnh sai vì tìm kiếm Commons khớp chuỗi con; lớp `xoi` có
  **0/31 ảnh đúng**. Cổng lọc mới yêu cầu khớp **từ trọn vẹn** hoặc đúng danh mục món → loại 1.304 ảnh rác;
  soi mắt loại thêm 21 ảnh (`goi_cuon` 11, `banh_xeo` 10) và 8 ảnh sai của `xoi`.
- 5 lớp đạt F1 = 0 khi huấn luyện 29 lớp → loại khỏi lần huấn luyện đang dùng; manifest đầy đủ vẫn giữ.
- Model đang chạy: `models/image/best.pt` (24 lớp); bản 15 lớp giữ ở `models/image_v15_backup/`;
  manifest v3: `data/processed/image_dataset_manifest_v3.csv`.
- `app/ml/labels_vi.py`: tên hiển thị tiếng Việt cho 29 nhãn + từ khoá tra cứu món, nối vào
  `app/api/v1/predict.py` và `app/templates/recognize.html`.
- Kiểm chứng: 10 ảnh món Việt thuộc tập test → top-1 **7/10**, top-3 **9/10**; e2e **92/0**; pytest **168/1**.
- Số liệu CSDL sau đợt nhập Open Food Facts Việt Nam: **102.847 thực phẩm · 364.611 food_nutrients ·
  98.721 alias · 69.198 thiếu năng lượng**; không sửa giá trị dinh dưỡng nào (đối chiếu bản sao lưu).
- Tối ưu tra cứu gợi ý (`has_match` + `with_total=False` + bỏ từ khoá trùng): `POST /predict/image`
  từ **630–1.040 ms xuống 297–370 ms** (suy luận model chỉ ~20 ms — nút cổ chai là tra cứu SQL trên
  102.847 thực phẩm). Chi tiết và số đo ở `BAO_CAO_KIEM_THU.md` §7.2.
---

## 27/11/2026 — FTS5 cho tra cứu + kiểm toán dữ liệu ảnh

**Tra cứu toàn văn FTS5** (migration `9b1c2d3e4f5a`; `app/core/food_search.py`):

- Bảng ảo `food_search` (`unicode61 remove_diacritics 2`) + 6 trigger đồng bộ + view
  `food_search_documents`; nạp sẵn 102.847 dòng; truy vấn thoát an toàn; tự hạ cấp về `LIKE`
  nếu CSDL chưa migrate.
- Đo qua HTTP: `POST /predict/image` **297–370 ms → 64–68 ms**; `/foods` **8–114 ms**
  (truy vấn khớp nhiều nhất "ga" 4.166 kết quả = 114 ms).
- `pytest` **175 bài / 0 hỏng / 1 bỏ qua**; e2e **92/0**.
- Chi phí thật: chỉ mục chiếm **66,3 MB** → CSDL 68,8 MB lên 135,1 MB (bỏ cột `suffix_norm` sẽ
  tiết kiệm ~60 MB nhưng mất kiểu khớp giữa từ).

**Kiểm toán dữ liệu ảnh** (thu thêm 89 ảnh Commons có giấy phép tự do cho 9 lớp mỏng):

- Phát hiện đúng: lớp `canh_chua` gần như toàn ảnh rác — soi lại 20/20 ảnh bị loại là
  vườn/chùa/cây cảnh; F1 = 1,0000 trước đây của lớp này là vô nghĩa.
- Phát hiện sai của luồng thu thập: lớp `banh_khot` bị loại oan (soi 20 ảnh bị loại: 17/20 đúng là
  bánh khọt) → đã khôi phục 14 ảnh.
- Manifest dựng lại: **1.665 dòng / 29 lớp / 0 đường dẫn chết** (trước: 1.711 dòng, 100 đường dẫn
  trỏ vào ảnh đã chuyển sang `_rejected`).
- Bảy lớp dưới ngưỡng 34 ảnh sạch bị loại khỏi huấn luyện; manifest huấn luyện:
  `data/processed/image_dataset_manifest_v4.csv` (22 lớp / 1.579 ảnh).
---

## 27/11/2026 (tiếp) — chọn model v5, sửa lỗi FTS5, thử GPU

**Model đang phục vụ: v5 — 22 lớp (14 món Việt + 8 lớp Food-101), 1.579 ảnh (1.105/240/234).**
Accuracy test **0,7137**, macro F1 **0,7062**; trên đúng tập test của 20 lớp chung với model cũ:
0,7207 so với 0,7511 của v3. So sánh đầy đủ:

| Lần chạy | Lớp | Accuracy test (20 lớp chung) | F1 có trọng số | Accuracy toàn bộ |
|---|---:|---:|---:|---:|
| v3 | 24 | 0,7511 | 0,7445 | 0,7521 |
| v4 | 22 | 0,6802 | 0,6698 | 0,6624 |
| **v5 (đang dùng)** | 22 | 0,7207 | 0,7197 | 0,7137 |

Chọn v5 dù v3 nhỉnh hơn về số, vì v3 có 4 lớp huấn luyện trên dữ liệu rác (lớp `canh_chua` 23/28 ảnh
là vườn/chùa) nên chỉ số các lớp đó vô nghĩa; v5 còn có thêm `banh_cuon` và `xoi`. Model v3 giữ ở
`models/image_v3/`. Kiểm chứng: 12 ảnh món Việt thuộc tập test → top-1 8/12, top-3 11/12.

**Sửa lỗi do chỉ mục FTS5 gây ra:** truy vấn AND rời từng từ + cột hậu tố làm gợi ý món khớp bậy
(`nem_ran` → "Medite**rran**e Creme"). Đã thêm `match_mode`: **phrase** cho gợi ý món theo nhãn
(đúng như `LIKE '%a b%'` trước đây), **and** cho ô tra cứu người dùng. Sau khi sửa: `nem_ran` →
"Spring Roll Rice Paper", `hu_tieu` → "Hủ Tiếu Nam Vang"; gợi ý mất 1–38 ms (trước 425–1.535 ms).

**GPU:** thử trong venv riêng `.venv-gpu` với `torch==2.5.1+cu121` → `torch.cuda.is_available() = True`
và `get_arch_list()` **có sm_61**, nên Quadro P2000 dùng được; huấn luyện **26–30 s/epoch** so với
**50–75 s/epoch** trên CPU (nhanh hơn ~2–2,5 lần). Ứng dụng vẫn chạy `.venv` CPU (2.15.0+cpu) —
suy luận 1 ảnh chỉ ~20 ms nên GPU không cần cho lúc chạy.
- **Chuyển sang CUDA (27/11/2026):** `.venv` nay dùng `torch 2.5.1+cu121` + `torchvision 0.20.1+cu121`
  (cài bằng `uv` vì venv không có pip; bản cu121 là kênh cuối còn hỗ trợ Pascal sm_61). Kiểm chứng:
  `cuda.is_available() = True`, `get_arch_list()` có sm_61, forward 4 ảnh GPU 8 ms, pytest **175/0/1**,
  e2e **92/0**, nhận diện món Việt không đổi (top-1 8/12). Ứng dụng vẫn suy luận trên CPU
  (`map_location="cpu"`) nên hành vi web không đổi. Sự cố khi cài: uv bị chặn xoá `PIL/_imaging*.pyd`
  đang bị giữ → mất PIL + sympy; đã chép lại PIL 13.0.0 từ `.venv-gpu` và cài bù gói phụ thuộc.

## 7.8. Vòng hoàn thiện ngày 28/11/2026: model 25 lớp, bỏ cột hậu tố FTS5, lớp kiểm chứng số liệu

### Model nhận diện ảnh
- Tập dữ liệu sau khi khôi phục ảnh Openverse: **1.784 ảnh / 29 lớp** (865 Wikimedia Commons +
  119 Openverse + 800 Food-101), chia 1.181 / 257 / 250.
- Lần chạy đang dùng **v8: 25 lớp** (17 món Việt + 8 lớp Food-101), **1.688 ảnh**, huấn luyện
  trên GPU (Quadro P2000) với **`CrossEntropyLoss(weight=balanced)`** để chống lệch lớp
  (lớp món Việt 24–27 ảnh train so với 70 ảnh của lớp Food-101).
- Kết quả test **0,7000 · macro F1 0,6629**; trên 234 ảnh test của 22 lớp chung đạt **168/234 =
  0,7179** (v5 0,7137 · v6 0,6923 · v7 0,6795) nên v8 được chọn làm bản phục vụ; bản cũ giữ ở
  `models/image_v5/`. Kiểm chứng HTTP thật: top-1 14/24, top-3 21/24.
- Ba lớp mới `bun_rieu`, `bun_thit_nuong`, `pho_ga` đã vào model; nhóm món nước còn nhầm lẫn
  nhau và cần thêm 30–50 ảnh thật mỗi món.
- `training/image/train.py` có thêm cờ `--class-weights balanced` (và `--device cuda`).

### Tra cứu (FTS5)
- Bỏ hẳn cột `suffix_norm` (mọi hậu tố của mọi từ) khỏi bảng ảo: cột này gây kết quả rác
  ("nem rán" → "Mediterrane Creme") và chiếm 66,3 MB. Migration `c4a7b1e9d2f3`.
- Truy vấn dùng khớp tiền tố theo từng từ, chỉ trên `name_norm`/`alias_norm`.
- CSDL **135,1 MB → 82,0 MB** (−53,1 MB), `integrity_check = ok`, 102.847 dòng đồng bộ.

### Trợ lý AI
- Thêm lớp kiểm chứng số liệu: `context_numbers`, `verify_numbers`, `official_numbers_text`;
  sai số thì hỏi lại model một lần, vẫn sai thì gắn số liệu chính thức lấy từ dữ liệu.
- API trả thêm `numbers_verified`, `numbers_checked`, `unsupported_numbers`, `retried`.
- Bỏ từ dừng/từ ngắn khi dò món trong câu hỏi (trước đây "ăn" → "and" nên nhắc "Beef and
  vegetables").

### Kiểm thử
- pytest **193 đạt / 1 bỏ qua / 0 hỏng**; e2e web **92 đạt / 0 hỏng** (chạy lại sau mỗi lần đổi
  model, đổi chỉ mục và sau khi thêm lớp kiểm chứng).
- Lượt kiểm thử lái trình duyệt thật: đăng nhập, `/recognize` (Top-3), `/foods`, `/assistant`.
- Dữ liệu kiểm thử đã dọn: 102.847 thực phẩm, 364.611 giá trị dinh dưỡng, 2 tài khoản thật.

## 7.9. Vòng 28/11/2026 (tiếp): 20 món Việt, model v10 44 lớp, đề xuất thực đơn, khẩu phần

- **Đề xuất thực đơn theo chỉ số cơ thể** (`app/services/nutrition_needs.py`, `plan_service.py`,
  `app/api/v1/plan.py`): BMR Mifflin–St Jeor + TDEE theo mức vận động + điều chỉnh theo mục tiêu cân
  nặng + ngưỡng an toàn; thực đơn chỉ cho **các bữa chưa ghi**, chia kcal 25/35/30/10, chọn nguyên
  liệu thật trong CSDL theo ngân sách từng bữa, co khẩu phần khi vượt 8 %; **ghi chú trong hồ sơ
  thành điều kiện lọc** (dị ứng/kiêng/chay/thuần chay/tăng cơ) và trả về `constraints.applied`.
  Kiểm chứng thật: BMR 1573 · TDEE 2162 · mục tiêu 2200 · đã ăn 540 · còn 1660; bữa đã ghi không bị
  đề xuất lại. 17 bài test mới cho phần này.
- **Khẩu phần và dinh dưỡng khi nhận diện ảnh** (`app/ml/portion_table.py` + khối `portion` trong
  `/predict/image`): khẩu phần tham khảo theo món × giá trị trong CSDL, có `nutrient_source` và
  `missing_nutrients`; loại nước sốt/gia vị khi chọn món khớp (lỗi thật đã gặp: nhãn `salad` khớp
  "Salad dressing" 884 kcal/100 g).
- **Đo model thị giác 0,8B**: có `vision` nhưng chỉ đúng **6/40 = 15 %** tên món Việt và không ước
  lượng được khối lượng ⇒ vẫn dùng CNN tự huấn luyện, khối lượng dùng bảng khẩu phần.
- **Tên món tiếng Việt**: pizza/hamburger/sushi/salad/steak nay hiển thị kèm tên Việt; khai báo thêm
  16 lớp mới trong `app/ml/labels_vi.py`.
- **20 món Việt mới về dữ liệu**: 5 luồng thu song song (mỗi món ≥40 ảnh tải về), 8 luồng soi độc lập
  bằng mắt; đĩa hiện có **4.149 ảnh nhận / 45 lớp**, 2.388 ảnh bị loại; đã loại 30 ảnh sai ở vòng này
  và **loại lớp `bun_mam` khỏi huấn luyện** (mẫu soi chỉ 6/15 ảnh đúng món).
- **Huấn luyện lại**: tập dùng **2.524 ảnh / 44 lớp** (train 1.768 · val 383 · test 373); v9
  (0,7024/0,6745) rồi **v10 = 60 epoch + RandomErasing + label smoothing → accuracy test
  0.7185 · macro F1 0.6917** (2.228,3 s, GPU).
- **Chọn bản phục vụ bằng so sánh công bằng** trên 134 ảnh test ở cả hai manifest:
  v8 0.7164 vs **v10 0.7463** ⇒ dùng **v10 (44 lớp)**.
- **Kiểm chứng qua HTTP thật**: top-1 0.7500 ·
  top-3 0.8068 trên 88 ảnh test, 92 ms/ảnh.
- **Kiểm thử**: pytest **217 đạt / 1 bỏ qua**; e2e **92 đạt / 0 hỏng**.
