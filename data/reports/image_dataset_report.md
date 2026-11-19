# Báo cáo chuẩn bị bộ ảnh nhận diện món ăn

- Thời điểm tạo: `2026-11-19T04:02:46+07:00`
- Giới hạn lần chạy: **100 ảnh/lớp** (mặc định của script: 300).
- Seed chia tập: **20261119**; tỷ lệ mục tiêu theo từng lớp: **70% train / 15% val / 15% test**.
- Kích thước ảnh đầu ra: cạnh dài tối đa **512px**, JPEG quality **85**; resize 224×224 để trainer thực hiện.
- Tổng ảnh JPEG thực có trong manifest: **1208**; tổng dung lượng JPEG trên đĩa: **58.629.884 byte (55.91 MiB)**.
- Tổng payload tệp ảnh nguồn đã chọn được tải/đọc: **416.703.981 byte (397.40 MiB)**. Với streaming Parquet, đây không phải tổng lưu lượng HTTP vì thư viện không công bố số byte range/chunk đã truyền.

## Kết quả thực tế theo lớp

| Lớp dự án | Tên hiển thị | Nguồn chọn | Kiểu phủ Food-101 | Train | Val | Test | Tổng | Byte JPEG |
|---|---|---|---|---:|---:|---:|---:|---:|
| `banh_mi` | Bánh mì | commons | not_covered | 70 | 15 | 15 | 100 | 4,369,205 |
| `banh_xeo` | Bánh xèo | commons | not_covered | 29 | 6 | 6 | 41 | 1,871,361 |
| `bun_bo_hue` | Bún bò Huế | commons | not_covered | 36 | 8 | 7 | 51 | 2,609,528 |
| `bun_cha` | Bún chả | commons | not_covered | 34 | 7 | 7 | 48 | 2,354,648 |
| `com_chien` | Cơm chiên | food101 | approximate | 70 | 15 | 15 | 100 | 4,996,239 |
| `com_tam` | Cơm tấm | commons | not_covered | 53 | 11 | 11 | 75 | 4,025,817 |
| `fried_chicken` | Fried Chicken | food101 | approximate | 70 | 15 | 15 | 100 | 4,772,129 |
| `goi_cuon` | Gỏi cuốn | commons | approximate | 33 | 7 | 7 | 47 | 1,692,758 |
| `hamburger` | Hamburger | food101 | exact | 70 | 15 | 15 | 100 | 4,652,495 |
| `pasta` | Pasta | food101 | approximate | 70 | 15 | 15 | 100 | 4,863,385 |
| `pho_bo` | Phở bò | commons | approximate | 32 | 7 | 7 | 46 | 2,171,441 |
| `pizza` | Pizza | food101 | exact | 70 | 15 | 15 | 100 | 5,504,473 |
| `salad` | Salad | food101 | approximate | 70 | 15 | 15 | 100 | 5,268,597 |
| `steak` | Steak | food101 | exact | 70 | 15 | 15 | 100 | 4,982,204 |
| `sushi` | Sushi | food101 | exact | 70 | 15 | 15 | 100 | 4,495,604 |

## Quy mô split

- Train: **847** ảnh.
- Validation (`val`): **181** ảnh.
- Test: **180** ảnh.
- Ảnh được nhận diện bằng SHA-256 của JPEG chuẩn hóa; script từ chối định danh trùng, nên một ảnh không thể nằm ở hai split.

## Lớp có quá ít ảnh để huấn luyện

Ngưỡng vận hành được khai báo cho báo cáo này là **100 ảnh/lớp** (có thể đổi bằng `--minimum-trainable`).

- `banh_xeo`: **41** ảnh (< 100).
- `bun_bo_hue`: **51** ảnh (< 100).
- `bun_cha`: **48** ảnh (< 100).
- `com_tam`: **75** ảnh (< 100).
- `goi_cuon`: **47** ảnh (< 100).
- `pho_bo`: **46** ảnh (< 100).

## Food-101 qua Hugging Face

- Repo: <https://huggingface.co/datasets/ethz/food101>.
- Bố cục đã xác minh: train **75.750 dòng / 3.798.520.995 byte / 8 shard**; validation **25.250 dòng / 1.261.451.313 byte / 3 shard**; tổng cộng 11 shard.
- Phương thức lần chạy: `huggingface_datasets_streaming`; số dòng train đã quét: **67600**.
- Không tải nguyên shard Parquet nào; dùng streaming và dừng khi các lớp Food-101 đạt cap.

### Ràng buộc quyền Food-101

Ảnh Food-101 đến từ **Foodspotting** và **không thuộc sở hữu ETHZ**. Dataset card chỉ cho phép phạm vi scientific fair use; mọi sử dụng vượt phạm vi đó phải thương lượng với chủ ảnh theo điều khoản Foodspotting. Bộ dữ liệu này được chuẩn bị cho **bài tập/dự án học thuật, nghiên cứu khoa học**. Dự án **không được tuyên bố giấy phép mở bao trùm** cho ảnh Food-101 và không nên phát hành lại ảnh như một bộ open data.

## Wikimedia Commons

- Ảnh Commons trong manifest: **408**; ảnh Food-101: **800**.
- Collector dùng allow-list CC0, CC BY, CC BY-SA và Public domain; attribution/licence URL của từng tệp nằm trong cột `licence/source note`.
- Category Commons có thể lẫn ảnh nhà hàng, nguyên liệu hoặc biến thể; cần duyệt thủ công trước khi huấn luyện chính thức.

## Ánh xạ lớp và giới hạn nhãn

Ánh xạ máy đọc được nằm tại `training/image/class_map.json`. Bốn lớp Food-101 phủ chính xác là `pizza`, `hamburger`, `sushi`, `steak`; các ánh xạ khác là gần đúng hoặc không được Food-101 phủ. Ảnh cho bảy món Việt được lấy từ Commons thay vì gán nhãn sai bằng lớp Food-101 rộng/khác món.

## Tệp đầu ra

- `data/raw/images/<our_class_name>/*.jpg`: ảnh đã chuẩn hóa.
- `data/processed/image_dataset_manifest.csv`: manifest dùng để trainer đọc split; không dùng `ImageFolder` để tự chia.
- `data/processed/image_dataset_run.json`: thống kê phương thức tải và lỗi xử lý của lần chạy.
