# NHỮNG QUYẾT ĐỊNH KỸ THUẬT QUAN TRỌNG

Mỗi mục ghi: **quyết định – lý do – ảnh hưởng**. Chỉ ghi quyết định kiến trúc có hệ quả lâu dài.

---

## TD-01. Kiến trúc Modular Monolith (không microservices)

- **Quyết định:** một ứng dụng FastAPI duy nhất, chia lớp `api → service → repository → model`, module ML và tích hợp Ollama nằm trong cùng tiến trình.
- **Lý do:** yêu cầu §3 cho phép triển khai dạng modular monolith; máy chạy chỉ 4 nhân/16 GB, tách microservices sẽ tốn RAM vô ích và tăng độ phức tạp vận hành mà không có lợi ích kỹ thuật thực sự.
- **Ảnh hưởng:** ranh giới module phải giữ nghiêm bằng quy ước thư mục; router không được truy cập DB trực tiếp mà phải qua service/repository.

## TD-02. Python 3.12.8 cho `.venv` (không dùng 3.13/3.14)

- **Quyết định:** tạo `.venv` bằng `uv venv --python <Python312>`.
- **Lý do:** máy có 3.12.8 (bản cài hệ thống), 3.13.15 và 3.10.21 (uv), và `python` trên PATH là 3.14.9 (bản nội bộ của Hermes). 3.12.8 là bản đã kiểm chứng cài được đủ `torch`/`torchvision`/`scikit-learn`.
- **Ảnh hưởng:** mọi tài liệu và script phải dùng đường dẫn tuyệt đối `.venv\Scripts\python.exe`; không dựa vào `python` trên PATH.

## TD-03. PyTorch bản CPU; không dùng GPU cho huấn luyện

- **Quyết định:** cài `torch==2.15.0+cpu` từ `https://download.pytorch.org/whl/cpu`; mọi pipeline huấn luyện chạy CPU với `batch_size` 8–16.
- **Lý do:** Quadro P2000 là Pascal **sm_61**; các bản PyTorch CUDA mới không build cho kiến trúc này, và `torch.cuda.is_available()` trên máy trả về `False`. VRAM 4 GB lại đang chia sẻ với Ollama. Yêu cầu §2.7 bắt buộc có phương án CPU dự phòng, §2.8 cấm tùy tiện đổi driver/CUDA.
- **Ảnh hưởng:** MobileNetV3-Small được chọn đúng vì nhẹ (~2,5M tham số); thời gian huấn luyện CPU sẽ được **đo và ghi lại thật** thay vì giả định. Khi báo cáo kết quả phải ghi rõ "huấn luyện trên CPU".

## TD-04. `food_nutrients` là nguồn chuẩn, `foods.energy_kcal_per_100g` chỉ là bản sao tiện lợi

- **Quyết định:** mọi giá trị dinh dưỡng nằm ở bảng `food_nutrients` (khóa ngoại tới `nutrients`, đơn vị chuẩn hóa). Riêng năng lượng được sao chép sang `foods.energy_kcal_per_100g` (có index) để tra cứu/sắp xếp nhanh.
- **Lý do:** tra cứu thực phẩm và sắp xếp theo calo là truy vấn nóng nhất; nhưng nếu chỉ lưu ở `foods` thì không biểu diễn được các chất khác và không ghi được nguồn/độ tin cậy từng giá trị.
- **Ảnh hưởng:** trường sao chép **phải được đồng bộ trong service khi import**, và có script kiểm tra tính nhất quán. Khi lệch nhau, `food_nutrients` luôn thắng.

## TD-05. Giá trị thiếu lưu là `NULL`, tuyệt đối không lưu `0`

