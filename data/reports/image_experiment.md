# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-18T21:25:55+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cpu** (xem TD-03: GPU Quadro P2000 sm_61 không dùng được)
- Nguồn dữ liệu: manifest D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer\data\processed\image_dataset_manifest.csv (1208 ảnh)
- Số lớp: **15**
- Thời gian huấn luyện: **713.6 s** cho 15 epoch (65.4, 43.3, 41.4, 47.4, 49.3, 43.2, 48.7, 40.3, 41.5, 43.6, 40.7, 40.8, 50.1, 70.3, 47.2 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 847 |
| validation | 181 |
| test | 180 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.7072** (epoch 13) |
| Loss tốt nhất trên validation | 0.9023 |
| **Accuracy trên tập test** | **0.7889** |
| Loss trên tập test | 0.7475 |
| Macro F1 trên tập test | 0.763 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_mi | 15 | 0.8 | 0.8 | 0.8 |
| banh_xeo | 6 | 0.6667 | 0.3333 | 0.4444 |
| bun_bo_hue | 7 | 0.6 | 0.8571 | 0.7059 |
| bun_cha | 7 | 0.8333 | 0.7143 | 0.7692 |
| com_chien | 15 | 0.9286 | 0.8667 | 0.8966 |
| com_tam | 11 | 1.0 | 0.9091 | 0.9524 |
| fried_chicken | 15 | 0.875 | 0.9333 | 0.9032 |
| goi_cuon | 7 | 0.75 | 0.8571 | 0.8 |
| hamburger | 15 | 0.8667 | 0.8667 | 0.8667 |
| pasta | 15 | 0.7273 | 0.5333 | 0.6154 |
| pho_bo | 7 | 0.4444 | 0.5714 | 0.5 |
| pizza | 15 | 0.6667 | 0.8 | 0.7273 |
| salad | 15 | 0.8235 | 0.9333 | 0.875 |
| steak | 15 | 0.75 | 0.8 | 0.7742 |
| sushi | 15 | 0.9167 | 0.7333 | 0.8148 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 2.5297 | 0.2149 | 2.3004 | 0.3591 | 65.4 |
| 2 | 2.0028 | 0.4699 | 1.7847 | 0.4917 | 43.3 |
| 3 | 1.5034 | 0.6009 | 1.4031 | 0.6133 | 41.4 |
| 4 | 1.1545 | 0.6753 | 1.1634 | 0.663 | 47.4 |
| 5 | 0.8995 | 0.7532 | 1.0441 | 0.6961 | 49.3 |
| 6 | 0.7917 | 0.778 | 1.0201 | 0.7072 | 43.2 |
| 7 | 0.676 | 0.8052 | 0.9814 | 0.6961 | 48.7 |
| 8 | 0.6015 | 0.8312 | 0.9516 | 0.6961 | 40.3 |
| 9 | 0.542 | 0.8607 | 0.9274 | 0.7017 | 41.5 |
| 10 | 0.4788 | 0.8654 | 0.9254 | 0.7072 | 43.6 |
| 11 | 0.4618 | 0.8914 | 0.9106 | 0.7072 | 40.7 |
| 12 | 0.4163 | 0.8926 | 0.9053 | 0.7072 | 40.8 |
| 13 | 0.4444 | 0.8808 | 0.9023 | 0.7072 | 50.1 |
| 14 | 0.4182 | 0.8902 | 0.901 | 0.7017 | 70.3 |
| 15 | 0.4137 | 0.8961 | 0.9002 | 0.7017 | 47.2 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
