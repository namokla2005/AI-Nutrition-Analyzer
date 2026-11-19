# Kiểm kê tập con Open Food Facts

## Kết quả trích xuất

- **Đường lấy dữ liệu:** truyền trực tiếp (stream) toàn bộ bản xuất CSV nén, không dùng API dự phòng và không lưu bản dump 1,54 GB xuống đĩa.
- **URL nguồn:** `https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz`.[2]
- **URL sau chuyển hướng:** `https://openfoodfacts-ds.s3.eu-west-3.amazonaws.com/en.openfoodfacts.org.products.csv.gz`.
- **Content-Length nhận từ phản hồi tải:** **1.540.715.029 byte**.
- **Bắt đầu (UTC):** `2026-11-18T20:06:52.183857+00:00`.
- **Kết thúc (UTC):** `2026-11-18T20:22:36.560310+00:00`.
- **Dấu phân cách tự phát hiện:** tab (`\t`), phù hợp với phần mô tả bản xuất hiện tại của Open Food Facts.[1]
- **Số dòng đã đọc:** **4.921.304**.
- **Số dòng đủ điều kiện dinh dưỡng:** **3.449.726**.
- **Số dòng giữ lại:** **20.000**.
- **Số dòng ưu tiên Việt Nam giữ lại:** **1.132** (đã gặp 1.132 dòng đủ điều kiện có Việt Nam ở bất kỳ vị trí nào trong `countries_tags` hoặc `countries_en`).
- **Số dòng giữ lại có đủ bốn trường macro:** **20.000**.

## Tiêu chí và cách lấy mẫu

- Một dòng chỉ hợp lệ khi `energy-kcal_100g`, `proteins_100g`, `carbohydrates_100g` và `fat_100g` đều phân tích được thành số hữu hạn, không âm; ba macro theo gram không vượt 100 g/100 g và năng lượng không vượt 10.000 kcal/100 g.
- Các trường tùy chọn `fiber_100g`, `sugars_100g`, `sodium_100g` được giữ trống nếu thiếu hoặc không hợp lệ; không thay bằng 0.
- Bộ chọn một lượt giữ tối đa 10.000 ứng viên Việt Nam bằng reservoir sampling và tối đa 20.000 ứng viên dự phòng cân bằng theo `pnns_groups_1`, sau đó theo nhãn đầu tiên của `categories_en`. Tổng số ứng viên trong RAM bị chặn ở 30.000; hạt giống ngẫu nhiên là `20261119`.
- CSV và JSONL chứa cùng 20.000 bản ghi và cùng 14 trường đầu ra; JSONL có một đối tượng JSON trên mỗi dòng.

## Kiểm chứng tệp đầu ra

| Tệp | Số bản ghi | Kích thước (byte) | SHA-256 |
|---|---:|---:|---|
| `off_subset.csv` | 20.000 | 3.369.336 | `73140b7b09372078c24be62a0a9fdccf1fac186ba2502e03ee4d8c0027d94eb3` |
| `off_subset.jsonl` | 20.000 | 7.974.700 | `23690ea5f7629a996efdad3200f5082680b92bc2be26561109f7116267785fd1` |

Kiểm tra đọc lại xác nhận hai định dạng tương đương từng bản ghi, không có ô trống trong bốn trường macro bắt buộc.

## Số dòng giữ lại theo quốc gia

Bảng này dùng **nhãn quốc gia đầu tiên** trong `countries_en` (nếu thiếu thì dùng `countries_tags`); vì một sản phẩm có thể có nhiều quốc gia, số Việt Nam ở bảng này (1.053) nhỏ hơn số dòng phát hiện Việt Nam ở bất kỳ vị trí nào (1.132). Tổng các dòng trong bảng là **20.000**.

