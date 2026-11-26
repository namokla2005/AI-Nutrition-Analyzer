# AI Nutrition Analyzer

Hệ thống nhận diện thực phẩm, dự đoán calo và phân tích dinh dưỡng bằng Machine Learning.

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy + Alembic + SQLite (Argon2id cho mật khẩu)
- **Machine Learning:** PyTorch (MobileNetV3-Small, transfer learning) + scikit-learn (Linear Regression, Random Forest, Gradient Boosting)
- **Frontend:** HTML5 + CSS3 + JavaScript + Chart.js (giao diện tiếng Việt)
- **Trợ lý AI:** Ollama + Qwen3.5-0.8B qua HTTP API nội bộ (`http://127.0.0.1:11434`)

## Chạy nhanh

```
Nhấp đúp:  START_WEBSITE.bat
```

File này tự động: tạo `.venv` nếu chưa có → tạo `.env` → chạy migration + seed nếu chưa có database → kiểm tra Ollama → khởi động web server và mở trình duyệt.

### Chạy bằng dòng lệnh

```bat
.venv\Scripts\python.exe run.py                  :: chạy bình thường
.venv\Scripts\python.exe run.py --reload         :: chế độ phát triển
.venv\Scripts\python.exe run.py --port 9000 --auto-port
.venv\Scripts\python.exe run.py --no-browser
```

Địa chỉ mặc định: **http://127.0.0.1:8000** — mở `/` để xem trang trạng thái hệ thống, tài liệu API tại `/docs`.
(Đổi cổng: sửa `PORT` trong `.env`, hoặc chạy `run.py --port 9000`.)

### Các lệnh thiết lập riêng

| Việc cần làm | Lệnh |
|---|---|
| Tạo môi trường ảo + cài thư viện | `scripts\setup_env.bat` |
| Khởi tạo database (migration + seed) | `scripts\init_db.bat` |
| Chỉ chạy migration | `.venv\Scripts\python.exe -m alembic upgrade head` |
| Nạp danh mục chất dinh dưỡng/nguồn dữ liệu | `.venv\Scripts\python.exe scripts\seed_reference_data.py` |

## Yêu cầu hệ thống

- Windows, Python 3.12 (đường dẫn cấu hình trong `scripts\setup_env.bat`), `uv`
- RAM ≥ 8 GB (khuyến nghị 16 GB)
- Ổ đĩa trống ≥ 10 GB (dataset ảnh chiếm phần lớn)
- Ollama (không bắt buộc — chỉ cần cho trợ lý AI): `ollama pull qwen3.5:0.8b`

## Cấu trúc thư mục

```
app/            mã nguồn backend (api, core, models, schemas, services, repositories, ml, integrations)
app/templates/  giao diện HTML (tiếng Việt)
app/static/     CSS/JS, Chart.js
training/       mã huấn luyện (image/, regression/)
data/           raw/ processed/ external/ reports/ (+ nutrition.db)
models/         model đã huấn luyện (image/, regression/)
migrations/     Alembic
scripts/        script thiết lập, import dữ liệu, kiểm tra chất lượng
tests/          unit/ integration/ ml/
docs/           báo cáo môi trường, quyết định kỹ thuật, tiến độ, nguồn dữ liệu
run.py          điểm khởi chạy website
START_WEBSITE.bat  khởi chạy một chạm
```

## Tài liệu

| File | Nội dung |
|---|---|
| `docs/ENVIRONMENT_REPORT.md` | Báo cáo khảo sát môi trường (Giai đoạn 0) |
| `docs/TECHNICAL_DECISIONS.md` | Các quyết định kiến trúc và lý do |
| `docs/PROJECT_PROGRESS.md` | Tiến độ, lỗi, kết quả kiểm thử |
| `docs/DATA_SOURCES.md` | Nguồn dữ liệu, đơn vị, giấy phép, thời điểm nhập |
| `BAO_CAO_KIEM_THU.md` | **Báo cáo kiểm thử toàn website kèm ảnh chụp từng trang** |

## Giao diện (9 trang tiếng Việt)

| Trang | Đường dẫn | Nội dung |
|---|---|---|
| Đăng nhập / Đăng ký | `/login`, `/register` | Xác thực bằng cookie phiên |
| Tổng quan | `/dashboard` | Năng lượng hôm nay so với mục tiêu, biểu đồ tròn 4/4/9, biểu đồ 7 ngày, danh sách bữa ăn |
| Nhận diện ảnh | `/recognize` | Tải ảnh → Top-3 nhãn + độ tin cậy → xác nhận món có thật trong database |
| Tra cứu thực phẩm | `/foods` | Tra 102.847 thực phẩm (có dấu/không dấu), lọc, chi tiết + khẩu phần, nhập tay |
| Nhật ký ăn uống | `/diary` | Thêm/sửa/xoá bữa ăn theo ngày (giờ Việt Nam) |
| Thống kê | `/statistics` | 3 chế độ Ngày/Tuần/Tháng, biểu đồ + bảng; ngày thiếu dữ liệu là khoảng trống |
| Trợ lý AI | `/assistant` | Hỏi đáp với Qwen3.5-0.8B, ngữ cảnh do backend dựng |
| Tài khoản | `/profile` | Thông tin, sửa hồ sơ, đổi mật khẩu, xoá tài khoản |
| Trạng thái hệ thống | `/status` | Tình trạng máy chủ, database, số bản ghi thật |

## Kiểm thử

```bat
.venv\Scripts\python.exe -m pytest                          :: 168 passed, 1 skipped
.venv\Scripts\python.exe scripts\e2e_web_test.py            :: 92/92 (CẦN máy chủ đang chạy)
set ANA_LIVE_OLLAMA=1 && .venv\Scripts\python.exe -m pytest tests\integration\test_assistant_ollama_live.py -v -s
```

`scripts\e2e_web_test.py` tự tạo tài khoản tạm, kiểm thử 92 trường hợp (gồm cả các trường hợp sai để
xác nhận hệ thống từ chối đúng), rồi tự dọn dẹp và ghi báo cáo ra `data/reports/e2e_web_test.md`.

## Lưu ý về dữ liệu và mô hình

- Dự án **không dùng dữ liệu giả lập**. Mọi số liệu dinh dưỡng đều có nguồn ghi rõ trong bảng `food_sources`.
- Giá trị dinh dưỡng không biết được lưu là **trống (NULL)**, không điền 0.
- Kết quả huấn luyện (accuracy, MAE, RMSE, R²) chỉ được công bố khi đã chạy thực tế; xem thư mục `data/reports/`.
- Trợ lý AI chỉ diễn giải dữ liệu do backend cung cấp, không tự tạo số liệu dinh dưỡng.
