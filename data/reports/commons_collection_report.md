# Báo cáo bổ sung và duyệt ảnh Commons 2026-11-27

- Sao lưu trước khi chạy: `data/reports/backups/*_20261127_005020.*`.
- Kiểm đếm bản sao trước chạy cho thấy provenance có 932 dòng / 21 lớp Commons (không phải 29 lớp như cảnh báo ban đầu); 8 lớp Food-101 trong manifest không có dòng Wikimedia Commons.
- Không huấn luyện model; không dựng lại hay sửa manifest huấn luyện.

| Lớp | Manifest trước | Tải mới | Loại qua duyệt mắt | Ảnh sạch trên đĩa sau | ≥35 |
|---|---:|---:|---:|---:|:---:|
| `pho_ga` | 21 | 39 | 50 | 10 | Không |
| `banh_cuon` | 30 | 30 | 13 | 47 | Có |
| `hu_tieu` | 32 | 10 | 3 | 39 | Có |
| `canh_chua` | 28 | 0 | 23 | 5 | Không |
| `banh_khot` | 25 | 9 | 26 | 8 | Không |
| `bun_rieu` | 26 | 0 | 11 | 15 | Không |
| `banh_beo` | 21 | 0 | 9 | 12 | Không |
| `bun_thit_nuong` | 15 | 0 | 3 | 12 | Không |
| `bun_dau_mam_tom` | 12 | 1 | 3 | 10 | Không |

- Tổng ảnh mới có metadata: **89**.
- Tổng ảnh đánh SAI và chuyển sang `_rejected` trong đợt duyệt: **141**.
- Chi tiết ĐÚNG/SAI từng ảnh: `commons_visual_review_20261127_005020.csv/.json`.
- Danh sách ảnh tải mới (page_id, URL, giấy phép): `commons_downloaded_20261127_005020.csv/.json`.

## Lý do loại theo lớp

