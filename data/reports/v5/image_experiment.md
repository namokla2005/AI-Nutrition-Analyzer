# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-26T19:33:56+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cpu** (xem TD-03: GPU Quadro P2000 sm_61 không dùng được)
- Nguồn dữ liệu: manifest data\processed\image_dataset_manifest_v4.csv (1579 ảnh)
- Số lớp: **22**
- Thời gian huấn luyện: **2330.8 s** cho 25 epoch (145.8, 129.9, 120.0, 86.1, 115.2, 113.2, 117.0, 114.2, 145.5, 131.3, 113.7, 116.1, 108.7, 101.8, 67.8, 53.4, 50.9, 52.5, 58.8, 74.6, 46.3, 51.8, 75.2, 70.5, 69.8 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1105 |
| validation | 240 |
| test | 234 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.7083** (epoch 19) |
| Loss tốt nhất trên validation | 1.0562 |
| **Accuracy trên tập test** | **0.7137** |
| Loss trên tập test | 1.0138 |
| Macro F1 trên tập test | 0.7062 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_chung | 5 | 0.8 | 0.8 | 0.8 |
| banh_cuon | 7 | 0.6667 | 0.5714 | 0.6154 |
| banh_mi | 14 | 0.8333 | 0.7143 | 0.7692 |
| banh_xeo | 6 | 1.0 | 0.6667 | 0.8 |
| bun_bo_hue | 8 | 0.6 | 0.75 | 0.6667 |
| bun_cha | 10 | 0.5833 | 0.7 | 0.6364 |
| cha_ca | 6 | 1.0 | 0.5 | 0.6667 |
| com_chien | 15 | 0.7647 | 0.8667 | 0.8125 |
| com_tam | 8 | 1.0 | 0.75 | 0.8571 |
| fried_chicken | 15 | 0.8667 | 0.8667 | 0.8667 |
| goi_cuon | 6 | 0.4444 | 0.6667 | 0.5333 |
| hamburger | 15 | 0.7333 | 0.7333 | 0.7333 |
| hu_tieu | 6 | 0.5 | 0.5 | 0.5 |
| mi_quang | 6 | 0.5714 | 0.6667 | 0.6154 |
| nem_ran | 14 | 0.8571 | 0.8571 | 0.8571 |
| pasta | 15 | 0.5333 | 0.5333 | 0.5333 |
| pho_bo | 13 | 0.6 | 0.6923 | 0.6429 |
| pizza | 15 | 0.6667 | 0.8 | 0.7273 |
| salad | 15 | 0.9167 | 0.7333 | 0.8148 |
| steak | 15 | 0.5882 | 0.6667 | 0.625 |
| sushi | 15 | 0.7692 | 0.6667 | 0.7143 |
| xoi | 5 | 1.0 | 0.6 | 0.75 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 2.9114 | 0.1692 | 2.5723 | 0.3667 | 145.8 |
| 2 | 2.2984 | 0.4371 | 1.9735 | 0.4667 | 129.9 |
| 3 | 1.7171 | 0.543 | 1.5625 | 0.5583 | 120.0 |
| 4 | 1.3771 | 0.6262 | 1.3761 | 0.6333 | 86.1 |
| 5 | 1.1032 | 0.6824 | 1.2322 | 0.6625 | 115.2 |
| 6 | 0.9004 | 0.7647 | 1.1757 | 0.6667 | 113.2 |
| 7 | 0.7403 | 0.81 | 1.1483 | 0.675 | 117.0 |
| 8 | 0.6619 | 0.8208 | 1.1086 | 0.6958 | 114.2 |
| 9 | 0.5574 | 0.8507 | 1.0626 | 0.6875 | 145.5 |
| 10 | 0.5439 | 0.8525 | 1.0622 | 0.6792 | 131.3 |
| 11 | 0.4857 | 0.8706 | 1.0449 | 0.7 | 113.7 |
| 12 | 0.4194 | 0.895 | 1.0522 | 0.6958 | 116.1 |
| 13 | 0.3514 | 0.905 | 1.063 | 0.7042 | 108.7 |
| 14 | 0.3195 | 0.9231 | 1.0452 | 0.6958 | 101.8 |
| 15 | 0.3092 | 0.9249 | 1.0595 | 0.6875 | 67.8 |
| 16 | 0.2961 | 0.9348 | 1.0405 | 0.6958 | 53.4 |
| 17 | 0.2649 | 0.9457 | 1.0375 | 0.7042 | 50.9 |
| 18 | 0.2575 | 0.9385 | 1.0557 | 0.6958 | 52.5 |
| 19 | 0.2278 | 0.9575 | 1.0562 | 0.7083 | 58.8 |
| 20 | 0.2528 | 0.9448 | 1.0526 | 0.7042 | 74.6 |
| 21 | 0.2224 | 0.9575 | 1.0572 | 0.7 | 46.3 |
| 22 | 0.2337 | 0.9457 | 1.0592 | 0.7042 | 51.8 |
| 23 | 0.222 | 0.9593 | 1.0613 | 0.6958 | 75.2 |
| 24 | 0.2121 | 0.9511 | 1.0618 | 0.7 | 70.5 |
| 25 | 0.2161 | 0.9529 | 1.0615 | 0.7 | 69.8 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