| Quốc gia/nhãn chính | Số dòng |
|---|---:|
| Afghanistan | 2 |
| Albania | 2 |
| Algeria | 23 |
| Andorra | 3 |
| Argentina | 46 |
| Armenia | 1 |
| Australia | 280 |
| Austria | 110 |
| Bahrain | 3 |
| Bangladesh | 3 |
| Belarus | 17 |
| Belgium | 576 |
| Bolivia | 49 |
| Bosnia and Herzegovina | 5 |
| Brazil | 515 |
| Brunei | 2 |
| Bulgaria | 118 |
| Cambodia | 5 |
| Cameroon | 3 |
| Canada | 357 |
| Chile | 47 |
| China | 9 |
| Colombia | 116 |
| Costa Rica | 3 |
| Croatia | 40 |
| Cuba | 6 |
| Cyprus | 46 |
| Czech Republic | 133 |
| Côte d'Ivoire | 4 |
| Denmark | 77 |
| Djibouti | 1 |
| Dominican Republic | 1 |
| Ecuador | 4 |
| Egypt | 6 |
| El Salvador | 1 |
| Estonia | 21 |
| Ethiopia | 1 |
| European Union | 5 |
| Fiji | 2 |
| Finland | 104 |
| France | 3.786 |
| French Polynesia | 5 |
| Georgia | 4 |
| Germany | 1.351 |
| Ghana | 1 |
| Greece | 75 |
| Guadeloupe | 2 |
| Guatemala | 1 |
| Guernsey | 1 |
| Haiti | 1 |
| Hong Kong | 7 |
| Hungary | 71 |
| Iceland | 4 |
| India | 277 |
| Indonesia | 11 |
| Iraq | 5 |
| Ireland | 119 |
| Isle of Man | 1 |
| Israel | 10 |
| Italy | 1.068 |
| Jamaica | 2 |
| Japan | 45 |
| Jersey | 1 |
| Jordan | 2 |
| Kazakhstan | 8 |
| Kuwait | 10 |
| Latvia | 14 |
| Lebanon | 10 |
| Libya | 3 |
| Liechtenstein | 1 |
| Lithuania | 18 |
| Luxembourg | 24 |
| Madagascar | 3 |
| Malaysia | 18 |
| Malta | 6 |
| Mexico | 44 |
| Moldova | 2 |
| Monaco | 1 |
| Mongolia | 1 |
| Montenegro | 2 |
| Morocco | 35 |
| Myanmar | 2 |
| Namibia | 2 |
| Netherlands | 549 |
| New Caledonia | 1 |
| New Zealand | 31 |
| Nigeria | 2 |
| North Macedonia | 1 |
| Norway | 369 |
| Oman | 4 |
| Pakistan | 5 |
| Panama | 13 |
| Paraguay | 2 |
| Peru | 20 |
| Philippines | 24 |
| Poland | 241 |
| Portugal | 114 |
| Puerto Rico | 5 |
| Qatar | 16 |
| Romania | 54 |
| Russia | 136 |
| Rwanda | 4 |
| Réunion | 3 |
| Saint Martin | 1 |
| San Marino | 1 |
| Saudi Arabia | 122 |
| Senegal | 3 |
| Serbia | 13 |
| Singapore | 62 |
| Slovakia | 22 |
| Slovenia | 13 |
| South Africa | 12 |
| South Korea | 10 |
| Spain | 574 |
| Sri Lanka | 1 |
| Svalbard and Jan Mayen | 1 |
| Sweden | 118 |
| Switzerland | 247 |
| Syria | 1 |
| Taiwan | 9 |
| Tanzania | 4 |
| Thailand | 64 |
| Trinidad and Tobago | 1 |
| Tunisia | 12 |
| Turkey | 83 |
| Uganda | 1 |
| Ukraine | 102 |
| United Arab Emirates | 13 |
| United Kingdom | 667 |
| United States | 5.267 |
| Unknown | 77 |
| Uruguay | 1 |
| Vietnam | 1.053 |
| World | 32 |
| Yemen | 3 |
| Yugoslavia | 2 |
| Zimbabwe | 1 |
| en:Product of Canada | 1 |
| en:Sverige | 5 |
| en:Türkiye | 4 |
| Åland Islands | 2 |

## Số dòng giữ lại theo nhóm chọn mẫu

Nhóm bắt đầu bằng `PNNS:` lấy từ `pnns_groups_1`; nhóm bắt đầu bằng `Category:` là nhãn đầu tiên của `categories_en`. Tổng các dòng trong bảng là **20.000**.

