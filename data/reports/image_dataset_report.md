# Báo cáo chuẩn bị bộ ảnh nhận diện món ăn

- Thời điểm tạo: `2026-11-26T22:55:31+07:00`
- Giới hạn lần chạy: **100 ảnh/lớp** (mặc định của script: 300).
- Seed chia tập: **20261119**; tỷ lệ mục tiêu theo từng lớp: **70% train / 15% val / 15% test**.
- Kích thước ảnh đầu ra: cạnh dài tối đa **512px**, JPEG quality **85**; resize 224×224 để trainer thực hiện.
- Tổng ảnh JPEG thực có trong manifest: **1711**; tổng dung lượng JPEG trên đĩa: **86.701.318 byte (82.68 MiB)**.
- Tổng payload tệp ảnh nguồn đã chọn được tải/đọc: **520.390.954 byte (496.28 MiB)**. Với streaming Parquet, đây không phải tổng lưu lượng HTTP vì thư viện không công bố số byte range/chunk đã truyền.

## Kết quả thực tế theo lớp

| Lớp dự án | Tên hiển thị | Nguồn chọn | Kiểu phủ Food-101 | Train | Val | Test | Tổng | Byte JPEG |
|---|---|---|---|---:|---:|---:|---:|---:|
| `banh_beo` | Bánh bèo | commons | not_covered | 15 | 3 | 3 | 21 | 970,000 |
| `banh_chung` | Bánh chưng | commons | not_covered | 26 | 6 | 5 | 37 | 2,010,174 |
| `banh_cuon` | Bánh cuốn | commons | not_covered | 21 | 5 | 4 | 30 | 1,340,013 |
| `banh_khot` | Bánh khọt | commons | not_covered | 17 | 4 | 4 | 25 | 1,493,355 |
| `banh_mi` | Bánh mì | commons | not_covered | 68 | 15 | 14 | 97 | 4,291,067 |
| `banh_xeo` | Bánh xèo | commons | not_covered | 26 | 6 | 6 | 38 | 1,892,221 |
| `bun_bo_hue` | Bún bò Huế | commons | not_covered | 36 | 8 | 8 | 52 | 2,579,576 |
| `bun_cha` | Bún chả | commons | not_covered | 47 | 10 | 10 | 67 | 3,508,991 |
| `bun_dau_mam_tom` | Bún đậu mắm tôm | commons | not_covered | 8 | 2 | 2 | 12 | 533,967 |
| `bun_rieu` | Bún riêu | commons | not_covered | 18 | 4 | 4 | 26 | 1,366,335 |
| `bun_thit_nuong` | Bún thịt nướng | commons | not_covered | 11 | 2 | 2 | 15 | 814,550 |
| `canh_chua` | Canh chua | commons | not_covered | 20 | 4 | 4 | 28 | 2,088,213 |
| `cha_ca` | Chả cá | commons | not_covered | 30 | 7 | 6 | 43 | 2,482,874 |
| `com_chien` | Cơm chiên | food101 | approximate | 70 | 15 | 15 | 100 | 4,996,239 |
| `com_tam` | Cơm tấm | commons | not_covered | 39 | 9 | 8 | 56 | 3,001,246 |
| `fried_chicken` | Fried Chicken | food101 | approximate | 70 | 15 | 15 | 100 | 4,772,129 |
| `goi_cuon` | Gỏi cuốn | commons | approximate | 28 | 6 | 6 | 40 | 1,421,770 |
| `hamburger` | Hamburger | food101 | exact | 70 | 15 | 15 | 100 | 4,652,495 |
| `hu_tieu` | Hủ tiếu | commons | not_covered | 22 | 5 | 5 | 32 | 1,622,159 |
| `mi_quang` | Mì Quảng | commons | not_covered | 30 | 7 | 6 | 43 | 2,553,691 |
| `nem_ran` | Nem rán / Chả giò | commons | not_covered | 67 | 14 | 14 | 95 | 5,114,960 |
| `pasta` | Pasta | food101 | approximate | 70 | 15 | 15 | 100 | 4,863,385 |
| `pho_bo` | Phở bò | commons | approximate | 64 | 14 | 13 | 91 | 4,711,554 |
| `pho_ga` | Phở gà | commons | not_covered | 15 | 3 | 3 | 21 | 1,080,918 |
| `pizza` | Pizza | food101 | exact | 70 | 15 | 15 | 100 | 5,504,473 |
| `salad` | Salad | food101 | approximate | 70 | 15 | 15 | 100 | 5,268,597 |
| `steak` | Steak | food101 | exact | 70 | 15 | 15 | 100 | 4,982,204 |
| `sushi` | Sushi | food101 | exact | 70 | 15 | 15 | 100 | 4,495,604 |
| `xoi` | Xôi | commons | not_covered | 30 | 6 | 6 | 42 | 2,288,558 |

