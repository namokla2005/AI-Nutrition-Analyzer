# BÁO CÁO MÔI TRƯỜNG PHÁT TRIỂN (GIAI ĐOẠN 0)

**Dự án:** AI Nutrition Analyzer – Hệ thống nhận diện thực phẩm, dự đoán calo và phân tích dinh dưỡng bằng Machine Learning
**Thư mục dự án:** `D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer`
**Thời điểm khảo sát:** 2026-11-19 02:55–03:10 (UTC+07:00)
**Nguyên tắc:** mọi số liệu dưới đây lấy từ lệnh thực tế đã chạy, không ước lượng.

---

## 1. Workspace

| Nội dung | Kết quả thực tế |
|---|---|
| Thư mục `D:\Documents\BaoCao\TriTueNhanTao\` trước khi bắt đầu | Chỉ có 2 file: `Xây dựng hệ thống dự đoán lượng calo ... .txt` (23.700 B) và `Baocao_2023.docx` (23.573 B). **Không có dự án cũ nào bị ghi đè.** |
| Dự án mới tạo | `D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer\` (thư mục mới, không trùng) |
| Cấu trúc đã tạo | `app/{core,api/v1,models,schemas,services,repositories,ml,integrations,templates,static}`, `training/{image,regression}`, `data/{raw,processed,external,reports}`, `models/{image,regression}`, `uploads`, `migrations/versions`, `tests/{unit,integration,ml}`, `docs`, `scripts` |

## 2. Phần cứng (đo trực tiếp)

| Thành phần | Giá trị thực tế |
|---|---|
| CPU | Intel Core i5-8400H @ 2.50 GHz, 4 nhân / 8 luồng |
| RAM | 15,73 GB khả dụng (đo bằng `Win32_ComputerSystem.TotalPhysicalMemory`) |
| GPU | NVIDIA Quadro P2000, VRAM 4096 MiB, driver 572.76, CUDA runtime 12.8 |
| VRAM đang dùng lúc khảo sát | 713 MiB / 4096 MiB (Ollama + desktop) |
| Ổ C: | 238 GB, còn trống 91 GB |
| Ổ D: | 477 GB, còn trống 189 GB |

**Kết luận phần cứng:** đủ chỗ cho dự án (dự kiến < 15 GB gồm dataset ảnh và model). VRAM 4 GB lại đang chia sẻ với Ollama nên **không nên đặt cược vào GPU** cho huấn luyện.

## 3. Python và môi trường ảo

| Kiểm tra | Kết quả |
|---|---|
| Python mặc định của launcher (`py -0p`) | 3.12.8 (đường dẫn `C:\Users\Nam\AppData\Local\Programs\Python\Python312\python.exe`) |
| Python do uv cung cấp | 3.13.15 (`Astral/CPython3.13.15`), 3.10.21 (`Astral/CPython3.10.21`) |
| `python` trên PATH của shell | 3.14.9 (bản Hermes dùng nội bộ – **không dùng cho dự án**) |
| uv | 0.12.11 |
| Python 3.13 bản hệ thống | Không tồn tại (không có `Python313\python.exe`) |

**Quyết định:** dùng **Python 3.12.8** cho `.venv` của dự án (không đổi Python hệ thống, đúng yêu cầu §2). Lý do: đây là bản đã kiểm chứng cài được `torch`/`torchvision`/`scikit-learn` trên máy này.

### Thư viện **đã cài thực tế** trong `.venv` (kiểm tra bằng `pip list`)

```
fastapi        0.165.0      torch        2.15.0+cpu
uvicorn        0.54.0       torchvision  0.29.2+cpu
SQLAlchemy     2.1.9        scikit-learn 1.9.1
alembic        1.20.1       pandas       3.1.1
argon2-cffi    25.1.0       pillow, numpy, joblib, matplotlib, jinja2, httpx,
pydantic       2.x          python-multipart, aiofiles, itsdangerous,
                            email-validator, pytest, pytest-asyncio
```

Số gói trong `.venv\Lib\site-packages`: **155**.

## 4. GPU / CUDA – vấn đề tương thích đã xác định

- Bản `torch` cài sẵn trên Python hệ thống là `2.14.0+cpu`, **`torch.cuda.is_available()` trả về `False`** (khảo sát trực tiếp).
- Quadro P2000 là kiến trúc **Pascal, compute capability 6.1 (sm_61)**. Các bản PyTorch CUDA mới không còn build cho sm_61, nên GPU này không phải lựa chọn ổn định cho huấn luyện.
- Trong `.venv` đã cài **PyTorch bản CPU** (`2.15.0+cpu`, `torchvision 0.29.2+cpu`) từ `https://download.pytorch.org/whl/cpu`.
- **Không** cài CUDA toolkit, **không** sửa driver, **không** thay đổi cấu hình GPU (đúng yêu cầu §2.8).
- Phương án CPU là bắt buộc theo §2.7 và hoàn toàn khả thi: MobileNetV3-Small chỉ ~2,5 triệu tham số; thời gian huấn luyện thực tế sẽ được đo và ghi lại ở Giai đoạn 2.