- **Quyết định:** `food_nutrients.amount_per_100g` cho phép `NULL`; importer bỏ trống khi nguồn không có số liệu.
- **Lý do:** yêu cầu §6 ("không tự điền giá trị dinh dưỡng chưa biết bằng 0"). Số 0 mang nghĩa "đã đo và bằng 0", hoàn toàn khác "không biết". Trộn hai khái niệm này sẽ làm hỏng cả thống kê lẫn mô hình hồi quy.
- **Ảnh hưởng:** mọi truy vấn tổng hợp phải phân biệt `NULL` và `0`; mô hình hồi quy phải loại dòng thiếu feature thay vì thay bằng 0 (trừ khi có quyết định riêng được ghi lại).

## TD-06. Snapshot dinh dưỡng trong `meal_items`

- **Quyết định:** khi ghi một bữa ăn, tính và lưu ngay kcal/protein/carb/fat/fiber/sugar/natri cho **toàn bộ khối lượng đã ăn**, kèm `nutrition_snapshot` (JSON: tên thực phẩm, nguồn, giá trị/100 g dùng để tính) và `kcal_source`.
- **Lý do:** yêu cầu §7.4. Dữ liệu thực phẩm nguồn sẽ được cập nhật về sau (nhập thêm USDA/OFF); nếu không snapshot thì lịch sử ăn uống cũ tự dưng thay đổi và báo cáo không còn tái lập được.
- **Ảnh hưởng:** `meal_items` không join sang `food_nutrients` khi hiển thị lịch sử; chỉ join `foods` để lấy tên.

## TD-07. Phiên đăng nhập bằng cookie ký (itsdangerous), không dùng JWT

- **Quyết định:** token phiên = `URLSafeTimedSerializer` chứa `uid`, đặt trong cookie `HttpOnly`; hết hạn theo `SESSION_TTL_HOURS`. Mật khẩu hash bằng **Argon2id**.
- **Lý do:** website server-rendered cùng miền, không có client di động cần token rời; cookie ký có thể thu hồi bằng cách đổi `SECRET_KEY`, đơn giản hơn JWT và ít bề mặt tấn công hơn (không lưu token trong localStorage). Argon2id là lựa chọn được khuyến nghị hiện nay (§4).
- **Ảnh hưởng:** `user_id` **luôn** lấy từ phiên phía server, không bao giờ nhận từ client (yêu cầu §7.7, §7.8). Không có bảng session nên logout = xóa cookie.

## TD-08. Thời gian lưu UTC dạng naive trong SQLite

- **Quyết định:** mọi `DateTime` lưu UTC không kèm timezone; tiện ích `utcnow()` trong `app/core/utils.py`.
- **Lý do:** SQLite không có kiểu có timezone; trộn naive/aware là nguồn lỗi kinh điển. Thống kê theo ngày/tuần/tháng sẽ quy đổi sang UTC+07:00 ở tầng service.
- **Ảnh hưởng:** mọi phép nhóm theo ngày phải nêu rõ múi giờ đang dùng; không dùng `datetime.now()` trực tiếp trong code nghiệp vụ.

## TD-09. Bật `PRAGMA foreign_keys=ON` và WAL cho mỗi kết nối

- **Quyết định:** gắn listener trên SQLAlchemy engine để chạy `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`.
- **Lý do:** SQLite mặc định **tắt** kiểm tra khóa ngoại — nếu không bật thì các ràng buộc `ON DELETE CASCADE` trong schema chỉ là trang trí. WAL cho phép đọc trong khi ghi, phù hợp web server.
- **Ảnh hưởng:** đã kiểm chứng `PRAGMA foreign_keys = 1`, `journal_mode = wal`. Script kiểm tra dữ liệu phải chạy qua engine của ứng dụng, không dùng `sqlite3.connect` trần.

## TD-10. `alembic.ini` phải thuần ASCII

