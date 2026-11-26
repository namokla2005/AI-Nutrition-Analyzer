# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-26T21:33:21+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cuda** (GPU Quadro P2000 · Pascal sm_61 — dùng bản PyTorch cu121 vì các bản CUDA mới hơn đã bỏ Pascal)
- Nguồn dữ liệu: manifest data\processed\image_dataset_manifest_v6.csv (1688 ảnh)
- Số lớp: **25**
- Thời gian huấn luyện: **621.8 s** cho 27 epoch (21.3, 22.2, 22.5, 23.3, 23.4, 23.2, 23.0, 22.7, 22.8, 23.5, 23.1, 23.3, 21.9, 25.2, 28.1, 24.4, 23.0, 23.2, 23.1, 23.7, 22.1, 22.0, 22.1, 21.9, 21.4, 22.1, 22.3 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1181 |
| validation | 257 |
| test | 250 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.7354** (epoch 19) |
| Loss tốt nhất trên validation | 1.1763 |
| **Accuracy trên tập test** | **0.7000** |
| Loss trên tập test | 1.1791 |
| Macro F1 trên tập test | 0.6629 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_chung | 5 | 0.7143 | 1.0 | 0.8333 |
| banh_cuon | 7 | 1.0 | 0.4286 | 0.6 |
| banh_mi | 14 | 0.8571 | 0.8571 | 0.8571 |
| banh_xeo | 6 | 0.8 | 0.6667 | 0.7273 |
| bun_bo_hue | 8 | 0.5 | 0.75 | 0.6 |
| bun_cha | 10 | 0.8182 | 0.9 | 0.8571 |
| bun_rieu | 5 | 0.6667 | 0.4 | 0.5 |
| bun_thit_nuong | 6 | 0.2222 | 0.3333 | 0.2667 |
| cha_ca | 6 | 0.8 | 0.6667 | 0.7273 |
| com_chien | 15 | 0.8571 | 0.8 | 0.8276 |
| com_tam | 8 | 0.75 | 0.75 | 0.75 |
| fried_chicken | 15 | 0.8125 | 0.8667 | 0.8387 |
| goi_cuon | 6 | 0.625 | 0.8333 | 0.7143 |
| hamburger | 15 | 0.8125 | 0.8667 | 0.8387 |
| hu_tieu | 6 | 0.25 | 0.1667 | 0.2 |
| mi_quang | 6 | 0.6 | 0.5 | 0.5455 |
| nem_ran | 14 | 0.9167 | 0.7857 | 0.8462 |
| pasta | 15 | 0.8571 | 0.4 | 0.5455 |
| pho_bo | 13 | 0.6364 | 0.5385 | 0.5833 |
| pho_ga | 5 | 0.3333 | 0.6 | 0.4286 |
| pizza | 15 | 0.625 | 1.0 | 0.7692 |
| salad | 15 | 0.6875 | 0.7333 | 0.7097 |
| steak | 15 | 0.8333 | 0.6667 | 0.7407 |
| sushi | 15 | 0.6 | 0.6 | 0.6 |
| xoi | 5 | 0.75 | 0.6 | 0.6667 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 3.0993 | 0.1236 | 2.8877 | 0.214 | 21.3 |
| 2 | 2.5672 | 0.3903 | 2.3708 | 0.4086 | 22.2 |
| 3 | 2.02 | 0.4962 | 1.9492 | 0.5409 | 22.5 |
| 4 | 1.5989 | 0.6105 | 1.6567 | 0.5798 | 23.3 |
| 5 | 1.2199 | 0.696 | 1.4781 | 0.6381 | 23.4 |
| 6 | 1.0036 | 0.7248 | 1.3403 | 0.6537 | 23.2 |
| 7 | 0.8407 | 0.7722 | 1.2442 | 0.6381 | 23.0 |
| 8 | 0.7258 | 0.7951 | 1.2158 | 0.6693 | 22.7 |
| 9 | 0.5871 | 0.8374 | 1.1688 | 0.7004 | 22.8 |
| 10 | 0.5407 | 0.84 | 1.1694 | 0.677 | 23.5 |
| 11 | 0.4711 | 0.8544 | 1.1734 | 0.6809 | 23.1 |
| 12 | 0.4234 | 0.8823 | 1.157 | 0.6965 | 23.3 |
| 13 | 0.3609 | 0.9086 | 1.1716 | 0.6732 | 21.9 |
| 14 | 0.3307 | 0.9001 | 1.1555 | 0.716 | 25.2 |
| 15 | 0.3216 | 0.9043 | 1.16 | 0.7198 | 28.1 |
| 16 | 0.2698 | 0.9331 | 1.1768 | 0.7043 | 24.4 |
| 17 | 0.2346 | 0.9331 | 1.1799 | 0.7082 | 23.0 |
| 18 | 0.2078 | 0.9534 | 1.1695 | 0.7237 | 23.2 |
| 19 | 0.2191 | 0.9492 | 1.1763 | 0.7354 | 23.1 |
| 20 | 0.1871 | 0.9483 | 1.1853 | 0.7043 | 23.7 |
| 21 | 0.1889 | 0.9517 | 1.173 | 0.7276 | 22.1 |
| 22 | 0.1712 | 0.9543 | 1.1693 | 0.7315 | 22.0 |
| 23 | 0.167 | 0.9551 | 1.1743 | 0.7276 | 22.1 |
| 24 | 0.1492 | 0.9687 | 1.1724 | 0.7121 | 21.9 |
| 25 | 0.147 | 0.967 | 1.1672 | 0.7237 | 21.4 |
| 26 | 0.1298 | 0.9687 | 1.1693 | 0.716 | 22.1 |
| 27 | 0.1327 | 0.9687 | 1.1814 | 0.7082 | 22.3 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
