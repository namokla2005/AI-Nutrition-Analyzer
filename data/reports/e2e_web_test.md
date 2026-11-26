# KIỂM THỬ CHỨC NĂNG TOÀN HỆ THỐNG (chạy tự động qua API thật)

- Máy chủ: `http://127.0.0.1:8000`  ·  Thời điểm chạy: 27/11/2026 00:30:08 (giờ Việt Nam)
- Kết quả: **92 đạt**, 0 hỏng, 0 ghi nhận (tổng 92 bài)
- Cách chạy lại: `.venv\Scripts\python.exe scripts\e2e_web_test.py`
- Bộ kiểm thử tự tạo 2 tài khoản tạm, tự xoá ở cuối, không đụng tài khoản thật.

| # | Nhóm | Bài kiểm thử | Mong đợi | Thực tế | Kết quả |
|---:|---|---|---|---|---|
| 1 | Hạ tầng | GET /api/v1/health | 200 | 200 | ✅ PASS |
| 2 | Hạ tầng | GET / (chuyển hướng hợp lệ khi chưa đăng nhập) | 200 hoặc chuyển hướng | 303 → /login | ✅ PASS |
| 3 | Hạ tầng | GET /login | 200 | 200 | ✅ PASS |
| 4 | Hạ tầng | GET /register | 200 | 200 | ✅ PASS |
| 5 | Hạ tầng | GET /status | 200 | 200 | ✅ PASS |
| 6 | Hạ tầng | GET /favicon.ico | 200 | 200 | ✅ PASS |
| 7 | Hạ tầng | Trang riêng tư chuyển hướng khi chưa đăng nhập | 302 tới /login | 303 → /login?next=/dashboard | ✅ PASS |
| 8 | Hạ tầng | Trang không tồn tại trả 404 | 404 | 404 | ✅ PASS |
| 9 | Xác thực | Đăng ký tài khoản A | 201 | 201 {"id":4,"email":"e2e.a.20261127002843@example.com","full_name":"Tài khoản A","is | ✅ PASS |
| 10 | Xác thực | Đăng ký tài khoản B | 201 | 201 | ✅ PASS |
| 11 | Xác thực | Đăng ký trùng email bị từ chối | 4xx | 409 | ✅ PASS |
| 12 | Xác thực | Mật khẩu dưới 8 ký tự bị từ chối | 422 | 422 | ✅ PASS |
| 13 | Xác thực | Email sai định dạng bị từ chối | 422 | 422 | ✅ PASS |
| 14 | Xác thực | Đăng nhập sai mật khẩu bị từ chối | 401 | 401 | ✅ PASS |
| 15 | Xác thực | Đăng nhập đúng | 200 | 200 | ✅ PASS |
| 16 | Xác thực | Đọc phiên hiện tại đúng tài khoản | e2e.a.20261127002843@example.com | 200 e2e.a.20261127002843@example.com | ✅ PASS |
| 17 | Xác thực | Đăng xuất | 200 | 200 | ✅ PASS |
| 18 | Xác thực | Sau đăng xuất, phiên không còn | 401 | 401 | ✅ PASS |
| 19 | Phân quyền | Chưa đăng nhập gọi /api/v1/users/me → 401 | 401 | 401 | ✅ PASS |
| 20 | Phân quyền | Chưa đăng nhập gọi /api/v1/meals → 401 | 401 | 401 | ✅ PASS |
| 21 | Phân quyền | Chưa đăng nhập gọi /api/v1/statistics/daily → 401 | 401 | 401 | ✅ PASS |
| 22 | Phân quyền | Chưa đăng nhập gọi /api/v1/predict/models → 401 | 401 | 401 | ✅ PASS |
| 23 | Phân quyền | Chưa đăng nhập gọi /api/v1/assistant/status → 401 | 401 | 401 | ✅ PASS |
| 24 | Phân quyền | Chưa đăng nhập POST /predict/nutrition → 401 | 401 | 401 | ✅ PASS |
| 25 | Hồ sơ | Đọc hồ sơ cá nhân | 200 + email đúng | 200 e2e.a.20261127002843@example.com | ✅ PASS |
| 26 | Hồ sơ | Cập nhật hồ sơ | 200 | 200 | ✅ PASS |
| 27 | Hồ sơ | Giá trị hồ sơ được lưu thật (đọc lại) | giá trị mới giữ nguyên | ten=Tên đã sửa kcal=2150.0 cao=171.5 | ✅ PASS |
| 28 | Hồ sơ | Chiều cao vô lý 500 cm | nên bị từ chối 422 | 422 (API hiện chặn) | ✅ PASS |
| 29 | Hồ sơ | Đổi mật khẩu với mật khẩu hiện tại sai → bị chặn | 400/401 | 400 | ✅ PASS |
| 30 | Hồ sơ | Đổi mật khẩu đúng | 200 | 200 | ✅ PASS |
| 31 | Hồ sơ | Đăng nhập bằng mật khẩu mới | 200 | 200 | ✅ PASS |
| 32 | Thực phẩm | Danh sách thực phẩm (phân trang) | 200 + 5 dòng + tổng > 100.000 | 200 5 dòng / tổng 102,847 | ✅ PASS |
| 33 | Thực phẩm | Tìm có dấu và không dấu đều ra kết quả | tất cả > 0 | {"com": 1101, "cơm": 1101, "ga": 4166, "gà": 4166} | ✅ PASS |
| 34 | Thực phẩm | Bộ lọc (danh mục/nhóm/trạng thái/nguồn) | 200 + đủ 4 nguồn dữ liệu trở lên | 200 dm=200 nhom=11 nguon=4 [['openfoodfacts', 20563], ['usda_fndds', 5624], ['usda_foundation', 68867], ['usda_sr_legacy', 7793]] | ✅ PASS |
| 35 | Thực phẩm | Lọc theo trạng thái chế biến | > 0 kết quả | 200 tổng 4,351 | ✅ PASS |
| 36 | Thực phẩm | Lọc theo khoảng kcal trả đúng khoảng | mọi giá trị trong 100–150 | [108.0, 101.2658, 141.176470588235] | ✅ PASS |
| 37 | Thực phẩm | Chi tiết thực phẩm + bảng dinh dưỡng | 200 + có chất dinh dưỡng | 200 15 chất | ✅ PASS |
| 38 | Thực phẩm | Tính khẩu phần 150 g = 1,5 × giá trị/100 g | 534.0 kcal | 534.0 kcal (measured) | ✅ PASS |
| 39 | Thực phẩm | Khối lượng âm bị từ chối | 4xx | 422 | ✅ PASS |
| 40 | Thực phẩm | Thực phẩm không tồn tại → 404 | 404 | 404 | ✅ PASS |
| 41 | Thực phẩm | Thêm thực phẩm nhập tay | 201 + nguồn 'manual' | 201 nguồn=manual | ✅ PASS |
| 42 | Thực phẩm | Tìm lại được thực phẩm vừa thêm (qua tên phụ) | >= 1 | 1 | ✅ PASS |
| 43 | Thực phẩm | Thêm thực phẩm không có tên nào | nên bị từ chối 4xx | 400 (chặn) | ✅ PASS |
| 44 | Bữa ăn | Ghi bữa ăn 2 món | 201 | 201 {"id":15,"eaten_at":"2026-11-27T05:00:00","eaten_at_local":"2026-11-27T12:00:00","meal_typ | ✅ PASS |
| 45 | Bữa ăn | Tổng năng lượng bữa ăn đúng phép cộng | 842.0 kcal | 842.0 kcal | ✅ PASS |
| 46 | Bữa ăn | Món không tồn tại → 404 | 404 | 404 | ✅ PASS |
| 47 | Bữa ăn | Khối lượng 0 g bị từ chối | 4xx | 422 | ✅ PASS |
| 48 | Bữa ăn | Khối lượng 25.000 g (> giới hạn 20.000) bị từ chối | 422 | 422 | ✅ PASS |
| 49 | Bữa ăn | Loại bữa ăn không hợp lệ bị từ chối | 422 | 422 | ✅ PASS |
| 50 | Bữa ăn | Bữa ăn không có món nào | nên bị từ chối 4xx | 422 (chặn) | ✅ PASS |
| 51 | Bữa ăn | Danh sách bữa ăn theo khoảng ngày | chứa bữa vừa tạo | 200 1 bữa | ✅ PASS |
| 52 | Bữa ăn | Chi tiết một bữa ăn | 200 + lunch | 200 lunch | ✅ PASS |
| 53 | Bữa ăn | Sửa bữa ăn | 200 + dinner | 200 dinner | ✅ PASS |
| 54 | Bữa ăn | Bữa ăn giữ số liệu đã chốt (snapshot) | 842.0 kcal sau khi sửa | 842.0 kcal | ✅ PASS |
| 55 | Thống kê | Thống kê ngày khớp dữ liệu vừa ghi | 842.0 kcal | 842.0 kcal | ✅ PASS |
| 56 | Thống kê | Phân bổ năng lượng 4/4/9 có đủ 3 tỉ lệ | tổng ~100 % | {"protein_kcal": 105.1, "carbohydrate_kcal": 688.6, "fat_kcal": 36.7, "protein_percent": 12.7, "carbohydrate_percent": 82.9, "fat_percent": 4.4} | ✅ PASS |
| 57 | Thống kê | Thống kê ngày nêu rõ chất còn thiếu | danh sách (có thể rỗng) | ['fiber_g', 'sodium_mg', 'sugar_g'] | ✅ PASS |
| 58 | Thống kê | Thống kê tuần trả 7 ngày | 7 điểm | 7 điểm | ✅ PASS |
| 59 | Thống kê | Ngày thiếu dữ liệu là null (không phải 0) | kcal = null khi không có dữ liệu | [None] | ✅ PASS |
| 60 | Thống kê | Số liệu hôm nay trong tuần khớp thống kê ngày | 842.0 | 842.0 | ✅ PASS |
| 61 | Thống kê | Thống kê tháng trả đủ số ngày của tháng | 30 điểm | 30 điểm | ✅ PASS |
| 62 | Thống kê | Ngày không hợp lệ bị từ chối | 422 | 422 | ✅ PASS |
| 63 | Dự đoán | Trạng thái model nhận diện ảnh | available = True | True \| 24 lớp \| acc test 0.7521 | ✅ PASS |
| 64 | Dự đoán | Trạng thái model hồi quy năng lượng | available = True | True \| None | ✅ PASS |
| 65 | Dự đoán | Nhận diện ảnh món ăn thật | 200 + Top-3 | 200 top1=pizza 94.3% \| 88 ms | ✅ PASS |
| 66 | Dự đoán | Nhãn trả về thuộc 24 lớp đã huấn luyện | nhãn hợp lệ | ['pizza', 'pasta', 'com_chien'] | ✅ PASS |
| 67 | Dự đoán | Tệp không phải ảnh bị từ chối (kiểm tra magic bytes) | 4xx | 400 {"detail":"Nội dung tệp không phải ảnh JPEG/PNG/WEBP hợp lệ."} | ✅ PASS |
| 68 | Dự đoán | Tệp rỗng bị từ chối | 4xx | 400 | ✅ PASS |
| 69 | Dự đoán | Xem lại ảnh đã tải lên (chủ sở hữu) | 200 | 200 | ✅ PASS |
| 70 | Dự đoán | Tra năng lượng theo thực phẩm | 200 + có số | 200 130.0 kcal (nguồn: database) | ✅ PASS |
| 71 | Dự đoán | Ước lượng năng lượng bằng model hồi quy | 0 < kcal < 1000 | 123.8 kcal (nguồn: model) | ✅ PASS |
| 72 | Dự đoán | Chấp nhận tên feature theo mã chất trong database (moisture_g) | cùng kết quả với water_g | HTTP 200 123.8 vs 123.8 | ✅ PASS |
| 73 | Dự đoán | Thiếu feature -> báo rõ đang thiếu gì, không bịa số | 400 + nêu tên feature thiếu | 400 Thiếu feature đầu vào: fat_g, carbohydrate_g, fiber_g, water_g, ash_g. Hãy bổ sung hoặc để | ✅ PASS |
| 74 | Dự đoán | Thực phẩm không tồn tại khi tra năng lượng → 404 | 404 | 404 | ✅ PASS |
| 75 | Trợ lý AI | Trạng thái trợ lý | available = True | 200 model=qwen3.5:0.8b host=http://127.0.0.1:11434 | ✅ PASS |
| 76 | Trợ lý AI | Hỏi trợ lý và nhận câu trả lời thật | 200 + câu trả lời | 200 19644 ms \| 1. Người dùng chưa đặt mục tiêu calo hôm nay.
2. Tổng năng lượng trong 1 ngày có | ✅ PASS |
| 77 | Trợ lý AI | Câu trả lời có bám dữ liệu thật (grounded) | grounded = True + context_used | grounded=True khoá ngữ cảnh=['user', 'today_local', 'timezone', 'today_totals', 'today_missing_nutrients', 'today_by_meal_type', 'today_target', 'toda | ✅ PASS |
| 78 | Trợ lý AI | Số kcal trong câu trả lời khớp dữ liệu thật | câu trả lời chứa 842 kcal | chứa số khớp: True \| trả lời: 1. Người dùng chưa đặt mục tiêu calo hôm nay.
2. Tổng năng lượng trong 1 ngày có dữ liệu là 842.0 kcal.
3. Thực phẩm đư | ✅ PASS |
| 79 | Trợ lý AI | Câu hỏi rỗng bị từ chối | 422 | 422 | ✅ PASS |
| 80 | Trợ lý AI | Lịch sử trò chuyện lưu lại | có câu hỏi và câu trả lời | 200 2 tin nhắn | ✅ PASS |
| 81 | Trợ lý AI | Từ chối truy vấn SQL/thông tin hệ thống khi bị dụ | không lộ SQL/mật khẩu | lộ: False \| trả lời: Chưa có dữ liệu để trả lời câu hỏi này. | ✅ PASS |
| 82 | Cách ly | Tài khoản B không thấy bữa ăn của A | không chứa bữa của A | B có 0 bữa | ✅ PASS |
| 83 | Cách ly | B truy cập bữa ăn của A → 404 | 404 | 404 | ✅ PASS |
| 84 | Cách ly | B xem ảnh của A → 404 | 404 | 404 | ✅ PASS |
| 85 | Cách ly | Thống kê của B không lẫn dữ liệu của A | 0 hoặc null | None | ✅ PASS |
| 86 | Xoá và dọn dẹp | Xoá bữa ăn | 200 hoặc 204 | 204 | ✅ PASS |
| 87 | Xoá và dọn dẹp | Bữa ăn đã xoá không còn | 404 | 404 | ✅ PASS |
| 88 | Xoá và dọn dẹp | Xoá tài khoản với xác nhận sai → bị chặn | 4xx | 400 | ✅ PASS |
| 89 | Xoá và dọn dẹp | Xoá tài khoản A (xác nhận đúng) | 200 | 200 | ✅ PASS |
| 90 | Xoá và dọn dẹp | Tài khoản đã xoá không đăng nhập được | 401 | 401 | ✅ PASS |
| 91 | Xoá và dọn dẹp | Xoá tài khoản B | 200 | 200 | ✅ PASS |
| 92 | Xoá và dọn dẹp | Dọn thực phẩm do bộ kiểm thử tạo | xoá hết bản ghi 'Thực phẩm kiểm thử …' | đã xoá 1 bản ghi | ✅ PASS |

> Bảng này do `scripts/e2e_web_test.py` sinh ra; số liệu là kết quả gọi API thật, không nhập tay.