## 5. Ollama và Qwen

| Kiểm tra | Kết quả thực tế |
|---|---|
| `ollama --version` | 0.40.16 |
| Model | `qwen3.5:0.8b` (ID `de63045f2975`, 1.322.069.277 B, Q8_0) |
| Chi tiết model | 752,39M tham số, context 262.144, `capabilities: ["completion","vision","tools","thinking"]` |
| API `/api/tags` | HTTP 200, trả về đúng model trên |
| API `/api/chat` (thử thật) | **Chạy được nhưng có vấn đề quan trọng:** với `num_predict=60`, trường `content` **rỗng**, toàn bộ 60 token bị tiêu vào trường `thinking`, `done_reason="length"` |

**Phát hiện quan trọng:** `qwen3.5:0.8b` là **model "thinking"**. Nếu không tắt chế độ suy luận, câu trả lời sẽ rỗng vì model đốt hết token vào phần suy nghĩ nội bộ.
→ Đã đưa vào cấu hình: `OLLAMA_THINK=false` và `OLLAMA_NUM_PREDICT=400` (xem `app/core/config.py`). Tầng tích hợp sẽ phải xử lý cả trường `thinking` để không hiển thị phần suy luận nội bộ cho người dùng.

**Đo độ trễ lần chạy đầu (model chưa nạp):** tổng 23,6 s, trong đó 21,1 s là thời gian nạp model; phần sinh chỉ 2,15 s cho 60 token.

**Ghi chú chất lượng:** với câu hỏi tiếng Việt ngắn, model 0,8B đã hiểu sai ("tra loi ngan" bị hiểu thành tên sản phẩm). Vì vậy Assistant service phải: cấp ngữ cảnh dinh dưỡng **do backend lấy từ DB** và yêu cầu model chỉ trả lời dựa trên ngữ cảnh đó (đúng yêu cầu §8.6, §9).

## 6. Truy cập Internet và nguồn dữ liệu

| Nguồn | Kiểm tra thực tế | Kết luận |
|---|---|---|
| USDA FoodData Central | `fdc.nal.usda.gov` HTTP 200 | Dùng được |
| USDA – tải nguyên bộ dữ liệu bulk | 3 file CSV nén **đã xác nhận** HTTP 200 + kích thước: SR Legacy 2018-04 (6.074.592 B), Foundation Foods 2024-10-31 (3.258.886 B), Survey/FNDDS 2022-10-28 (4.427.502 B) | Tải trực tiếp, **không cần API key** |
| Open Food Facts | `world.openfoodfacts.org` HTTP 200; API v2 search trả JSON thật | Dùng được; dump CSV 1.540.715.029 B (sau redirect 302 → S3) |
| Hugging Face (Food-101) | `huggingface.co/datasets/ethz/food101` HTTP 200 | Dùng cho dataset ảnh |
| Food-101 bản cũ của ETHZ | `data.vision.ee.ethz.ch/.../food-101.tar.gz` **HTTP 404** | Liên kết cũ đã chết → phải dùng đường HF |
| PyPI | HTTP 200 | Cài gói được |

## 7. Công cụ hỗ trợ GPT (theo yêu cầu người dùng)

| Kiểm tra | Kết quả thực tế |
|---|---|
| Ứng dụng ChatGPT (MSIX `OpenAI.Codex` 26.1111.2228.0) | Có, tại `C:\Program Files\WindowsApps\OpenAI.Codex_26.1111.2228.0_x64__2p2nqsd0c76g0\app\ChatGPT.exe` |
| **Codex CLI đi kèm** | `C:\Users\Nam\AppData\Local\OpenAI\Codex\bin\c38161ad8494f88c\codex.exe` – phiên bản `0.169.0-alpha.11.1` |
| Đăng nhập | `codex login status` → **"Logged in using ChatGPT"** (dùng gói ChatGPT, không cần API key trả phí) |
| Cấu hình model | `C:\Users\Nam\.codex\config.toml`: `model = "gpt-5.6-sol"`, `model_reasoning_effort = "high"` — **đúng model người dùng yêu cầu** |
| Thử thật `codex exec` | Chạy thành công, trả về đúng chuỗi yêu cầu, dùng 3.003 token, `sandbox: read-only`, `reasoning effort: high` |
| Model khác khả dụng | `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-5.6-terra`, `codex-auto-review` |

