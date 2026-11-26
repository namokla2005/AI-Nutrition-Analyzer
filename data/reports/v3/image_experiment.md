# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-26T16:52:06+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cpu** (xem TD-03: GPU Quadro P2000 sm_61 không dùng được)
- Nguồn dữ liệu: manifest data\processed\image_dataset_manifest_v3.csv (1577 ảnh)
- Số lớp: **24**
- Thời gian huấn luyện: **1828.4 s** cho 15 epoch (199.6, 123.4, 130.5, 127.7, 175.0, 98.6, 110.3, 107.8, 115.3, 103.0, 110.8, 102.8, 105.7, 107.0, 110.2 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1103 |
| validation | 240 |
| test | 234 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.7000** (epoch 13) |
| Loss tốt nhất trên validation | 1.1186 |
| **Accuracy trên tập test** | **0.7521** |
| Loss trên tập test | 0.8241 |
| Macro F1 trên tập test | 0.7619 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_beo | 3 | 1.0 | 0.6667 | 0.8 |
| banh_chung | 5 | 0.625 | 1.0 | 0.7692 |
| banh_khot | 4 | 1.0 | 0.75 | 0.8571 |
| banh_mi | 14 | 0.8 | 0.5714 | 0.6667 |
| banh_xeo | 6 | 0.8 | 0.6667 | 0.7273 |
| bun_bo_hue | 8 | 0.6667 | 0.5 | 0.5714 |
| bun_cha | 10 | 0.7273 | 0.8 | 0.7619 |
| bun_dau_mam_tom | 2 | 1.0 | 0.5 | 0.6667 |
| canh_chua | 4 | 1.0 | 1.0 | 1.0 |
| cha_ca | 6 | 1.0 | 0.6667 | 0.8 |
| com_chien | 15 | 0.8667 | 0.8667 | 0.8667 |
| com_tam | 8 | 0.6667 | 0.5 | 0.5714 |
| fried_chicken | 15 | 0.9231 | 0.8 | 0.8571 |
| goi_cuon | 6 | 0.75 | 0.5 | 0.6 |
| hamburger | 15 | 0.7778 | 0.9333 | 0.8485 |
| hu_tieu | 5 | 1.0 | 1.0 | 1.0 |
| mi_quang | 6 | 0.8571 | 1.0 | 0.9231 |
| nem_ran | 14 | 1.0 | 0.8571 | 0.9231 |
| pasta | 15 | 0.6429 | 0.6 | 0.6207 |
| pho_bo | 13 | 0.6429 | 0.6923 | 0.6667 |
| pizza | 15 | 0.6842 | 0.8667 | 0.7647 |
| salad | 15 | 0.7059 | 0.8 | 0.75 |
| steak | 15 | 0.6111 | 0.7333 | 0.6667 |
| sushi | 15 | 0.5556 | 0.6667 | 0.6061 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 2.9772 | 0.1659 | 2.7166 | 0.2833 | 199.6 |
| 2 | 2.3655 | 0.4089 | 2.122 | 0.4375 | 123.4 |
| 3 | 1.7818 | 0.5313 | 1.7096 | 0.5125 | 130.5 |
| 4 | 1.3634 | 0.6383 | 1.4512 | 0.5833 | 127.7 |
| 5 | 1.0752 | 0.7081 | 1.3262 | 0.6083 | 175.0 |
| 6 | 0.9172 | 0.7561 | 1.2374 | 0.6167 | 98.6 |
| 7 | 0.772 | 0.7978 | 1.1992 | 0.6583 | 110.3 |
| 8 | 0.6901 | 0.8141 | 1.1895 | 0.6708 | 107.8 |
| 9 | 0.6119 | 0.8377 | 1.1505 | 0.675 | 115.3 |
| 10 | 0.5743 | 0.8558 | 1.1471 | 0.6833 | 103.0 |
| 11 | 0.5142 | 0.8713 | 1.1376 | 0.7 | 110.8 |
| 12 | 0.5329 | 0.8595 | 1.1248 | 0.6958 | 102.8 |
| 13 | 0.489 | 0.8812 | 1.1186 | 0.7 | 105.7 |
| 14 | 0.4838 | 0.8849 | 1.1169 | 0.6958 | 107.0 |
| 15 | 0.4775 | 0.8858 | 1.1177 | 0.6958 | 110.2 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
