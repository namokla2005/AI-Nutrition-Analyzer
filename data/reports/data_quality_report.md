# Báo cáo chất lượng dữ liệu

- CSDL: `sqlite+pysqlite:///D:/Documents/BaoCao/TriTueNhanTao/AI-Nutrition-Analyzer/data/nutrition.db`
- Chế độ truy cập: **chỉ đọc** (`mode=ro`, `PRAGMA query_only=ON`)
- Tổng thực phẩm: **102284**

## 1. Trùng lặp

- Nhóm trùng chính xác theo `source_id + source_ref`: **0**
- Nhóm gần trùng theo `name_normalized` ở nhiều nguồn: **210** (tối đa 30 ví dụ)

### Trùng chính xác

Không có.

### Gần trùng khác nguồn

| name_normalized | so_luong | so_nguon | nguon |
|---|---|---|---|
| yogurt greek whole milk plain | 337 | 2 | usda_foundation,usda_fndds |
| yogurt whole milk plain | 337 | 2 | usda_foundation,usda_fndds |
| milk whole | 247 | 2 | usda_foundation,usda_fndds |
| pineapple raw | 245 | 2 | usda_foundation,usda_fndds |
| green beans raw | 225 | 2 | usda_foundation,usda_fndds |
| beets raw | 171 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| cabbage red raw | 171 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| cabbage green raw | 170 | 2 | usda_foundation,usda_fndds |
| turkey ground 93 lean 7 fat raw | 162 | 2 | usda_sr_legacy,usda_foundation |
| ketchup | 152 | 2 | usda_foundation,usda_fndds |
| celery raw | 147 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| brussels sprouts raw | 131 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| cauliflower raw | 131 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| collards raw | 131 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| chicken ground raw | 121 | 2 | usda_sr_legacy,usda_foundation |
| ham | 119 | 2 | usda_foundation,usda_fndds |
| garlic | 55 | 2 | usda_foundation,openfoodfacts |
| corn oil | 50 | 2 | usda_foundation,usda_fndds |
| canola oil | 37 | 2 | usda_foundation,usda_fndds |
| soybean oil | 28 | 2 | usda_foundation,usda_fndds |
| cheese american | 22 | 2 | usda_foundation,usda_fndds |
| whipped topping | 17 | 2 | usda_fndds,openfoodfacts |
| pita chips | 6 | 2 | usda_fndds,openfoodfacts |
| strawberries raw | 6 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| blueberries raw | 4 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| broccoli raw | 4 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| cheese swiss | 4 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| raspberries raw | 4 | 3 | usda_sr_legacy,usda_foundation,usda_fndds |
| sauerkraut | 4 | 2 | usda_fndds,openfoodfacts |
| beef loin tenderloin roast separable lean only boneless trimmed to 0 fat select cooked roasted | 3 | 2 | usda_sr_legacy,usda_foundation |

## 2. Đồng bộ bộ nhớ đệm năng lượng

Số thực phẩm cache khác hàng `food_nutrients.energy_kcal`: **0**.

Không có.

## 3. Thiếu năng lượng

Thực phẩm không có năng lượng ở cả cache lẫn bảng chuẩn: **68732**.

| id | ten |
|---|---|
| 7794 | HUMMUS, SABRA CLASSIC |
| 7795 | HUMMUS, SABRA CLASSIC |
| 7796 | HUMMUS, SABRA CLASSIC |
| 7797 | Hummus |
| 7798 | Hummus |
| 7799 | HUMMUS, SABRA CLASSIC |
| 7800 | HUMMUS, SABRA CLASSIC |
| 7801 | HUMMUS, SABRA CLASSIC |
| 7802 | Hummus |
| 7803 | Hummus |
| 7804 | Hummus |
| 7805 | HUMMUS, SABRA CLASSIC |
| 7806 | HUMMUS, SABRA CLASSIC |
| 7807 | HUMMUS, SABRA CLASSIC |
| 7808 | HUMMUS, SABRA CLASSIC |
| 7809 | HUMMUS, SABRA CLASSIC |
| 7810 | HUMMUS, SABRA CLASSIC |
| 7811 | HUMMUS, SABRA CLASSIC |
| 7812 | Hummus |
| 7813 | Hummus |
| 7814 | HUMMUS, OTHER |
| 7815 | HUMMUS, OTHER |
| 7816 | HUMMUS, OTHER |
| 7817 | HUMMUS, OTHER |
| 7818 | HUMMUS, OTHER |
| 7819 | Hummus |
| 7820 | Hummus |
| 7821 | HUMMUS, SABRA CLASSIC |
| 7822 | HUMMUS, SABRA CLASSIC |
| 7823 | HUMMUS, SABRA CLASSIC |