- **Quyết định:** mọi ghi chú trong `alembic.ini` viết bằng tiếng Anh không dấu.
- **Lý do:** `configparser` đọc file này bằng encoding locale (cp1252 trên máy này) nên chữ tiếng Việt UTF-8 gây `UnicodeDecodeError` và làm hỏng toàn bộ migration — đã gặp lỗi thật và sửa.
- **Ảnh hưởng:** các file `.ini`/`.cfg` khác cũng phải giữ ASCII. Chữ tiếng Việt chỉ đặt trong `.py`, `.md`, `.html`, `.csv` (UTF-8).

## TD-11. Trợ lý AI dùng Ollama + Qwen3.5-0.8B với chế độ suy luận TẮT

- **Quyết định:** gọi `POST /api/chat` với `think=false` (mặc định `OLLAMA_THINK=false`), `num_predict=400`; backend luôn dựng ngữ cảnh dinh dưỡng từ service trước khi gọi model.
- **Lý do:** đo thực tế cho thấy model này là model thinking — với `num_predict=60`, `content` trả về **rỗng** vì toàn bộ token bị tiêu vào trường `thinking`. Ngoài ra model 0,8B trả lời sai khi không có dữ liệu thật cấp kèm.
- **Ảnh hưởng:** model chỉ được diễn giải/giải thích dữ liệu do backend đưa; không được tự tạo số liệu (§8.6). Khi Ollama không chạy, các chức năng nhận diện/tra cứu/tính dinh dưỡng vẫn phải hoạt động bình thường (§9).

## TD-12. Dùng Codex CLI (GPT-5.6-Sol, reasoning High) làm kênh hỗ trợ của người dùng

- **Quyết định:** gọi mô hình GPT-5.6-Sol thông qua `codex exec` của CLI đi kèm ứng dụng ChatGPT, thay vì điều khiển giao diện ứng dụng bằng chuột/bàn phím.
- **Lý do:** người dùng yêu cầu dùng "GPT 5.6 sol reasoning High". Kiểm tra thực tế: Codex CLI 0.169.0-alpha.11.1 đã đăng nhập sẵn bằng tài khoản ChatGPT, `config.toml` đã đặt đúng `model = "gpt-5.6-sol"` và `model_reasoning_effort = "high"`; `codex exec` chạy được ở chế độ không tương tác. Điều khiển GUI sẽ chiếm màn hình, chậm và dễ lỗi.
- **Ảnh hưởng:** dùng cho việc phản biện thiết kế và soát mã ở các mốc quan trọng; mọi kết quả do mô hình đề xuất vẫn phải được kiểm chứng bằng chạy thật trong dự án.

## TD-13. Ảnh người dùng có chính sách lưu trữ và kiểm tra chặt

- **Quyết định:** bảng `food_images` có `retained_until`, `sha256`, kích thước, MIME; chỉ chấp nhận JPEG/PNG/WEBP trong `MAX_UPLOAD_MB`; không cho tải file thực thi.
- **Lý do:** yêu cầu §5.1 và §13. Kiểm tra **nội dung** ảnh (Pillow xác nhận mở được) chứ không chỉ tin vào đuôi file hay header do client khai.
- **Ảnh hưởng:** cần script dọn ảnh hết hạn; tên file lưu trên đĩa là tên sinh tự động, không dùng tên người dùng tải lên.

## TD-14. Tách thông tin nguồn dữ liệu khỏi thông tin thực phẩm

- **Quyết định:** bảng `food_sources` riêng (mã, URL, giấy phép, trích dẫn, thời điểm lấy, phiên bản); mỗi `foods` trỏ tới một nguồn qua `source_id` + `source_ref` (FDC ID / mã vạch OFF) với ràng buộc duy nhất.
- **Lý do:** yêu cầu §6 và §7.5. Cùng một món có thể đến từ nhiều nguồn với số liệu khác nhau; tách ra thì mới truy vết và so sánh được.
- **Ảnh hưởng:** không nhập trùng bản ghi cùng nguồn; muốn so sánh chéo nguồn thì tạo bản ghi riêng và ghi chú rõ.