| Nhóm chọn mẫu | Số dòng |
|---|---:|
| Category: Baby foods | 388 |
| Category: Beverages | 388 |
| Category: Beverages and beverages preparations | 391 |
| Category: Biscuits and crackers | 178 |
| Category: Breakfasts | 268 |
| Category: Chips and fries | 388 |
| Category: Cocoa and its products | 388 |
| Category: Condiments | 388 |
| Category: Cooking helpers | 388 |
| Category: Crêpes and pancakes | 388 |
| Category: Dairies | 389 |
| Category: Desserts | 389 |
| Category: Dietary supplements | 390 |
| Category: Dried products | 388 |
| Category: Festive foods | 388 |
| Category: Flavoured almonds | 3 |
| Category: Flavoured pistachios | 13 |
| Category: Food additives | 388 |
| Category: Freeze-dried foods | 58 |
| Category: Frozen foods | 388 |
| Category: Meal kits | 345 |
| Category: Meat alternatives | 389 |
| Category: Meats and their products | 388 |
| Category: Plant-based foods and beverages | 391 |
| Category: Snacks | 393 |
| Category: Specific products | 388 |
| Category: Spreads | 388 |
| Category: Sweeteners | 390 |
| Category: Syrups | 388 |
| Category: broths | 388 |
| Category: en:Aguas | 19 |
| Category: en:Alimentos preparados | 4 |
| Category: en:Aliments d'origine végétale | 62 |
| Category: en:Aliments pour bébé | 6 |
| Category: en:Baking decorations | 93 |
| Category: en:Beans | 10 |
| Category: en:Beech nut | 1 |
| Category: en:Beef ragu | 1 |
| Category: en:Bison | 1 |
| Category: en:Boissons  Boissons avec sucre ajouté | 1 |
| Category: en:Breaded fish filets | 1 |
| Category: en:Caramel-flavored topping | 1 |
| Category: en:Cauliflower Rice | 2 |
| Category: en:Cheddar jack cheese | 1 |
| Category: en:Cheese crackers | 3 |
| Category: en:Cheese scone | 1 |
| Category: en:Cheese-flavored corn snack | 1 |
| Category: en:Chicken tenderloins | 1 |
| Category: en:Chilled ready-made meals | 1 |
| Category: en:Chips | 152 |
| Category: en:Coconut based alternative to soft chees | 1 |
| Category: en:Condimentos | 6 |
| Category: en:Cookies with chocolate chips | 1 |
| Category: en:Cooking oil | 7 |
| Category: en:Corn snacks | 4 |
| Category: en:Cremas | 16 |
| Category: en:Crispbake | 1 |
| Category: en:Cucumbers in Brine | 1 |
| Category: en:Desert mixes | 1 |
| Category: en:Drink mix | 5 |
| Category: en:Dry beans | 1 |
| Category: en:Eat well | 1 |
| Category: en:Empty | 7 |
| Category: en:Food | 120 |
| Category: en:Frozen Bread & Dough | 1 |
| Category: en:Frozen Peaches | 1 |
| Category: en:Fruit leather | 1 |
| Category: en:Fruit yogurts fat-free | 1 |
| Category: en:Fully Cooked Hickory Smoked Sausage | 2 |
| Category: en:Gluten free toasts | 1 |
| Category: en:Gravy Mix | 1 |
| Category: en:Iced tea mix | 1 |
| Category: en:Ingredientes | 2 |
| Category: en:Jello | 1 |
| Category: en:Juice Blends | 1 |
| Category: en:King Prawns | 1 |
| Category: en:Lamb Rogan Josh | 1 |
| Category: en:Macaroni & cheese | 1 |
| Category: en:Meals  Pizzas pies and quiches  Pizzas | 1 |
| Category: en:Mexican Dinner Mixes | 86 |
| Category: en:Mixed Salad | 2 |
| Category: en:Non-GMO certified project | 1 |
| Category: en:Null | 2 |
| Category: en:Oat Cookies | 1 |
| Category: en:Pita chips | 12 |
| Category: en:Potato mash | 1 |
| Category: en:Produce | 21 |
| Category: en:Salted snacks | 316 |
| Category: en:Salted-snacks | 1 |
| Category: en:Smoked salmon lentil salad | 1 |
| Category: en:Strawberry topping | 1 |
| Category: en:Undefined | 43 |
| Category: en:Vanilla pudding | 1 |
| Category: en:Vegetable sweet | 1 |
| Category: en:Water Flavor Packet | 1 |
| Category: en:Water drinks | 1 |
| Category: en:baked-brie | 8 |
| Category: en:baking-decorations | 387 |
| Category: en:brandy and clementine mincemeat | 1 |
| Category: en:canned-precooked-meat | 1 |
| Category: en:carrot-coriander-soup | 1 |
| Category: en:casserole | 3 |
| Category: en:cauliflower-crust-pizza | 16 |
| Category: en:cauliflower-florets | 4 |
| Category: en:chocolate-cupcakes | 1 |
| Category: en:chocolate-fudge | 2 |
| Category: en:chocolate-with-raspberries | 1 |
| Category: en:composite-foods | 2 |
| Category: en:condensed-soup | 3 |
| Category: en:cooking-helpersdessert-mixespancake-mixespancake-mixespastries-mixes | 1 |
| Category: en:crackers | 171 |
| Category: en:crepes-and-galettes | 387 |
| Category: en:dessert-crumble-rhubarb | 1 |
| Category: en:empty | 18 |
| Category: en:frozen-bread-dough | 1 |
| Category: en:frozen-pancakes-waffles-french-toast-crepes | 1 |
| Category: en:full fat cream | 1 |
| Category: en:grapeseed-oil-blend | 2 |
| Category: en:gravy-mix | 1 |
| Category: en:groceries | 387 |
| Category: en:guava-juice | 2 |
| Category: en:hashbrowns | 1 |
| Category: en:high-cholesterol | 1 |
| Category: en:juice | 82 |
| Category: en:kelp-granules | 1 |
| Category: en:legums | 1 |
| Category: en:lemongrass-paste | 1 |
| Category: en:mackerel-in-soybean-paste | 1 |
| Category: en:meat-product | 5 |
| Category: en:mexican-dinner-mixes | 387 |
| Category: en:mixed-olives-greek-feta | 1 |
| Category: en:null | 387 |
| Category: en:peanut-butter-bliss | 1 |
| Category: en:peels | 1 |
| Category: en:pita-chips | 50 |
| Category: en:pizza-crust | 8 |
| Category: en:plant-based-foods-and-beverages-plant-based-foods-snacks-desserts-fruits-and-vegetables-based-foods-fruits-based-food | 1 |
| Category: en:rice-flakes-sheet | 1 |
| Category: en:rice-noodles | 64 |
| Category: en:salsa | 74 |
| Category: en:salted-snacks | 387 |
| Category: en:seaweed-salads | 8 |
| Category: en:skin-toner | 1 |
| Category: en:spicy-guacamole-mix | 1 |
| Category: en:sports-drink | 52 |
| Category: en:streaky-bacon | 1 |
| Category: en:tagine | 1 |
| Category: en:tuscan-soup | 3 |
| Category: en:undefined | 387 |
| Category: en:unknown | 16 |
| Category: es:Despensa/Cereales | 7 |
| Category: es:Despensa/Ingredientes para repostería &gt; Despensa | 8 |
| Category: es:Despensa/Salsas | 31 |
| Category: es:Mercado/Bebidas/Jugos &gt; Mercado/Bebidas &gt; Mercado | 4 |
| Category: es:Mercado/Despensa/Cereales y granolas &gt; Mercado/Despensa &gt; Mercado | 9 |
| Category: es:Mercado/Despensa/Enlatados y conservas &gt; Mercado/Despensa &gt; Mercado | 7 |
| Category: es:Mercado/Despensa/Salsas | 22 |
| Category: es:frutas-en-licor | 1 |
| Category: es:mutigrain | 1 |
| Category: fr:Biotine | 1 |
| Category: fr:Bouillies | 1 |
| Category: fr:Breuvage | 1 |
| Category: fr:Chocolate snack | 1 |
| Category: fr:Crakers | 2 |
| Category: fr:Fromage camembert | 1 |
| Category: fr:Légumineuses cuites | 1 |
| Category: fr:Produits à garnir | 3 |
| Category: fr:Préparations pour pâtisseries | 7 |
| Category: fr:Sauces poutine | 4 |
| Category: fr:barres croquantes aux 7 grains quinoa | 1 |
| Category: fr:beurres-d-erable | 2 |
| Category: fr:boisson-pour-sportifs | 1 |
| Category: fr:craquelin | 3 |
| Category: fr:creme-d-asperges | 28 |
| Category: fr:farines-de-avoines | 1 |
| Category: fr:filets-poisson-enrobe-de-chapelure | 1 |
| Category: fr:fondue-chinoise | 1 |
| Category: fr:grnola-au-beurre-d-amande | 1 |
| Category: fr:hot-chocolate-mix | 1 |
| Category: fr:jus | 10 |
| Category: fr:jus-de-fruis | 2 |
| Category: fr:lamb-rogan-josh | 1 |
| Category: fr:pommes-de-terre-farcies | 6 |
| Category: fr:sans-viande-hache | 1 |
| Category: fr:sauces-poutine | 9 |
| Category: fr:tartinade-amandes-et-chocolat-noir | 1 |
| Category: it:parmigiana | 1 |
| Category: stuffing | 238 |
| Other categories | 409 |
| PNNS: Alcoholic beverages | 387 |
| PNNS: Baby foods | 387 |
| PNNS: Beverages | 439 |
| PNNS: Cereals and potatoes | 430 |
| PNNS: Composite foods | 394 |
| PNNS: Fat and sauces | 402 |
| PNNS: Fish Meat Eggs | 391 |
| PNNS: Fruits and vegetables | 393 |
| PNNS: Milk and dairy products | 410 |
| PNNS: Salty snacks | 50 |
| PNNS: Sugary snacks | 37 |
| Uncategorized | 884 |

## Giấy phép dữ liệu

Open Food Facts công bố nguyên văn: **“The Open Food Facts database is available under the Open Database License (ODbL).”**[1]

URL giấy phép và điều kiện tái sử dụng: https://world.openfoodfacts.org/data

## Tệp liên quan

- `data/external/openfoodfacts/off_subset.csv`
- `data/external/openfoodfacts/off_subset.jsonl`
- `data/external/openfoodfacts/extraction_metadata.json`
- `scripts/extract_off_subset.py`

## Sources

[1] https://world.openfoodfacts.org/data — Open Food Facts Data
[2] https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz — Open Food Facts CSV export