## Quy mô split

- Train: **1198** ảnh.
- Validation (`val`): **260** ảnh.
- Test: **253** ảnh.
- Ảnh được nhận diện bằng SHA-256 của JPEG chuẩn hóa; script từ chối định danh trùng, nên một ảnh không thể nằm ở hai split.

## Lớp có quá ít ảnh để huấn luyện

Ngưỡng vận hành được khai báo cho báo cáo này là **100 ảnh/lớp** (có thể đổi bằng `--minimum-trainable`).

- `banh_beo`: **21** ảnh (< 100).
- `banh_chung`: **37** ảnh (< 100).
- `banh_cuon`: **30** ảnh (< 100).
- `banh_khot`: **25** ảnh (< 100).
- `banh_mi`: **97** ảnh (< 100).
- `banh_xeo`: **38** ảnh (< 100).
- `bun_bo_hue`: **52** ảnh (< 100).
- `bun_cha`: **67** ảnh (< 100).
- `bun_dau_mam_tom`: **12** ảnh (< 100).
- `bun_rieu`: **26** ảnh (< 100).
- `bun_thit_nuong`: **15** ảnh (< 100).
- `canh_chua`: **28** ảnh (< 100).
- `cha_ca`: **43** ảnh (< 100).
- `com_tam`: **56** ảnh (< 100).
- `goi_cuon`: **40** ảnh (< 100).
- `hu_tieu`: **32** ảnh (< 100).
- `mi_quang`: **43** ảnh (< 100).
- `nem_ran`: **95** ảnh (< 100).
- `pho_bo`: **91** ảnh (< 100).
- `pho_ga`: **21** ảnh (< 100).
- `xoi`: **42** ảnh (< 100).

## Food-101 qua Hugging Face

- Repo: <https://huggingface.co/datasets/ethz/food101>.
- Bố cục đã xác minh: train **75.750 dòng / 3.798.520.995 byte / 8 shard**; validation **25.250 dòng / 1.261.451.313 byte / 3 shard**; tổng cộng 11 shard.
- Phương thức lần chạy: `existing_local_food101_images`; số dòng train đã quét: **0**.
- Không tải nguyên shard Parquet nào; dùng streaming và dừng khi các lớp Food-101 đạt cap.

### Ràng buộc quyền Food-101

Ảnh Food-101 đến từ **Foodspotting** và **không thuộc sở hữu ETHZ**. Dataset card chỉ cho phép phạm vi scientific fair use; mọi sử dụng vượt phạm vi đó phải thương lượng với chủ ảnh theo điều khoản Foodspotting. Bộ dữ liệu này được chuẩn bị cho **bài tập/dự án học thuật, nghiên cứu khoa học**. Dự án **không được tuyên bố giấy phép mở bao trùm** cho ảnh Food-101 và không nên phát hành lại ảnh như một bộ open data.

## Wikimedia Commons

- Ảnh Commons trong manifest: **911**; ảnh Food-101: **800**.
- Collector dùng allow-list CC0, CC BY, CC BY-SA và Public domain; attribution/licence URL của từng tệp nằm trong cột `licence/source note`.
- Category Commons có thể lẫn ảnh nhà hàng, nguyên liệu hoặc biến thể; cần duyệt thủ công trước khi huấn luyện chính thức.

## Ánh xạ lớp và giới hạn nhãn

Ánh xạ máy đọc được nằm tại `training/image/class_map.json`. Bốn lớp Food-101 phủ chính xác là `pizza`, `hamburger`, `sushi`, `steak`; các ánh xạ khác là gần đúng hoặc không được Food-101 phủ. Các món Việt dùng ảnh Commons và cần duyệt contact sheet trước khi huấn luyện.

## Tệp đầu ra

- `data/raw/images/<our_class_name>/*.jpg`: ảnh đã chuẩn hóa.
- `data/processed/image_dataset_manifest.csv`: manifest dùng để trainer đọc split; không dùng `ImageFolder` để tự chia.
- `data/processed/image_dataset_run.json`: thống kê phương thức tải và lỗi xử lý của lần chạy.
