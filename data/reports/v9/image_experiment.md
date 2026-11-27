# BÁO CÁO THỰC NGHIỆM – NHẬN DIỆN MÓN ĂN BẰNG ẢNH

- Thời điểm chạy (UTC): 2026-11-27T19:45:55+00:00
- Kiến trúc: MobileNetV3-Small (transfer learning từ ImageNet: có)
- Thiết bị: **cuda** (GPU Quadro P2000 · Pascal sm_61 — dùng bản PyTorch cu121 vì các bản CUDA mới hơn đã bỏ Pascal)
- Nguồn dữ liệu: manifest data\processed\image_dataset_manifest_v9.csv (2524 ảnh)
- Số lớp: **44**
- Thời gian huấn luyện: **899.4 s** cho 24 epoch (38.4, 39.4, 37.1, 37.7, 37.5, 37.5, 36.1, 36.7, 37.4, 37.4, 38.3, 38.2, 37.4, 37.1, 37.8, 35.8, 36.3, 36.8, 37.9, 37.3, 38.0, 37.5, 37.7, 37.0 giây/epoch)

## 1. Kích thước tập dữ liệu

| Tập | Số ảnh |
|---|---|
| train | 1768 |
| validation | 383 |
| test | 373 |

## 2. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy tốt nhất trên validation | **0.6893** (epoch 16) |
| Loss tốt nhất trên validation | 1.3570 |
| **Accuracy trên tập test** | **0.7024** |
| Loss trên tập test | 1.2927 |
| Macro F1 trên tập test | 0.6745 |

## 3. Chỉ số theo từng lớp (tập test)

| Lớp | Số mẫu | Precision | Recall | F1 |
|---|---|---|---|---|
| banh_bao | 5 | 1.0 | 0.6 | 0.75 |
| banh_beo | 6 | 0.8333 | 0.8333 | 0.8333 |
| banh_canh | 7 | 0.75 | 0.8571 | 0.8 |
| banh_chung | 5 | 0.6667 | 0.4 | 0.5 |
| banh_cuon | 7 | 0.8 | 0.5714 | 0.6667 |
| banh_da_cua | 5 | 0.6667 | 0.8 | 0.7273 |
| banh_khot | 7 | 0.6667 | 0.8571 | 0.75 |
| banh_mi | 14 | 0.5556 | 0.7143 | 0.625 |
| banh_tom | 7 | 1.0 | 0.7143 | 0.8333 |
| banh_trang_nuong | 3 | 0.2 | 0.3333 | 0.25 |
| banh_uot | 8 | 0.875 | 0.875 | 0.875 |
| banh_xeo | 6 | 0.8 | 0.6667 | 0.7273 |
| bo_kho | 8 | 0.75 | 0.75 | 0.75 |
| bun_bo_hue | 8 | 0.4545 | 0.625 | 0.5263 |
| bun_cha | 10 | 0.7143 | 0.5 | 0.5882 |
| bun_dau_mam_tom | 7 | 0.875 | 1.0 | 0.9333 |
| bun_rieu | 5 | 0.3333 | 0.2 | 0.25 |
| bun_thit_nuong | 6 | 0.5714 | 0.6667 | 0.6154 |
| ca_kho_to | 6 | 0.8333 | 0.8333 | 0.8333 |
| canh_chua | 6 | 0.3333 | 0.1667 | 0.2222 |
| cha_ca | 6 | 0.5714 | 0.6667 | 0.6154 |
| chao | 7 | 0.8 | 0.5714 | 0.6667 |
| che_ba_mau | 6 | 1.0 | 0.6667 | 0.8 |
| com_chien | 15 | 0.6 | 0.8 | 0.6857 |
| com_ga | 5 | 0.5 | 0.6 | 0.5455 |
| com_tam | 8 | 0.5714 | 0.5 | 0.5333 |
| fried_chicken | 15 | 0.9231 | 0.8 | 0.8571 |
| goi_cuon | 6 | 0.7143 | 0.8333 | 0.7692 |
| goi_ga | 6 | 0.6667 | 0.3333 | 0.4444 |
| hamburger | 15 | 0.7647 | 0.8667 | 0.8125 |
| hu_tieu | 6 | 0.5 | 0.5 | 0.5 |
| mi_quang | 6 | 0.6 | 1.0 | 0.75 |
| mi_xao | 6 | 0.8571 | 1.0 | 0.9231 |
| nem_ran | 14 | 0.9286 | 0.9286 | 0.9286 |
| pasta | 15 | 0.7273 | 0.5333 | 0.6154 |
| pho_bo | 13 | 0.7 | 0.5385 | 0.6087 |
| pho_ga | 5 | 0.75 | 0.6 | 0.6667 |
| pizza | 15 | 0.6471 | 0.7333 | 0.6875 |
| salad | 15 | 0.5652 | 0.8667 | 0.6842 |
| steak | 15 | 0.7333 | 0.7333 | 0.7333 |
| sushi | 15 | 0.8333 | 0.6667 | 0.7407 |
| thit_kho_trung | 9 | 0.8889 | 0.8889 | 0.8889 |
| xoi | 5 | 0.25 | 0.2 | 0.2222 |
| xoi_xeo | 9 | 1.0 | 0.8889 | 0.9412 |

