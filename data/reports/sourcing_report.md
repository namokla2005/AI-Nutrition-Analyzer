# Báo cáo xác minh nguồn dữ liệu dinh dưỡng và ảnh món ăn

**Thời điểm kiểm tra HTTP:** 2026-11-19 03:12:59 +07:00  
**Phạm vi:** nguồn tải hợp pháp, không vượt đăng nhập/paywall/CAPTCHA; mọi số đếm Commons là **tệp thành viên trực tiếp** của category tại thời điểm kiểm tra, không đệ quy qua subcategory.

## 1. Bảng thành phần thực phẩm Việt Nam

### 1.1. Bảng của Viện Dinh dưỡng Quốc gia — bản PDF do FAO lưu trữ

Nguồn tải trực tiếp đã xác minh:

- URL: `https://www.fao.org/fileadmin/templates/food_composition/documents/pdf/VTN_FCT_2007.pdf`
- `HEAD`: **HTTP 200**, `Content-Type: application/pdf`, `Content-Length: 4722438`.
- `GET`: **HTTP 200**, đã đọc đủ **4.722.438 byte**; chữ ký đầu tệp là `%PDF-1.6`.
- Nội dung bìa trích nguyên văn: “**BỘ Y TẾ — VIỆN DINH DƯỠNG — BẢNG THÀNH PHẦN THỰC PHẨM VIỆT NAM — VIETNAMESE FOOD COMPOSITION TABLE — NHÀ XUẤT BẢN Y HỌC, 2007**”.[1]
- Tài liệu tự mô tả: “**Bảng thành phần thực phẩm Việt Nam bao gồm 526 thực phẩm được trình bày theo 14 nhóm, cung cấp số liệu của 86 chất dinh dưỡng**” và số liệu được trình bày trong “**100 gam thực phẩm ăn được**”.[1]

Đây là nguồn tải hợp lệ từ tên miền FAO, không yêu cầu đăng nhập và đáp ứng yêu cầu có tệp PDF thực, thay vì chỉ có trang HTML. Không dùng các bản sao Scribd/Academia hoặc bản mirror không rõ quyền.

**Quyền sử dụng:** tìm kiếm toàn văn PDF không thấy chuỗi `copyright`, `license/licence`, `bản quyền` hay điều khoản tái sử dụng. Vì vậy, việc máy chủ cho tải PDF **không được diễn giải thành giấy phép tái phân phối hoặc tái xuất bản dữ liệu**. Có thể dùng làm tài liệu tham chiếu/nhập liệu có dẫn nguồn cho dự án học thuật; nếu dự định công bố lại toàn bộ bảng hoặc dùng thương mại, cần xin phép Viện Dinh dưỡng/Nhà xuất bản Y học hoặc FAO.

### 1.2. ASEAN Food Composition Database — nguồn ASEANFOODS/INFOODS có thực phẩm Việt Nam

Trang chính thức của Institute of Nutrition, Mahidol University trả **HTTP 200**, dài **4.376 byte**, và liên kết trực tiếp tới PDF.[2]

- Trang: `https://inmu.mahidol.ac.th/aseanfoods/composition_data.html`
- PDF: `https://inmu.mahidol.ac.th/aseanfoods/doc/OnlineASEAN_FCD_V1_2014.pdf`
- PDF `HEAD`/`GET`: **HTTP 200**, `Content-Type: application/pdf`, `Content-Length: 907493`; đã đọc đủ **907.493 byte**.
- Tên tài liệu nguyên văn: “**ASEAN Food Composition Database — Electronic version 1, February, 2014 — Institute of Nutrition, Mahidol University, THAILAND — ASEANFOODS Regional Centre and INFOODS Regional Database Centre**”.[3]

Bằng chứng tài liệu có dữ liệu Việt Nam:

> “In 1996, with technical and financial support from UNU/INFOODS ... 20 participants from 6 countries, namely Indonesia, Malaysia, Philippines, Singapore, Thailand and **Vietnam** ...”[3]
>
> “Record identifiers beginning with ID, MY, PH, SG, TH and **VN** were original records from those countries ...”[3]
>
> Ví dụ dòng dữ liệu: `AAA61 | MYA24, VNA8 | Rice, flour, glutinous, white` và `AAB1 | VNB40, PHB025 | Arrowroot, flour`.[3]

Lưu ý phạm vi: phần giới thiệu nói bản in đầu tiên có khoảng 1.740 thực phẩm; chính PDF ghi rõ bản điện tử đang phát hành chứa **616 thực phẩm** gồm dữ liệu ASEAN tổng hợp và dữ liệu Thái riêng. Không được gán nhầm con số 1.740/1.746 cho số dòng thực phẩm trong PDF điện tử này.[3]