## 4. Giá trị phi lý

- Năng lượng > 900 kcal/100 g: **54**
- Tổng protein + carbohydrate + fat > 100 g/100 g: **198**
- Giá trị âm trong `food_nutrients`: **0** thực phẩm
- Cache năng lượng âm: **0** thực phẩm
- Natri > 40000 mg/100 g: **22**

| id | ten | energy | macro_sum | sodium |
|---|---|---|---|---|
| 100 | Oil, bearded seal (Oogruk) (Alaska Native) | 899.0 | 100.16 | 0.0 |
| 191 | Oil, flaxseed, cold pressed | 884.0 | 100.09 | 0.0 |
| 3889 | Fat, beef tallow | 902.0 | 100.0 | 0.0 |
| 3890 | Lard | 902.0 | 100.0 | 0.0 |
| 4829 | Fish oil, herring | 902.0 | 100.0 | 0.0 |
| 4830 | Fish oil, menhaden | 902.0 | 100.0 | 0.0 |
| 4831 | Fish oil, menhaden, fully hydrogenated | 902.0 | 100.0 | 0.0 |
| 4832 | Fish oil, salmon | 902.0 | 100.0 | 0.0 |
| 6066 | Fish oil, cod liver | 902.0 | 100.0 | 0.0 |
| 6067 | Fish oil, sardine | 902.0 | 100.0 | 0.0 |
| 8485 | Salt; iodized | NULL | 0 | 40100.0 |
| 8514 | Salt; iodized | NULL | 0 | 40300.0 |
| 8556 | Salt; iodized | NULL | 0 | 40700.0 |
| 81624 | Lard | 902.0 | 100.0 | 0.0 |
| 81643 | Flaxseed oil | 884.0 | 100.09 | 0.0 |
| 82288 | Milano dark chocolate cookies | 523.80952380952 | 100.0000000000008 | 190.476190476188 |
| 82355 | Crepini | 370.0 | 103.0 | NULL |
| 82455 | gg | 67.0 | 183.0 | 18800.0 |
| 82996 | Saucisse chinoise smoked | 550.0 | 101.0 | NULL |
| 82998 | Saucisse chinoise au bœuf | 550.0 | 105.0 | NULL |
| 83068 | gg | 11.0 | 171.0 | 2400.0 |
| 83204 | Nouilles instantanées | 366.0 | 115.69999980926514 | NULL |
| 83416 | gg | 3.0 | 178.0 | 30800.0 |
| 83736 | Pediasure Vanilla | 461.538461538462 | 146.1538461538461 | 71.79487179487181 |
| 83893 | Cardamom instant Chai Tea Latte | 381.25 | 103.75 | 56.25 |
| 84117 | Cioccolata Bianca | 466.0 | 103.20000000000002 | 320.0 |
| 84287 | Chocolat | 398.0 | 100.1 | 4.0 |
| 84550 | Paper boat lychee 250ml pet | 62.4 | 15.6 | 50000.0 |
| 84923 | Cini Minis Churros | 596.666666666667 | 130.66666666666669 | 600.0 |
| 85041 | Jalapeno & Cheddar Kettle Cooked Flavored Potato Chips | 500.0 | 100.00000000000009 | 571.42857142856 |

## 5. Hồ sơ giá trị thiếu

`NULL` gồm cả trường hợp không có hàng chất dinh dưỡng và hàng có `amount_per_100g=NULL`.

| nutrient_code | Có giá trị | NULL | Độ phủ | Đánh giá |
|---|---:|---:|---:|---|
| ash_g | 11386 | 90898 | 11.1% | thưa |
| calcium_mg | 17557 | 84727 | 17.2% | thưa |
| carbohydrate_g | 33756 | 68528 | 33.0% | thưa |
| cholesterol_mg | 13901 | 88383 | 13.6% | thưa |
| energy_kcal | 33552 | 68732 | 32.8% | thưa |
| energy_kj | 7928 | 94356 | 7.8% | thưa |
| fat_g | 37885 | 64399 | 37.0% | thưa |
| fiber_g | 28076 | 74208 | 27.4% | thưa |
| iron_mg | 17558 | 84726 | 17.2% | thưa |
| moisture_g | 17896 | 84388 | 17.5% | thưa |
| potassium_mg | 17354 | 84930 | 17.0% | thưa |
| protein_g | 34769 | 67515 | 34.0% | thưa |
| sodium_mg | 34813 | 67471 | 34.0% | thưa |
| sugar_g | 30449 | 71835 | 29.8% | thưa |
| vitamin_c_mg | 13702 | 88582 | 13.4% | thưa |

