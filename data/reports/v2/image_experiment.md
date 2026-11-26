# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-26T16:12:00+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cpu** (xem TD-03: GPU Quadro P2000 sm_61 không dùng được)
- Nguồn dữ liệu: manifest D:\Documents\BaoCao\TriTueNhanTao\AI-Nutrition-Analyzer\data\processed\image_dataset_manifest.csv (1711 ảnh)
- Số lớp: **29**
- Thời gian huấn luyện: **969.1 s** cho 15 epoch (72.3, 61.9, 72.6, 60.3, 67.5, 66.9, 67.8, 77.2, 64.9, 63.0, 81.4, 55.5, 49.4, 51.3, 56.7 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1198 |
| validation | 260 |
| test | 253 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.6538** (epoch 14) |
| Loss tốt nhất trên validation | 1.2930 |
| **Accuracy trên tập test** | **0.6640** |
| Loss trên tập test | 1.1090 |
| Macro F1 trên tập test | 0.7217 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_beo | 3 | 1.0 | 0.6667 | 0.8 |
| banh_chung | 5 | 0.8333 | 1.0 | 0.9091 |
| banh_cuon | 4 | 0.0 | 0.0 | - |
| banh_khot | 4 | 0.75 | 0.75 | 0.75 |
| banh_mi | 14 | 0.7273 | 0.5714 | 0.64 |
| banh_xeo | 6 | 0.5 | 0.3333 | 0.4 |
| bun_bo_hue | 8 | 0.625 | 0.625 | 0.625 |
| bun_cha | 10 | 0.7273 | 0.8 | 0.7619 |
| bun_dau_mam_tom | 2 | 1.0 | 1.0 | 1.0 |
| bun_rieu | 4 | - | 0.0 | - |
| bun_thit_nuong | 2 | - | 0.0 | - |
| canh_chua | 4 | 1.0 | 1.0 | 1.0 |
| cha_ca | 6 | 0.8 | 0.6667 | 0.7273 |
| com_chien | 15 | 0.6667 | 0.8 | 0.7273 |
| com_tam | 8 | 0.5556 | 0.625 | 0.5882 |
| fried_chicken | 15 | 0.7857 | 0.7333 | 0.7586 |
| goi_cuon | 6 | 0.375 | 0.5 | 0.4286 |
| hamburger | 15 | 0.6842 | 0.8667 | 0.7647 |
| hu_tieu | 5 | 1.0 | 1.0 | 1.0 |
| mi_quang | 6 | 0.75 | 1.0 | 0.8571 |
| nem_ran | 14 | 0.8 | 0.8571 | 0.8276 |
| pasta | 15 | 0.7273 | 0.5333 | 0.6154 |
| pho_bo | 13 | 0.5333 | 0.6154 | 0.5714 |
| pho_ga | 3 | - | 0.0 | - |
| pizza | 15 | 0.6875 | 0.7333 | 0.7097 |
| salad | 15 | 0.6667 | 0.9333 | 0.7778 |
| steak | 15 | 0.4706 | 0.5333 | 0.5 |
| sushi | 15 | 0.5625 | 0.6 | 0.5806 |
| xoi | 6 | 0.0 | 0.0 | - |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 3.1882 | 0.1461 | 2.9143 | 0.2538 | 72.3 |
| 2 | 2.5752 | 0.3706 | 2.3142 | 0.4231 | 61.9 |
| 3 | 1.9697 | 0.4917 | 1.9021 | 0.4885 | 72.6 |
| 4 | 1.564 | 0.5843 | 1.6811 | 0.5577 | 60.3 |
| 5 | 1.2869 | 0.6619 | 1.5412 | 0.5615 | 67.5 |
| 6 | 1.0826 | 0.6886 | 1.4635 | 0.5923 | 66.9 |
| 7 | 0.9574 | 0.7454 | 1.3949 | 0.6077 | 67.8 |
| 8 | 0.8305 | 0.7938 | 1.3688 | 0.6077 | 77.2 |
| 9 | 0.7591 | 0.7871 | 1.3266 | 0.6308 | 64.9 |
| 10 | 0.6895 | 0.8255 | 1.316 | 0.6423 | 63.0 |
| 11 | 0.6661 | 0.8239 | 1.3026 | 0.6462 | 81.4 |
| 12 | 0.6163 | 0.8381 | 1.2952 | 0.65 | 55.5 |
| 13 | 0.6 | 0.8481 | 1.2943 | 0.6538 | 49.4 |
| 14 | 0.6153 | 0.8356 | 1.293 | 0.6538 | 51.3 |
| 15 | 0.6016 | 0.8406 | 1.2942 | 0.65 | 56.7 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