**Điều khoản tái sử dụng, trích nguyên văn từ PDF:**[3]

> “**All rights reserved. ASEANFOODS encourages the use and dissemination of this online ASEAN Food Composition Database. Noncommercial users will be authorised free of charge, provided that appropriate acknowledgement of ASEANFOODS as the source and copyright holder is given. Reproduction for resale or other commercial uses including educational purposes, may incur fees. Applications for permission to reproduce or disseminate ASEANFOODS copyright materials ... should be addressed ... to the Director of the Institute of Nutrition, Mahidol University ... or to the Coordinators of ASEANFOODS.**”

Kết luận quyền: dự án phi thương mại có thể sử dụng miễn phí nếu ghi nhận ASEANFOODS đúng yêu cầu; tái bán, dùng thương mại, hoặc trường hợp “commercial uses including educational purposes” phải hỏi quyền. Không gắn nhãn nguồn này là open data/CC.

## 2. Food-101 trên Hugging Face

### 2.1. Repo, split và bằng chứng API

- Repo chính xác: `https://huggingface.co/datasets/ethz/food101`.
- API cây tệp: `https://huggingface.co/api/datasets/ethz/food101/tree/main/data` trả **HTTP 200** và liệt kê 8 shard train + 3 shard validation.[4]
- Dataset viewer train trả **HTTP 200**, raw JSON có `"num_rows_total":75750`.[6]
- Dataset viewer validation trả **HTTP 200**, raw JSON có `"num_rows_total":25250`.[7]
- Manifest parquet trả **HTTP 200** và cung cấp URL alias `refs/convert/parquet`, tên tệp và kích thước từng shard.[5]

Các URL `resolve/main/data/...` dưới đây đều được kiểm tra bằng `HEAD`: URL ổn định trả **302**, sau khi theo redirect trả **200**, và `Content-Length` cuối khớp đúng trường `size` của API cây repo.

| Split | URL ổn định đã kiểm tra | Alias do `/parquet` trả về | Byte | HTTP quan sát |
|---|---|---|---:|---|
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00000-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet` | 489.582.959 | 302 → 200 |
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00001-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0001.parquet` | 464.225.341 | 302 → 200 |
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00002-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0002.parquet` | 472.211.726 | 302 → 200 |
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00003-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0003.parquet` | 463.644.865 | 302 → 200 |
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00004-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0004.parquet` | 475.091.267 | 302 → 200 |
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00005-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0005.parquet` | 469.875.468 | 302 → 200 |
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00006-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0006.parquet` | 478.240.948 | 302 → 200 |
| train | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/train-00007-of-00008.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/train/0007.parquet` | 485.648.421 | 302 → 200 |
| validation | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/validation-00000-of-00003.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/validation/0000.parquet` | 422.634.283 | 302 → 200 |
| validation | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/validation-00001-of-00003.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/validation/0001.parquet` | 413.147.844 | 302 → 200 |
| validation | `https://huggingface.co/datasets/ethz/food101/resolve/main/data/validation-00002-of-00003.parquet` | `https://huggingface.co/datasets/ethz/food101/resolve/refs%2Fconvert%2Fparquet/default/validation/0002.parquet` | 425.669.186 | 302 → 200 |

Tổng kích thước đã cộng từ các shard: **train 3.798.520.995 byte**, **validation 1.261.451.313 byte**, toàn bộ **5.059.972.308 byte**. URL tarball cũ `http://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/food-101.tar.gz` được kiểm tra lại và kết thúc ở HTTPS với **HTTP 404**; không dùng đường này.

### 2.2. Danh sách 101 lớp có thẩm quyền

Nguồn có thẩm quyền là schema `ClassLabel.names` do dataset viewer trả về và mapping `dataset_info.features.label.class_label.names` trong dataset card của chính repo.[6][8] Trích nguyên văn danh sách, giữ nguyên chữ thường và dấu gạch dưới:

```text
["apple_pie", "baby_back_ribs", "baklava", "beef_carpaccio", "beef_tartare", "beet_salad", "beignets", "bibimbap", "bread_pudding", "breakfast_burrito", "bruschetta", "caesar_salad", "cannoli", "caprese_salad", "carrot_cake", "ceviche", "cheesecake", "cheese_plate", "chicken_curry", "chicken_quesadilla", "chicken_wings", "chocolate_cake", "chocolate_mousse", "churros", "clam_chowder", "club_sandwich", "crab_cakes", "creme_brulee", "croque_madame", "cup_cakes", "deviled_eggs", "donuts", "dumplings", "edamame", "eggs_benedict", "escargots", "falafel", "filet_mignon", "fish_and_chips", "foie_gras", "french_fries", "french_onion_soup", "french_toast", "fried_calamari", "fried_rice", "frozen_yogurt", "garlic_bread", "gnocchi", "greek_salad", "grilled_cheese_sandwich", "grilled_salmon", "guacamole", "gyoza", "hamburger", "hot_and_sour_soup", "hot_dog", "huevos_rancheros", "hummus", "ice_cream", "lasagna", "lobster_bisque", "lobster_roll_sandwich", "macaroni_and_cheese", "macarons", "miso_soup", "mussels", "nachos", "omelette", "onion_rings", "oysters", "pad_thai", "paella", "pancakes", "panna_cotta", "peking_duck", "pho", "pizza", "pork_chop", "poutine", "prime_rib", "pulled_pork_sandwich", "ramen", "ravioli", "red_velvet_cake", "risotto", "samosa", "sashimi", "scallops", "seaweed_salad", "shrimp_and_grits", "spaghetti_bolognese", "spaghetti_carbonara", "spring_rolls", "steak", "strawberry_shortcake", "sushi", "tacos", "takoyaki", "tiramisu", "tuna_tartare", "waffles"]
```

### 2.3. Đối chiếu 15 lớp đích

“Chính xác” dưới đây nghĩa là có đúng khái niệm lớp món ăn trong danh sách Food-101; tên kỹ thuật thật vẫn được ghi nguyên văn.

| Lớp đích | Kết luận | Lớp Food-101 và khác biệt |
|---|---|---|
| phở bò | **Phủ gần đúng** | `pho` — lớp rộng là phở, không ràng buộc riêng phở bò. |
| bún bò Huế | **Không phủ** | Không có lớp tương ứng. |
| bánh mì | **Không phủ** | Không có `banh_mi`; `club_sandwich`/`pulled_pork_sandwich` là món khác. |
| cơm tấm | **Không phủ** | Không có lớp tương ứng. |
| gỏi cuốn | **Phủ gần đúng** | `spring_rolls` — tên rộng, không tách gỏi cuốn tươi Việt Nam khỏi các loại spring roll khác. |
| bánh xèo | **Không phủ** | Không có lớp tương ứng; `pancakes` không phải bánh xèo Việt Nam. |
| bún chả | **Không phủ** | Không có lớp tương ứng. |
| cơm chiên | **Phủ gần đúng** | `fried_rice` — tương đương loại món tổng quát, nhưng nhãn không đặc tả biến thể Việt Nam. |
| Pizza | **Phủ chính xác** | `pizza` (tên kỹ thuật viết thường). |
| Hamburger | **Phủ chính xác** | `hamburger` (tên kỹ thuật viết thường). |
| Sushi | **Phủ chính xác** | `sushi` (tên kỹ thuật viết thường). |
| Salad | **Phủ gần đúng** | Không có `salad` chung; có `beet_salad`, `caesar_salad`, `caprese_salad`, `greek_salad`, `seaweed_salad`. |
| Pasta | **Phủ gần đúng** | Không có `pasta` chung; có các lớp cụ thể như `gnocchi`, `lasagna`, `ravioli`, `spaghetti_bolognese`, `spaghetti_carbonara`. |
| Steak | **Phủ chính xác** | `steak` (tên kỹ thuật viết thường). |
| Fried Chicken | **Phủ gần đúng, yếu** | `chicken_wings` chỉ phủ phần giao khi cánh gà được chiên; không có lớp `fried_chicken` và `chicken_wings` hẹp hơn theo phần thịt, không bảo đảm phương pháp chiên. |

### 2.4. Giấy phép Food-101

Dataset card khai báo metadata `license: unknown` và chép điều khoản:[8]

> “**The Food-101 data set consists of images from Foodspotting [1] which are not property of the Federal Institute of Technology Zurich (ETHZ). Any use beyond scientific fair use must be negociated with the respective picture owners according to the Foodspotting terms of use.**”

Vì vậy, tuyến Hugging Face đã xác minh được về mặt kỹ thuật, nhưng không phải một giấy phép mở đồng nhất cho ảnh. Chỉ nên dùng theo phạm vi nghiên cứu/scientific fair use; triển khai thương mại hoặc phát hành lại ảnh cần rà soát quyền riêng.

## 3. Ảnh món Việt trên Wikimedia Commons

### 3.1. Phương pháp đếm