## 4. Lịch sử huấn luyện

| Epoch | Train loss | Train acc | Val loss | Val acc | Giây |
|---|---|---|---|---|---|
| 1 | 3.65 | 0.0871 | 3.3706 | 0.2376 | 38.4 |
| 2 | 3.0019 | 0.3343 | 2.6601 | 0.389 | 39.4 |
| 3 | 2.1887 | 0.4853 | 2.1006 | 0.4856 | 37.1 |
| 4 | 1.6391 | 0.6114 | 1.765 | 0.5535 | 37.7 |
| 5 | 1.3045 | 0.6578 | 1.615 | 0.5979 | 37.5 |
| 6 | 1.0725 | 0.7149 | 1.496 | 0.6188 | 37.5 |
| 7 | 0.8979 | 0.746 | 1.4245 | 0.6475 | 36.1 |
| 8 | 0.7973 | 0.763 | 1.4345 | 0.6371 | 36.7 |
| 9 | 0.6609 | 0.8105 | 1.3603 | 0.6658 | 37.4 |
| 10 | 0.5983 | 0.8314 | 1.3707 | 0.6632 | 37.4 |
| 11 | 0.4777 | 0.866 | 1.3628 | 0.6684 | 38.3 |
| 12 | 0.446 | 0.8761 | 1.3475 | 0.6867 | 38.2 |
| 13 | 0.3773 | 0.8954 | 1.3799 | 0.6684 | 37.4 |
| 14 | 0.3578 | 0.8988 | 1.341 | 0.6841 | 37.1 |
| 15 | 0.3095 | 0.9157 | 1.3417 | 0.6867 | 37.8 |
| 16 | 0.2721 | 0.9236 | 1.357 | 0.6893 | 35.8 |
| 17 | 0.2701 | 0.9282 | 1.3667 | 0.6841 | 36.3 |
| 18 | 0.2465 | 0.9299 | 1.3993 | 0.6736 | 36.8 |
| 19 | 0.2227 | 0.944 | 1.39 | 0.6762 | 37.9 |
| 20 | 0.1941 | 0.9491 | 1.4401 | 0.6684 | 37.3 |
| 21 | 0.1915 | 0.9434 | 1.3995 | 0.6841 | 38.0 |
| 22 | 0.171 | 0.9564 | 1.4105 | 0.6867 | 37.5 |
| 23 | 0.182 | 0.948 | 1.4169 | 0.6841 | 37.7 |
| 24 | 0.161 | 0.9553 | 1.4206 | 0.6893 | 37.0 |

## 5. Biểu đồ

- data/reports/figures/image_training_curves.png, image_confusion_matrix.png

## 6. Ghi chú trung thực về kết quả

- Toàn bộ số liệu trong báo cáo này do chính lần chạy trên sinh ra, không nhập tay.
- Độ chính xác phụ thuộc hoàn toàn vào dữ liệu đã huấn luyện. Số lớp thực tế có thể ít hơn 15 lớp mục tiêu của đề bài nếu thiếu ảnh (xem data/reports/image_dataset_report.md).
- Food-101 chỉ phủ chính xác 4/15 lớp món ăn mục tiêu; ảnh món Việt Nam phải thu thập riêng từ Wikimedia Commons (xem data/reports/sourcing_report.md).
- Không được trích dẫn kết quả này cho một lớp chưa từng có ảnh huấn luyện.