### pho_ga
- 16: đàn gà
- 4: gà sống
- 3: chuồng gà
- 3: mâm món gà, không phải phở
- 2: gà nguyên liệu, không phải phở
- 2: cảnh phục vụ/quầy, không thấy bát phở
- 2: gà quay/nướng, không phải phở
- 1: đĩa rau/thịt, không phải bát phở gà
- 1: cảnh bàn/quán, món không rõ
- 1: người và gà nguyên con, không phải phở
- 1: biển hiệu/mặt tiền quán
- 1: chuồng/đàn gà
- 1: cơm/đùi gà, không phải phở
- 1: món trộn, không rõ là phở gà
- 1: gà luộc/nước gà, không phải phở
- 1: gà và nước chấm, không phải phở
- 1: gà luộc, không phải phở
- 1: món gà, không phải phở
- 1: món gà chiên, không phải phở
- 1: gà chặt, không phải phở
- 1: chế biến gà, không phải phở
- 1: bát mì/súp không đủ rõ là phở gà
- 1: bàn nhiều món, không xác định phở gà
- 1: gà nướng, không phải phở
- 1: đĩa thức ăn, không phải bát phở
### banh_cuon
- 2: cảnh chợ/người bán
- 2: cảnh chế biến, không phải món hoàn chỉnh
- 1: thực phẩm đóng gói/không phải bánh cuốn
- 1: đĩa giò/chả, không phải bánh cuốn
- 1: món khác/không đủ rõ là bánh cuốn
- 1: món rau trộn khác
- 1: mặt tiền/biển hiệu quán
- 1: món cuốn rau khác
- 1: sản phẩm đóng gói
- 1: thịt/giò cuộn, không phải bánh cuốn
- 1: bề mặt/vật thể không phải món ăn
### hu_tieu
- 1: canh rau, không thấy sợi hủ tiếu
- 1: ảnh con chó
- 1: món tôm/sốt, không thấy hủ tiếu
### canh_chua
- 4: cảnh vườn
- 3: cây cảnh
- 3: tranh/bản đồ
- 2: đường phố
- 2: bia/đá trong vườn
- 1: cảnh hồ/công trình
- 1: cảnh chùa/hồ
- 1: cảnh vườn/chùa
- 1: cảnh sân/vườn
- 1: cảnh chùa/vườn
- 1: cảnh cây/vườn
- 1: cảnh đêm công trình
- 1: cảnh chùa
- 1: cảnh công trình
### banh_khot
- 13: bánh căn, không phải bánh khọt
- 2: người đang chế biến
- 2: nguyên liệu sợi, không phải bánh khọt
- 1: tranh vẽ
- 1: chảo đang chế biến, chưa phải món hoàn chỉnh
- 1: cảnh người bán/chợ
- 1: khay đang chế biến, chưa phải món hoàn chỉnh
- 1: đang chiên nguyên liệu, món không rõ
- 1: món khác/không đủ rõ là bánh khọt
- 1: bánh căn/bàn ăn, không phải bánh khọt
- 1: bát nước chấm, không phải món bánh khọt
- 1: rổ rau, không phải món bánh khọt
### bun_rieu
- 2: món cơm/canh khác
- 2: ảnh dàn dựng với sách/sản phẩm
- 2: món cà ri/rau củ, không phải bún riêu
- 1: món cơm/cháo, không rõ là bún riêu
- 1: bàn nhiều món, không rõ bún riêu
- 1: món hầm, không thấy bún
- 1: biển hiệu/quầy hàng
- 1: món cà ri, không phải bún riêu
### banh_beo
- 1: khay dim sum/món khác
- 1: gỏi cuốn, không phải bánh bèo
- 1: bánh/món áp chảo khác
- 1: món trộn khác
- 1: bánh vàng/món khác
- 1: hộp thức ăn/món chưa rõ
- 1: tranh vẽ
- 1: nồi nguyên liệu/món khác
- 1: cảnh người/quán
### bun_thit_nuong
- 3: thịt nướng riêng, không có bún
### bun_dau_mam_tom
- 2: bát mắm tôm riêng
- 1: mắm tôm riêng

## Lệnh đã chạy nguyên văn

```bash
"D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/Scripts/python.exe" scripts/collect_vn_images.py --help
```
```bash
"D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/Scripts/python.exe" scripts/collect_vn_images.py --mode search -n 60 --scan-limit 300 "pho_ga=phở gà|pho ga|gà ta|mì gà" "banh_cuon=bánh cuốn|bánh ướt|bánh cuốn tráng|bánh cuốn nóng" "hu_tieu=hủ tiếu|hủ tíu|hủ tiếu nam vang|hủ tiếu mì" "canh_chua=canh chua|cá nấu canh chua|canh chua tôm" "banh_khot=bánh khọt|bánh căn|bánh khọt tôm" "bun_rieu=bún riêu|riêu cua|bún riêu cua" "banh_beo=bánh bèo|bánh bèo chén|bánh đập" "bun_thit_nuong=bún thịt nướng|thịt nướng bún|bún thịt" "bun_dau_mam_tom=bún đậu mắm tôm|mắm tôm|bún đậu"
```
```bash
"D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/Scripts/python.exe" scripts/collect_vn_images.py --mode search -n 60 --scan-limit 300 "hu_tieu=hủ tiếu|hủ tíu|hủ tiếu nam vang|hủ tiếu mì"
```
```bash
"D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/.venv/Scripts/python.exe" "C:/Users/Nam/AppData/Local/hermes/cache/scratch/apply_commons_visual_review.py"
```
```bash
mkdir -p data/raw/images/_rejected/hu_tieu/visual_review_retry_20261127_005020 && for id in 121668290 53463830 81671438; do for f in data/raw/images/hu_tieu/commons_${id}.*; do [ -e "$f" ] && mv "$f" data/raw/images/_rejected/hu_tieu/visual_review_retry_20261127_005020/; done; done
```