**Kết luận:** không cần điều khiển ứng dụng ChatGPT bằng chuột/bàn phím (vừa chậm vừa chiếm màn hình). Codex CLI cho phép gọi **GPT-5.6-Sol reasoning High** bằng dòng lệnh, chạy nền song song, cùng tài khoản ChatGPT của người dùng.

## 8. Vấn đề tương thích đã phát hiện và đã xử lý

| # | Vấn đề | Trạng thái |
|---|---|---|
| 1 | `alembic.ini` chứa chữ tiếng Việt → `configparser` đọc bằng cp1252 → `UnicodeDecodeError`, migration không chạy | **Đã sửa**: file cấu hình Alembic giữ thuần ASCII, có ghi chú lý do |
| 2 | `torch` bản CUDA không dùng được với GPU Pascal sm_61 | Đã chuyển sang bản CPU, có phương án CPU chính thức |
| 3 | `pip install torch` mặc định trên Windows kéo bản CUDA ~2,5 GB không cần thiết | Cài từ index CPU của PyTorch |
| 4 | `qwen3.5:0.8b` là model thinking → câu trả lời rỗng khi hết token | Đã đưa `think=false` + số token sinh vào cấu hình |
| 5 | git-bash (MSYS) không có `unzip` | Dùng `zipfile` của Python 3.12 để giải nén dữ liệu |
| 6 | `python` trên PATH là 3.14.9 (bản nội bộ Hermes), không có `torch`/`sklearn` | Mọi lệnh của dự án dùng đường dẫn tuyệt đối `.venv\Scripts\python.exe` |
| 7 | Liên kết tải Food-101 cũ của ETHZ đã 404 | Chuyển sang nguồn Hugging Face (đang xác minh chi tiết) |

## 9. Dung lượng lưu trữ dự kiến

| Hạng mục | Ước tính có căn cứ |
|---|---|
| `.venv` (đã cài thực tế, 155 gói, gồm torch CPU) | ~1,5 GB |
| Dữ liệu USDA (3 file CSV bulk đã xác nhận kích thước) | ~14 MB nén, ~120 MB sau giải nén |
| Open Food Facts (bản trích lọc có giới hạn ~20.000 dòng) | < 30 MB (file gốc 1,54 GB không lưu lại) |
| Dataset ảnh Food-101 (chỉ các lớp cần thiết, nếu tải từng phần) | 1–6 GB tùy số lớp |
| Ảnh Wikimedia Commons cho món Việt (tối đa vài trăm ảnh/lớp) | ~0,5–2 GB |
| Model đã huấn luyện (MobileNetV3-Small ~10 MB + 3 model hồi quy joblib) | < 50 MB |
| **Tổng** | **khoảng 3–10 GB** — thoải mái với 189 GB trống trên ổ D: |

## 10. Kế hoạch triển khai Giai đoạn 1

1. Thiết kế 14 bảng SQLAlchemy + khóa ngoại + index (✅ **đã xong**).
2. Alembic: revision đầu tiên `827db6071a8d_init_schema` (✅ **đã chạy**, 15 bảng, 31 index).
3. Seed danh mục 15 chất dinh dưỡng + 6 nguồn dữ liệu (✅ **đã chạy**, idempotent).
4. Ba luồng thu thập dữ liệu chạy song song bằng subagent:
   - USDA FoodData Central (3 bộ CSV bulk) → `data/external/usda/`
   - Open Food Facts (trích lọc có giới hạn) → `data/external/openfoodfacts/`
   - Nguồn bảng thành phần dinh dưỡng Việt Nam + nguồn ảnh (Food-101/Hugging Face, Wikimedia Commons) → `docs/`, `data/raw/images/`
5. Viết importer CSV/JSON (`scripts/import_*.py`) + kiểm tra trùng/thiếu/sai đơn vị.
6. Viết `docs/DATA_SOURCES.md` mô tả nguồn, đơn vị, giấy phép, thời điểm nhập.
7. Kiểm thử: đếm số bản ghi theo nguồn, kiểm tra không có bản ghi trùng, kiểm tra giá trị thiếu được để trống (không điền 0).

## 11. Trạng thái khởi động website (kiểm chứng thực tế)

```
GET /api/v1/health → 200
{"app":"AI Nutrition Analyzer","version":"1.0.0",
 "database":{"ok":true,"file":"D:\\...\\data\\nutrition.db"},
 "ollama":{"base_url":"http://127.0.0.1:11434","model":"qwen3.5:0.8b","checked":false}}
GET /docs → HTTP 200
PRAGMA foreign_keys = 1     PRAGMA journal_mode = wal
```

File khởi chạy đã có: `START_WEBSITE.bat` (nhấp đúp là chạy), `run.py` (dòng lệnh), `scripts/setup_env.bat`, `scripts/init_db.bat`.
