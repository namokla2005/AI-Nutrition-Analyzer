# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-26T18:51:45+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cpu** (xem TD-03: GPU Quadro P2000 sm_61 không dùng được)
- Nguồn dữ liệu: manifest data\processed\image_dataset_manifest_v4.csv (1579 ảnh)
- Số lớp: **22**
- Thời gian huấn luyện: **1437.6 s** cho 12 epoch (166.7, 118.3, 112.8, 101.6, 116.8, 115.7, 121.3, 111.8, 117.8, 121.0, 113.7, 119.6 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1105 |
| validation | 240 |
| test | 234 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.6958** (epoch 8) |
| Loss tốt nhất trên validation | 1.1297 |
| **Accuracy trên tập test** | **0.6624** |
| Loss trên tập test | 1.1174 |
| Macro F1 trên tập test | 0.6326 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_chung | 5 | 0.75 | 0.6 | 0.6667 |
| banh_cuon | 7 | 1.0 | 0.4286 | 0.6 |
| banh_mi | 14 | 0.7143 | 0.7143 | 0.7143 |
| banh_xeo | 6 | 0.6 | 0.5 | 0.5455 |
| bun_bo_hue | 8 | 0.8333 | 0.625 | 0.7143 |
| bun_cha | 10 | 0.5385 | 0.7 | 0.6087 |
| cha_ca | 6 | 1.0 | 0.5 | 0.6667 |
| com_chien | 15 | 0.75 | 0.8 | 0.7742 |
| com_tam | 8 | 0.8 | 0.5 | 0.6154 |
| fried_chicken | 15 | 0.7 | 0.9333 | 0.8 |
| goi_cuon | 6 | 0.4444 | 0.6667 | 0.5333 |
| hamburger | 15 | 0.6875 | 0.7333 | 0.7097 |
| hu_tieu | 6 | 0.4286 | 0.5 | 0.4615 |
| mi_quang | 6 | 0.5 | 0.6667 | 0.5714 |
| nem_ran | 14 | 0.6471 | 0.7857 | 0.7097 |
| pasta | 15 | 0.5833 | 0.4667 | 0.5185 |
| pho_bo | 13 | 0.6429 | 0.6923 | 0.6667 |
| pizza | 15 | 0.625 | 0.6667 | 0.6452 |
| salad | 15 | 0.9167 | 0.7333 | 0.8148 |
| steak | 15 | 0.5556 | 0.6667 | 0.6061 |
| sushi | 15 | 0.7143 | 0.6667 | 0.6897 |
| xoi | 5 | 0.5 | 0.2 | 0.2857 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 2.9114 | 0.1692 | 2.5723 | 0.3667 | 166.7 |
| 2 | 2.3001 | 0.4371 | 1.9762 | 0.4667 | 118.3 |
| 3 | 1.7243 | 0.5421 | 1.5729 | 0.5542 | 112.8 |
| 4 | 1.3917 | 0.6226 | 1.3893 | 0.6208 | 101.6 |
| 5 | 1.1277 | 0.6787 | 1.2506 | 0.6583 | 116.8 |
| 6 | 0.935 | 0.7529 | 1.1971 | 0.6625 | 115.7 |
| 7 | 0.7892 | 0.7928 | 1.163 | 0.6792 | 121.3 |
| 8 | 0.7273 | 0.8009 | 1.1297 | 0.6958 | 111.8 |
| 9 | 0.637 | 0.8407 | 1.0948 | 0.6917 | 117.8 |
| 10 | 0.6447 | 0.829 | 1.0878 | 0.6875 | 121.0 |
| 11 | 0.6091 | 0.8353 | 1.0767 | 0.6917 | 113.7 |
| 12 | 0.5556 | 0.8552 | 1.0781 | 0.6833 | 119.6 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