Đã gọi `https://commons.wikimedia.org/w/api.php` bằng User-Agent mô tả dự án, `generator=categorymembers`, `gcmtype=file`, phân trang đến hết, và lấy `imageinfo` với `extmetadata`. Một tệp được tính “cho phép tái sử dụng” chỉ khi `LicenseShortName` khớp allow-list: **CC0, CC BY, CC BY-SA hoặc Public domain**. Không suy diễn từ việc tệp có mặt trên Commons.

Raw JSON `categoryinfo` trả **HTTP 200**; đoạn bằng chứng nguyên văn (rút gọn chỉ giữ trường liên quan):[9]

```json
{"title":"Category:Bún bò Huế","categoryinfo":{"size":52,"pages":0,"files":51,"subcats":1,"hidden":false}}
{"title":"Category:Phở","categoryinfo":{"size":53,"pages":1,"files":48,"subcats":4,"hidden":false}}
{"title":"Category:Bánh xèo","categoryinfo":{"size":41,"pages":0,"files":41,"subcats":0,"hidden":false}}
{"title":"Category:Cơm tấm","categoryinfo":{"size":75,"pages":0,"files":75,"subcats":0,"hidden":false}}
{"title":"Category:Bánh mì","categoryinfo":{"size":135,"pages":0,"files":127,"subcats":8,"hidden":false}}
{"title":"Category:Gỏi cuốn","categoryinfo":{"size":49,"pages":1,"files":48,"subcats":0,"hidden":false}}
{"title":"Category:Bún chả","categoryinfo":{"size":48,"pages":0,"files":48,"subcats":0,"hidden":false}}
```

Ví dụ raw `imageinfo.extmetadata` cho một tệp trong `Category:Bánh xèo` trả `"LicenseShortName":{"value":"Public domain"}`, `"UsageTerms":{"value":"Public domain"}`, `"Copyrighted":{"value":"False"}`.[9] Bản chứng cứ đầy đủ, gồm từng file title/licence/source URL và phân bố giấy phép, nằm trong `data/reports/commons_category_evidence.json`.

### 3.2. Kết quả thực tế theo category

| Commons category | File trực tiếp | Được phép tái sử dụng | Phân bố giấy phép đã đọc từ API |
|---|---:|---:|---|
| `Category:Phở` | 48 | 48 | CC BY 14; CC BY-SA 29; CC0 3; Public domain 2 |
| `Category:Bánh mì` | 127 | 127 | CC BY 49; CC BY-SA 59; CC0 9; Public domain 10 |
| `Category:Bún bò Huế` | 51 | 51 | CC BY 17; CC BY-SA 24; CC0 5; Public domain 5 |
| `Category:Cơm tấm` | 75 | 75 | CC BY 0; CC BY-SA 23; CC0 51; Public domain 1 |
| `Category:Bánh xèo` | 41 | 41 | CC BY 11; CC BY-SA 21; CC0 3; Public domain 6 |
| `Category:Bún chả` | 48 | 48 | CC BY 9; CC BY-SA 21; CC0 0; Public domain 18 |
| `Category:Gỏi cuốn` | 48 | 48 | CC BY 14; CC BY-SA 24; CC0 6; Public domain 4 |

Các tổng trên là ảnh được gắn trực tiếp vào category, không gồm ảnh chỉ nằm trong subcategory. Chất lượng nhãn vẫn cần kiểm duyệt thủ công: một category có thể chứa ảnh nhà hàng, nguyên liệu, biến thể món, hoặc tệp liên quan nhưng không phù hợp làm mẫu huấn luyện cận cảnh.

## 4. Bộ thu thập ảnh và kiểm thử

Script: `scripts/collect_vn_images.py`.

Đặc tính đã thực thi:

- Chỉ dùng Python stdlib (`urllib.request`), User-Agent mô tả rõ.
- Nhận nhiều category; mặc định tối đa **200 ảnh/category** (`--limit/-n`).
- Mặc định ghi vào `data/raw/images/<class>/`.
- Chỉ tải CC0/CC BY/CC BY-SA/Public domain; các licence khác hoặc thiếu/không nhận diện bị bỏ qua.
- Mỗi ảnh có sidecar JSON cùng stem với `file_title`, `license`, `license_url`, `author`, `source_url`, URL file gốc, kích thước và metadata khác.
- `--dry-run` không tạo thư mục và không tải ảnh.

Kiểm thử thật:

1. Dry-run 7 category, `-n 3`: **7 category, 21 ứng viên tái sử dụng, 0 tải, 0 lỗi**.
2. Run nhỏ một category, `Category:Bánh xèo`, `-n 2`, với output override nằm trong vùng được phép của dự án: **2 ảnh tải thành công, 2 sidecar JSON, 0 lỗi**. Thư mục: `data/external/commons_smoke/Bánh xèo/`.
3. Đã đọc lại sidecar `710139_Cookshop Vietnam(2).json`: licence `CC BY-SA 2.5`, tác giả `Thomas Schoch`, URL nguồn Commons có mặt, và `downloaded_size_bytes` **327655** khớp `file_size_bytes` **327655**.

## 5. Mẫu nhập dữ liệu dinh dưỡng

Đã tạo `data/external/vn_fct_template.csv` với đúng 17 cột:

```text
food_name_vi,food_name_en,food_group,cooking_state,edible_portion,energy_kcal_per_100g,protein_g_per_100g,fat_g_per_100g,carbohydrate_g_per_100g,fiber_g_per_100g,sugar_g_per_100g,sodium_mg_per_100g,moisture_g_per_100g,ash_g_per_100g,source_name,source_url,source_note
```

Dòng đầu là comment ghi đơn vị theo 100 g phần ăn được, `edible_portion` là %, và yêu cầu giá trị chưa biết phải để trống, **không điền 0**.

## 6. Khuyến nghị nguồn

- Dữ liệu thành phần Việt Nam: dùng PDF FAO/NIN 2007 làm tài liệu gốc; nhập có kiểm soát vào CSV, lưu `source_url/source_note`, và không phát hành lại toàn bộ nếu chưa làm rõ quyền.
- Đối chiếu khu vực: dùng ASEAN FCDB cho các dòng có mã nguồn `VN...`; tuân thủ ghi nhận ASEANFOODS và giới hạn phi thương mại.
- Ảnh quốc tế: Food-101 thuận tiện kỹ thuật nhưng quyền ảnh không mở đồng nhất và chỉ phủ chính xác 4/15 lớp đích; 6 lớp phủ gần đúng, 5 lớp không phủ.
- Ảnh món Việt: Commons phù hợp hơn để bổ sung lớp thiếu vì có metadata licence từng tệp; vẫn phải giữ sidecar, attribution và ShareAlike khi áp dụng.

## Tệp chứng cứ cục bộ

- `data/reports/food101_hf_evidence.json`: raw API tree, parquet manifest, train/validation rows, dataset card và kết quả `HEAD` từng shard.
- `data/reports/commons_category_evidence.json`: raw `categoryinfo`, raw mẫu `imageinfo`, toàn bộ file/licence đã phân trang và số đếm tính được.

## Sources

[1] https://www.fao.org/fileadmin/templates/food_composition/documents/pdf/VTN_FCT_2007.pdf — Bảng thành phần thực phẩm Việt Nam 2007
    > "BẢNG THÀNH PHẦN THỰC PHẨM VIỆT NAM"
[2] https://inmu.mahidol.ac.th/aseanfoods/composition_data.html — Electronic ASEAN Food Composition Database
    > "Electronic ASEAN Food Composition Database"
[3] https://inmu.mahidol.ac.th/aseanfoods/doc/OnlineASEAN_FCD_V1_2014.pdf — ASEAN Food Composition Database, Electronic version 1
    > "ASEANFOODS encourages the use and dissemination of this online ASEAN Food Composition Database."
[4] https://huggingface.co/api/datasets/ethz/food101/tree/main/data — Food-101 repository data tree
    > ""type": "file", "oid": "aba8dad7c89bda255954ba51adf8b0147d4db870", "size": 489582959"
[5] https://datasets-server.huggingface.co/parquet?dataset=ethz/food101 — Food-101 parquet manifest
    > ""dataset": "ethz/food101", "config": "default", "split": "train""
[6] https://datasets-server.huggingface.co/rows?dataset=ethz/food101&config=default&split=train&offset=0&length=1 — Food-101 train row schema
    > ""num_rows_total": 75750, "num_rows_per_page": 100, "partial": false"
[7] https://datasets-server.huggingface.co/rows?dataset=ethz/food101&config=default&split=validation&offset=0&length=1 — Food-101 validation row schema
    > ""num_rows_total": 25250, "num_rows_per_page": 100, "partial": false"
[8] https://huggingface.co/datasets/ethz/food101/raw/main/README.md — Food-101 dataset card
    > "The Food-101 data set consists of images from Foodspotting"
[9] https://commons.wikimedia.org/w/api.php — Wikimedia Commons MediaWiki API
    > ""title": "Category:Bún bò Huế""
