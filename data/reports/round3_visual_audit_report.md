# Kiểm duyệt ảnh huấn luyện vòng 3 (20 món Việt)

Sinh viên thực hiện: Phạm Hoài Nam – Xuân Hải (DK14-CNTT2). Môn: Trí tuệ nhân tạo.

## 1. Cách làm

1. Năm luồng thu thập chạy song song tải ảnh cho 20 món Việt (4 món còn thiếu + 16 món mới),
   mỗi ảnh lưu kèm tệp sidecar JSON ghi URL nguồn, trang tìm kiếm, giấy phép (nếu công bố) và
   SHA-256; ảnh bị loại được **chuyển** (không xoá) sang `data/raw/images/_rejected/<lớp>/`.
2. Tôi **kiểm chứng độc lập trên đĩa**: đếm tệp theo từng lớp, đối chiếu với số luồng báo, kiểm
   tra sidecar, tìm ảnh trùng nội dung giữa các lớp bằng SHA-1.
3. Tôi tự dựng contact sheet cho từng lớp bằng mẫu ngẫu nhiên có khoá (`random.seed`), rồi giao
   cho **8 luồng kiểm duyệt độc lập** (khác luồng thu thập) soi bằng mắt và trả về đúng số ô sai.
4. Vì mẫu có khoá, tôi tái lập được phép lấy mẫu để **ánh xạ ngược số ô → tên tệp** và chuyển
   đúng những ảnh đó ra khỏi tập huấn luyện.

## 2. Kết quả kiểm chứng trên đĩa

* 20/20 lớp có số ảnh **khớp đúng hoặc vượt** số luồng báo (xem bảng dưới).
* 1 ảnh trùng nội dung giữa hai lớp (`bun_rieu/ov_ca723e83.jpg` = `canh_chua/ov_ca723e83.jpg`)
  → đã xoá bản ở `canh_chua`.
* Toàn bộ ảnh mới đều có sidecar; ảnh Food-101 (8 lớp × 300) không có sidecar vì lấy từ bộ chuẩn.

## 3. Số ảnh đúng theo mẫu soi và số ảnh đã loại

| Lớp | Mẫu soi | Đúng trong mẫu | Tỉ lệ | Còn lại sau lọc | Ước lượng ảnh sạch |
|---|---:|---:|---:|---:|---:|
| `canh_chua` | 16 | 14 | 88% | 40 | ~35 |
| `banh_beo` | 20 | 18 | 90% | 42 | ~38 |
| `banh_khot` | 16 | 15 | 94% | 48 | ~45 |
| `bun_dau_mam_tom` | 20 | 19 | 95% | 45 | ~43 |
| `banh_bao` | 15 | 14 | 93% | 33 | ~31 |
| `chao` | 15 | 15 | 100% | 48 | ~48 |
| `banh_canh` | 15 | 14 | 93% | 45 | ~42 |
| `banh_uot` | 15 | 12 | 80% | 54 | ~43 |
| `banh_tom` | 15 | 15 | 100% | 50 | ~50 |
| `bo_kho` | 15 | 15 | 100% | 53 | ~53 |
| `thit_kho_trung` | 15 | 15 | 100% | 62 | ~62 |
| `ca_kho_to` | 15 | 11 | 73% | 42 | ~31 |
| `com_ga` | 15 | 15 | 100% | 36 | ~36 |
| `xoi_xeo` | 15 | 15 | 100% | 58 | ~58 |
| `che_ba_mau` | 15 | 9 | 60% | 41 | ~25 |
| `banh_da_cua` | 15 | 15 | 100% | 35 | ~35 |
| `goi_ga` | 15 | 15 | 100% | 43 | ~43 |
| `banh_trang_nuong` | 15 | 15 | 100% | 22 | ~22 |
| `mi_xao` | 15 | 15 | 100% | 38 | ~38 |

Tổng số ảnh bị loại ở vòng này: **21 ảnh** (đã chuyển sang
`_rejected`, không xoá).

## 4. Quyết định

* 19 lớp đủ ảnh sạch để huấn luyện (mỗi lớp ≥ 22 ảnh sạch, phần lớn ≥ 35).
* **Loại lớp `bun_mam` khỏi lần huấn luyện này**: mẫu soi chỉ 6/15 ảnh đúng món; sau khi loại còn ~10 ảnh sạch. Ảnh vẫn giữ trong dự án để
  thu thập thêm rồi huấn luyện lại — không đưa vào mô hình khi chưa đủ sạch.
* Lớp `banh_trang_nuong` chỉ có 22 ảnh sạch (dưới ngưỡng 34): vẫn huấn luyện nhưng ghi rõ trong
  báo cáo là lớp ít dữ liệu nhất.

## 5. Giấy phép

Phần lớn ảnh mới lấy từ tìm kiếm ảnh công khai và **không công bố giấy phép rõ ràng**: dự án ghi
trung thực giá trị `unknown` và lưu URL ảnh + trang nguồn thật trong sidecar, không tự gán giấy
phép. Đây là dự án học tập, không phát hành lại ảnh.
