# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-26T21:19:20+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cuda** (GPU Quadro P2000 · Pascal sm_61 — dùng bản PyTorch cu121 vì các bản CUDA mới hơn đã bỏ Pascal)
- Nguồn dữ liệu: manifest data\processed\image_dataset_manifest_v6.csv (1688 ảnh)
- Số lớp: **25**
- Thời gian huấn luyện: **586.5 s** cho 26 epoch (21.1, 22.8, 23.0, 22.4, 21.9, 21.5, 21.8, 21.6, 21.7, 22.4, 22.1, 23.1, 23.2, 22.3, 22.5, 22.3, 23.3, 23.0, 23.5, 22.9, 22.8, 23.0, 23.5, 23.1, 22.6, 22.5 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1181 |
| validation | 257 |
| test | 250 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.7393** (epoch 18) |
| Loss tốt nhất trên validation | 1.0641 |
| **Accuracy trên tập test** | **0.6680** |
| Loss trên tập test | 1.1196 |
| Macro F1 trên tập test | 0.6369 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_chung | 5 | 0.7143 | 1.0 | 0.8333 |
| banh_cuon | 7 | 0.75 | 0.4286 | 0.5455 |
| banh_mi | 14 | 0.7059 | 0.8571 | 0.7742 |
| banh_xeo | 6 | 1.0 | 0.6667 | 0.8 |
| bun_bo_hue | 8 | 0.4545 | 0.625 | 0.5263 |
| bun_cha | 10 | 0.8182 | 0.9 | 0.8571 |
| bun_rieu | 5 | 0.6667 | 0.4 | 0.5 |
| bun_thit_nuong | 6 | 0.2222 | 0.3333 | 0.2667 |
| cha_ca | 6 | 0.75 | 0.5 | 0.6 |
| com_chien | 15 | 0.75 | 0.8 | 0.7742 |
| com_tam | 8 | 0.5556 | 0.625 | 0.5882 |
| fried_chicken | 15 | 0.8 | 0.8 | 0.8 |
| goi_cuon | 6 | 0.5714 | 0.6667 | 0.6154 |
| hamburger | 15 | 0.9286 | 0.8667 | 0.8966 |
| hu_tieu | 6 | 0.2 | 0.1667 | 0.1818 |
| mi_quang | 6 | 0.5 | 0.5 | 0.5 |
| nem_ran | 14 | 0.8889 | 0.5714 | 0.6957 |
| pasta | 15 | 0.5385 | 0.4667 | 0.5 |
| pho_bo | 13 | 0.6667 | 0.4615 | 0.5455 |
| pho_ga | 5 | 0.4 | 0.8 | 0.5333 |
| pizza | 15 | 0.6667 | 0.8 | 0.7273 |
| salad | 15 | 0.6875 | 0.7333 | 0.7097 |
| steak | 15 | 0.7692 | 0.6667 | 0.7143 |
| sushi | 15 | 0.6471 | 0.7333 | 0.6875 |
| xoi | 5 | 1.0 | 0.6 | 0.75 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 3.0375 | 0.1626 | 2.7436 | 0.2685 | 21.1 |
| 2 | 2.3886 | 0.3954 | 2.1277 | 0.4397 | 22.8 |
| 3 | 1.8186 | 0.5216 | 1.7314 | 0.5486 | 23.0 |
| 4 | 1.4462 | 0.6088 | 1.5047 | 0.6187 | 22.4 |
| 5 | 1.142 | 0.7104 | 1.3352 | 0.6459 | 21.9 |
| 6 | 0.9561 | 0.7333 | 1.2391 | 0.6848 | 21.5 |
| 7 | 0.7993 | 0.7934 | 1.1573 | 0.6965 | 21.8 |
| 8 | 0.6931 | 0.8086 | 1.1376 | 0.6887 | 21.6 |
| 9 | 0.5652 | 0.8577 | 1.091 | 0.7198 | 21.7 |
| 10 | 0.517 | 0.8586 | 1.0788 | 0.7043 | 22.4 |
| 11 | 0.4645 | 0.8611 | 1.0867 | 0.7121 | 22.1 |
| 12 | 0.3946 | 0.8984 | 1.0633 | 0.7121 | 23.1 |
| 13 | 0.3297 | 0.9297 | 1.0736 | 0.7004 | 23.2 |
| 14 | 0.2995 | 0.9356 | 1.0638 | 0.7276 | 22.3 |
| 15 | 0.2918 | 0.9255 | 1.0735 | 0.7237 | 22.5 |
| 16 | 0.2455 | 0.9441 | 1.0637 | 0.7354 | 22.3 |
| 17 | 0.2147 | 0.9526 | 1.0769 | 0.7354 | 23.3 |
| 18 | 0.1966 | 0.9568 | 1.0641 | 0.7393 | 23.0 |
| 19 | 0.198 | 0.9568 | 1.0753 | 0.7315 | 23.5 |
| 20 | 0.1806 | 0.9585 | 1.0823 | 0.7276 | 22.9 |
| 21 | 0.1671 | 0.967 | 1.0677 | 0.7315 | 22.8 |
| 22 | 0.1568 | 0.9661 | 1.0751 | 0.7354 | 23.0 |
| 23 | 0.1476 | 0.9729 | 1.0728 | 0.7315 | 23.5 |
| 24 | 0.1329 | 0.9788 | 1.077 | 0.7237 | 23.1 |
| 25 | 0.1292 | 0.9721 | 1.0852 | 0.7276 | 22.6 |
| 26 | 0.1204 | 0.9738 | 1.0843 | 0.7393 | 22.5 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