## 6. Trạng thái chế biến

`cooking_state='unknown'`: **57286/102284 (56.0%)**.

## 7. Đối chiếu Atwater

Chỉ xét năng lượng `measured` (giá trị NULL của dữ liệu cũ được xem là measured) và có đủ protein/carbohydrate/fat.

- Số thực phẩm đối chiếu: **13552**
- Sai khác tuyệt đối trung bình: **6.209 kcal/100 g**
- Sai khác lớn hơn 25%: **410**

| id | ten | measured | atwater | chenh_lech_pct |
|---:|---|---:|---:|---:|
| 56 | Baking chocolate, unsweetened, liquid | 472.000 | 622.500 | 31.9% |
| 95 | Sweet Potatoes, french fried, frozen as packaged, salt added in processing | 182.000 | 231.240 | 27.1% |
| 170 | Beverages, fruit-flavored drink, dry powdered mix, low calorie, with aspartame | 218.000 | 351.680 | 61.3% |
| 196 | Beverages, fruit-flavored drink, powder, with high vitamin C with other added vitamins, low calorie | 227.000 | 366.440 | 61.4% |
| 212 | Alcoholic beverage, rice (sake) | 134.000 | 22.000 | 83.6% |
| 235 | Lemons, raw, without peel | 29.000 | 44.380 | 53.0% |
| 236 | Lemon juice, raw | 22.000 | 31.160 | 41.6% |
| 237 | Lemon juice from concentrate, canned or bottled | 17.000 | 24.910 | 46.5% |
| 238 | Lemon peel, raw | 47.000 | 72.700 | 54.7% |
| 291 | Lemon juice from concentrate, bottled, REAL LEMON | 17.000 | 25.150 | 47.9% |
| 295 | Baobab powder | 250.000 | 337.590 | 35.0% |
| 644 | Limes, raw | 30.000 | 46.760 | 55.9% |
| 645 | Lime juice, raw | 25.000 | 35.990 | 44.0% |
| 646 | Lime juice, canned or bottled, unsweetened | 21.000 | 29.830 | 42.0% |
| 873 | Alfalfa seeds, sprouted, raw | 23.000 | 30.570 | 32.9% |
| 874 | Amaranth leaves, raw | 23.000 | 28.890 | 25.6% |
| 878 | Asparagus, raw | 20.000 | 25.400 | 27.0% |
| 879 | Asparagus, cooked, boiled, drained | 22.000 | 28.020 | 27.4% |
| 880 | Balsam-pear (bitter gourd), leafy tips, raw | 30.000 | 40.570 | 35.2% |
| 881 | Balsam-pear (bitter gourd), leafy tips, cooked, boiled, drained, without salt | 34.000 | 42.920 | 26.2% |
| 884 | Beans, kidney, mature seeds, sprouted, cooked, boiled, drained, without salt | 33.000 | 43.420 | 31.6% |
| 895 | Cowpeas, leafy tips, cooked, boiled, drained, without salt | 22.000 | 30.780 | 39.9% |
| 905 | Drumstick leaves, raw | 64.000 | 83.320 | 30.2% |
| 908 | Jute, potherb, raw | 34.000 | 44.050 | 29.6% |
| 918 | Lettuce, butterhead (includes boston and bibb types), raw | 13.000 | 16.300 | 25.4% |
| 920 | Lettuce, red leaf, raw | 13.000 | 16.340 | 25.7% |
| 923 | Mushrooms, brown, italian, or crimini, raw | 22.000 | 28.100 | 27.7% |
| 929 | New Zealand spinach, raw | 14.000 | 17.800 | 27.1% |
| 930 | New Zealand spinach, cooked, boiled, drained, without salt | 12.000 | 15.250 | 27.1% |
| 936 | Pumpkin leaves, cooked, boiled, drained, without salt | 21.000 | 26.420 | 25.8% |

## Tổng kết

**WARN** — trùng lặp, thiếu năng lượng, giá trị phi lý, đối chiếu Atwater lệch trên 25%.
