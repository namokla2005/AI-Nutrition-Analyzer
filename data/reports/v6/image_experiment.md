# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-26T21:08:38+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cuda** (GPU Quadro P2000 · Pascal sm_61 — dùng bản PyTorch cu121 vì các bản CUDA mới hơn đã bỏ Pascal)
- Nguồn dữ liệu: manifest data\processed\image_dataset_manifest_v6.csv (1688 ảnh)
- Số lớp: **25**
- Thời gian huấn luyện: **483.8 s** cho 20 epoch (26.3, 25.7, 25.2, 25.1, 24.7, 25.5, 24.7, 26.9, 22.6, 22.0, 24.5, 24.6, 23.0, 22.9, 23.1, 23.7, 22.8, 23.3, 23.0, 23.1 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1181 |
| validation | 257 |
| test | 250 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.7354** (epoch 20) |
| Loss tốt nhất trên validation | 1.0578 |
| **Accuracy trên tập test** | **0.6760** |
| Loss trên tập test | 1.0852 |
| Macro F1 trên tập test | 0.6589 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_chung | 5 | 0.7143 | 1.0 | 0.8333 |
| banh_cuon | 7 | 1.0 | 0.2857 | 0.4444 |
| banh_mi | 14 | 0.75 | 0.8571 | 0.8 |
| banh_xeo | 6 | 1.0 | 0.6667 | 0.8 |
| bun_bo_hue | 8 | 0.5556 | 0.625 | 0.5882 |
| bun_cha | 10 | 0.7273 | 0.8 | 0.7619 |
| bun_rieu | 5 | 0.6667 | 0.4 | 0.5 |
| bun_thit_nuong | 6 | 0.2 | 0.3333 | 0.25 |
| cha_ca | 6 | 0.6 | 0.5 | 0.5455 |
| com_chien | 15 | 0.75 | 0.8 | 0.7742 |
| com_tam | 8 | 0.7143 | 0.625 | 0.6667 |
| fried_chicken | 15 | 0.7647 | 0.8667 | 0.8125 |
| goi_cuon | 6 | 0.6667 | 0.6667 | 0.6667 |
| hamburger | 15 | 0.8125 | 0.8667 | 0.8387 |
| hu_tieu | 6 | 0.0 | 0.0 | - |
| mi_quang | 6 | 0.5 | 0.5 | 0.5 |
| nem_ran | 14 | 0.9167 | 0.7857 | 0.8462 |
| pasta | 15 | 0.5455 | 0.4 | 0.4615 |
| pho_bo | 13 | 0.5385 | 0.5385 | 0.5385 |
| pho_ga | 5 | 0.375 | 0.6 | 0.4615 |
| pizza | 15 | 0.6667 | 0.8 | 0.7273 |
| salad | 15 | 0.75 | 0.8 | 0.7742 |
| steak | 15 | 0.8462 | 0.7333 | 0.7857 |
| sushi | 15 | 0.6471 | 0.7333 | 0.6875 |
| xoi | 5 | 1.0 | 0.6 | 0.75 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 3.0375 | 0.1626 | 2.7433 | 0.2685 | 26.3 |
| 2 | 2.3895 | 0.3971 | 2.1293 | 0.4358 | 25.7 |
| 3 | 1.8222 | 0.5191 | 1.7386 | 0.5331 | 25.2 |
| 4 | 1.4559 | 0.6088 | 1.5143 | 0.6109 | 25.1 |
| 5 | 1.157 | 0.7062 | 1.3484 | 0.642 | 24.7 |
| 6 | 0.9788 | 0.7257 | 1.2509 | 0.6693 | 25.5 |
| 7 | 0.829 | 0.7858 | 1.1766 | 0.6926 | 24.7 |
| 8 | 0.7317 | 0.7985 | 1.1495 | 0.6887 | 26.9 |
| 9 | 0.6161 | 0.845 | 1.11 | 0.716 | 22.6 |
| 10 | 0.5738 | 0.8442 | 1.0831 | 0.7121 | 22.0 |
| 11 | 0.535 | 0.8535 | 1.0892 | 0.7121 | 24.5 |
| 12 | 0.4772 | 0.8781 | 1.0688 | 0.7276 | 24.6 |
| 13 | 0.4225 | 0.9001 | 1.0685 | 0.7198 | 23.0 |
| 14 | 0.3984 | 0.9009 | 1.0611 | 0.7276 | 22.9 |
| 15 | 0.4055 | 0.9018 | 1.0619 | 0.7198 | 23.1 |
| 16 | 0.3764 | 0.9009 | 1.0554 | 0.7276 | 23.7 |
| 17 | 0.3462 | 0.9187 | 1.0555 | 0.7315 | 22.8 |
| 18 | 0.3399 | 0.9213 | 1.0562 | 0.7315 | 23.3 |
| 19 | 0.3648 | 0.9162 | 1.0554 | 0.7276 | 23.0 |
| 20 | 0.3522 | 0.9128 | 1.0578 | 0.7354 | 23.1 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
