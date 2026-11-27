"""Đề xuất thực đơn trong ngày dựa trên: chỉ số cơ thể, mục tiêu kcal, các bữa ĐÃ ĂN, kcal còn lại
và ghi chú của người dùng.

Nguyên tắc (giữ đúng tinh thần của dự án):
- Mọi con số đều lấy từ CSDL thật: chọn thực phẩm theo tên, giá trị dinh dưỡng theo 100 g, rồi
  nhân với khối lượng đề xuất. Không bịa món, không bịa giá trị dinh dưỡng.
- Không đủ dữ liệu thì nói rõ thiếu gì (ví dụ chưa đặt mục tiêu kcal, chưa khai chỉ số cơ thể).
- Ghi chú của người dùng được dùng làm ĐIỀU KIỆN LỌC: nếu ghi chú trống thì bỏ qua, nếu có thì
  loại các nguyên liệu bị dị ứng/kiêng và ghi lại rõ đã áp dụng điều kiện nào.
- Tỉ lệ chia kcal cho các bữa: sáng 25 % · trưa 35 % · tối 30 % · bữa nhẹ 10 %; phần chưa tiêu
  được chia lại cho các bữa CHƯA ghi.

Hằng số dùng để quy đổi năng lượng khi vận động: MET ≈ 4,0 cho đi bộ nhanh/đạp xe nhẹ và
kcal ≈ MET × cân nặng(kg) × số giờ (Quy tắc chuyển đổi MET tiêu chuẩn).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.food_repository import FoodRepository
from app.services import meal_service, nutrition, statistics_service
from app.services.nutrition_needs import compute_needs, exercise_suggestion

MEAL_SHARES: dict[str, float] = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.30, "snack": 0.10}
MEAL_LABELS_VI: dict[str, str] = {"breakfast": "Bữa sáng", "lunch": "Bữa trưa",
                                  "dinner": "Bữa tối", "snack": "Bữa nhẹ"}
MET_WALKING = 4.0  # đi bộ nhanh / đạp xe nhẹ


@dataclass(frozen=True)
class Component:
    """Một nguyên liệu trong thực đơn, gắn với cách tìm trong CSDL và khẩu phần hợp lý."""

    key: str
    name_vi: str
    search: str
    role: str            # carb | protein | veg | fruit | dairy | fat
    meals: tuple[str, ...]
    grams_min: float
    grams_max: float
    kcal_min: float      # khoảng năng lượng/100 g hợp lý để loại bản ghi sai (chips, bột khô...)
    kcal_max: float
    exclude_words: tuple[str, ...] = ()   # loại bản ghi có các từ này trong tên
    tags: tuple[str, ...] = ()            # vd: ("meat",), ("seafood",), ("egg",), ("dairy",)


COMPONENTS: tuple[Component, ...] = (
    Component("com_trang", "Cơm trắng", "rice white cooked", "carb", ("lunch", "dinner"),
              120, 250, 90, 220, ("fried", "soup", "beverage", "drink", "flour", "cake")),
    Component("com_lut", "Cơm gạo lứt", "rice brown cooked", "carb", ("lunch", "dinner"),
              120, 250, 90, 220, ("beverage", "flour", "cake")),
    Component("bun_pho", "Bún/phở (sợi)", "rice noodles", "carb", ("breakfast", "lunch"),
              150, 300, 100, 250, ("soup", "mix", "season", "flour")),
    Component("banh_mi", "Bánh mì", "bread white", "carb", ("breakfast",),
              60, 150, 200, 320, ("stuffing", "crumbs", "roll", "sweet", "cake")),
    Component("yen_mach", "Yến mạch", "oatmeal", "carb", ("breakfast",),
              40, 100, 300, 420, ("beverage", "cookie", "bar", "cereal bar")),
    Component("uc_ga", "Ức gà", "chicken breast", "protein", ("lunch", "dinner"),
              80, 200, 120, 260, ("nugget", "fried", "soup", "salad", "spread", "deli"),
              ("meat",)),
    Component("thit_heo", "Thịt heo nạc", "pork lean", "protein", ("lunch", "dinner"),
              70, 180, 120, 300, ("bacon", "sausage", "ham", "soup", "canned"), ("meat",)),
    Component("thit_bo", "Thịt bò nạc", "beef lean", "protein", ("lunch", "dinner"),
              70, 180, 120, 300, ("soup", "canned", "jerky", "sausage"), ("meat",)),
    Component("ca_bien", "Cá biển", "fish anchovy", "protein", ("lunch", "dinner"),
              80, 200, 90, 300, ("sauce", "canned", "dried", "snack"), ("seafood",)),
    Component("tom", "Tôm", "shrimp", "protein", ("lunch", "dinner"),
              70, 180, 70, 200, ("noodles", "sauce", "canned", "dried"), ("seafood",)),
    Component("trung_ga", "Trứng gà", "egg whole", "protein", ("breakfast", "lunch"),
              50, 150, 120, 220, ("beverage", "nog", "salad", "sandwich"), ("egg",)),
    Component("dau_hu", "Đậu hũ", "tofu", "protein", ("lunch", "dinner"),
              80, 200, 60, 200, ("vegetables", "sauce", "fried"), ("soy",)),
    Component("rau_cai", "Rau cải", "cabbage chinese cooked", "veg", ("lunch", "dinner"),
              100, 300, 15, 120, ("soup", "salad", "roll", "kimchi")),
    Component("bong_cai", "Bông cải", "broccoli cooked", "veg", ("lunch", "dinner"),
              100, 250, 20, 120, ("soup", "dip", "salad", "casserole")),
    Component("ca_rot", "Cà rốt", "carrot raw", "veg", ("lunch", "dinner"),
              50, 150, 25, 90, ("dehydrated", "juice", "cake", "canned")),
    Component("ca_chua", "Cà chua", "tomato red ripe raw", "veg", ("lunch", "dinner"),
              50, 150, 12, 60, ("sauce", "juice", "paste", "soup", "salad")),
    Component("chuoi", "Chuối", "banana raw", "fruit", ("snack", "breakfast"),
              80, 200, 70, 130, ("chips", "dried", "juice", "cake", "bread")),
    Component("tao", "Táo", "apple raw", "fruit", ("snack",),
              100, 250, 40, 90, ("juice", "sauce", "pie", "dried", "cake")),
    Component("cam", "Cam", "orange raw", "fruit", ("snack",),
              100, 250, 35, 90, ("juice", "drink", "blossom", "cake")),
    Component("sua_tuoi", "Sữa tươi", "milk", "dairy", ("breakfast", "snack"),
              150, 250, 40, 90, ("condensed", "powder", "chocolate", "shake", "coconut"),
              ("dairy",)),
    Component("sua_chua", "Sữa chua", "yogurt plain", "dairy", ("snack",),
              100, 200, 40, 120, ("chocolate", "frozen", "drink", "candy"), ("dairy",)),
)

ALLERGY_KEYWORDS: dict[tuple[str, ...], tuple[str, ...]] = {
    ("meat",): ("thịt", "thit", "bò", "bo", "heo", "lợn", "lon", "gà", "ga", "pork", "beef",
                "chicken", "mặn", "man"),
    ("seafood",): ("hải sản", "hai san", "cá", "ca", "tôm", "tom", "mực", "muc", "fish",
                   "shrimp", "seafood", "ốc", "oc", "cua"),
    ("egg",): ("trứng", "trung", "egg"),
    ("dairy",): ("sữa", "sua", "milk", "dairy", "lactose"),
    ("soy",): ("đậu nành", "dau nanh", "đậu hũ", "dau hu", "tofu", "soy"),
}
VEGETARIAN_WORDS = ("chay", "vegetarian", "thuần chay", "thuan chay", "vegan")
VEGAN_WORDS = ("thuần chay", "thuan chay", "vegan")
DIABETES_WORDS = ("tiểu đường", "tieu duong", "đường huyết", "duong huyet")
PROTEIN_WORDS = ("tăng cơ", "tang co", "gym", "protein", "tập tạ", "tap ta")


def _normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def parse_note_constraints(note: str | None) -> dict:
    """Đọc ghi chú của người dùng thành điều kiện lọc nguyên liệu.

    Ghi chú trống -> không có điều kiện nào (bỏ qua). Ghi chú có nội dung -> tìm các nhóm bị
    dị ứng/kiêng và các chế độ đặc biệt.
    """
    text = _normalize(note)
    if not text:
        return {"applied": [], "exclude_tags": [], "vegetarian": False, "diabetes": False,
                "prioritise_protein": False, "note_used": None}

    exclude_tags: list[str] = []
    applied: list[str] = []
    for tags, words in ALLERGY_KEYWORDS.items():
        hit = next((word for word in words if word and word in text), None)
        if not hit:
            continue
        # cần chỉ ra ý phủ định/dị ứng để tránh hiểu sai khi ghi chú chỉ nhắc tên món
        if any(marker in text for marker in ("dị ứng", "di ung", "không ăn", "khong an", "kiêng",
                                             "kieng", "tránh", "tranh", "không dùng", "khong dung")
               ) or hit in ("hải sản", "hai san", "lactose"):
            exclude_tags.extend(tags)
            applied.append(f"loại nguyên liệu thuộc nhóm {tags[0]} (ghi chú có: “{hit}”)")

    vegetarian = any(word in text for word in VEGETARIAN_WORDS)
    vegan = any(word in text for word in VEGAN_WORDS)
    if vegetarian:
        exclude_tags.extend(("meat", "seafood"))
        applied.append("chế độ ăn chay: loại thịt và hải sản"
                       + (" (thuần chay: loại cả trứng và sữa)" if vegan else " (vẫn dùng được trứng, sữa)"))
    if vegan:
        exclude_tags.extend(("egg", "dairy"))
    diabetes = any(word in text for word in DIABETES_WORDS)
    if diabetes:
        applied.append("có nhắc tới tiểu đường/đường huyết: hạn chế món nhiều đường")
    protein = any(word in text for word in PROTEIN_WORDS)
    if protein:
        applied.append("có nhắc tới tăng cơ/tập luyện: tăng khẩu phần đạm")
    return {"applied": applied, "exclude_tags": sorted(set(exclude_tags)), "vegetarian": vegetarian,
            "diabetes": diabetes, "prioritise_protein": protein, "note_used": note}


def _pick_food(repo: FoodRepository, component: Component) -> tuple[object, dict] | tuple[None, dict]:
    """Tìm thực phẩm THẬT trong CSDL cho một nguyên liệu, có kiểm tra khoảng kcal hợp lý."""
    rows, total = repo.search(query=component.search, limit=25)
    checked = 0
    for food in rows:
        name = _normalize(f"{food.name_vi or ''} {food.name_en or ''} {food.display_name}")
        if any(word in name for word in component.exclude_words):
            continue
        values = repo.nutrient_values_per_100g(food.id)
        kcal = values.get("energy_kcal")
        if kcal is None:
            continue
        checked += 1
        if component.kcal_min <= float(kcal) <= component.kcal_max:
            return food, {"food_id": food.id, "name": food.display_name, "kcal_per_100g": float(kcal),
                          "per_100g": {k: values.get(k) for k in nutrition.KEYS_FOR_REPORT},
                          "candidates_considered": checked, "search_hits": total}
    return None, {"reason": "không có bản ghi nào khớp khoảng năng lượng hợp lý",
                  "search_hits": total, "candidates_considered": checked}


def _round5(value: float) -> float:
    return float(int(round(value / 5.0)) * 5)


def _grams_for_budget(kcal_per_100g: float, budget_kcal: float, component: Component) -> float:
    grams = budget_kcal / (kcal_per_100g / 100.0)
    return _round5(max(component.grams_min, min(component.grams_max, grams)))


def build_plan(db: Session, user: User, day: date | None = None) -> dict:
    """Dựng thực đơn cho các bữa CHƯA ghi, dựa trên kcal còn lại và điều kiện trong ghi chú."""
    day = day or date.today()
    profile = user.profile
    needs = compute_needs(profile, day)
    constraints = parse_note_constraints(getattr(profile, "note", None))

    target = getattr(profile, "daily_kcal_target", None) or needs.suggested_kcal
    daily = statistics_service.daily(db, user.id, day, getattr(profile, "daily_kcal_target", None))
    eaten = daily["totals"]["totals"].get("energy_kcal")
    meals, meal_count = meal_service.list_meals(db, user.id, date_from=day, date_to=day, limit=30)
    logged_types = {meal.meal_type for meal in meals}
    if eaten is None and meal_count == 0:
        # Chưa ghi bữa nào trong ngày: coi như đã ăn 0 kcal (nói rõ trong cảnh báo bên dưới).
        eaten = 0.0
    by_meal = {row["meal_type"]: row for row in daily.get("by_meal_type", [])}

    plan: dict = {
        "date": day.isoformat(),
        "energy": {
            "needs": needs.as_dict(),
            "target_kcal": target,
            "target_source": ("mục tiêu người dùng đặt" if getattr(profile, "daily_kcal_target", None)
                              else ("đề xuất theo công thức" if needs.suggested_kcal else None)),
            "eaten_kcal": eaten,
            "remaining_kcal": (round(float(target) - float(eaten), 1)
                               if target is not None and eaten is not None else None),
        },
        "today_meals": [{"meal_type": row["meal_type"], "meal_type_vi": MEAL_LABELS_VI.get(row["meal_type"], row["meal_type"]),
                         "calories": row.get("calories"), "item_count": row.get("item_count")}
                        for row in daily.get("by_meal_type", [])],
        "constraints": constraints,
        "meals": [],
        "exercise": exercise_suggestion(needs, (float(target) - float(eaten))
                                        if (target is not None and eaten is not None) else None),
        "warnings": [],
    }
    if meal_count:
        plan["warnings"].append(f"Đã có {meal_count} bữa ghi trong ngày: chỉ đề xuất các bữa còn lại.")

    remaining = plan["energy"]["remaining_kcal"]
    if target is None:
        plan["warnings"].append("Chưa có mục tiêu kcal (chưa đặt và chưa đủ chỉ số cơ thể để đề xuất).")
        return plan
    if remaining is None:
        plan["warnings"].append("Chưa tính được kcal còn lại vì thiếu số liệu đã ăn.")
        remaining = float(target)

    pending = [meal for meal in ("breakfast", "lunch", "dinner", "snack") if meal not in logged_types]
    share_total = sum(MEAL_SHARES[meal] for meal in pending) or 1.0
    remaining_for_plan = max(0.0, float(remaining))
    rotation = day.toordinal() % 3  # đổi món theo ngày để thực đơn không lặp y hệt nhau

    repo = FoodRepository(db)
    for meal in pending:
        budget = remaining_for_plan * (MEAL_SHARES[meal] / share_total)
        if budget < 80:
            plan["meals"].append({"meal_type": meal, "meal_type_vi": MEAL_LABELS_VI[meal],
                                  "budget_kcal": round(budget, 1), "items": [],
                                  "skipped": "kcal còn lại quá ít cho bữa này"})
            continue
        wanted_roles = ("carb", "protein") if meal == "breakfast" else ("carb", "protein", "veg")
        if meal == "snack":
            wanted_roles = ("fruit", "dairy")
        items = []
        # nguyên liệu chính chiếm phần lớn kcal của bữa, phần còn lại chia cho các nguyên liệu khác
        role_shares = {"carb": 0.55, "protein": 0.45, "veg": 0.35, "fruit": 0.6, "dairy": 0.4}
        chosen: list[Component] = []
        for role in wanted_roles:
            candidates = [c for c in COMPONENTS
                          if c.role == role and meal in c.meals
                          and not set(c.tags).intersection(constraints["exclude_tags"])]
            if role == "protein" and constraints["vegetarian"]:
                # người ăn chay: ưu tiên đậu hũ nhưng VẪN dùng được trứng (trừ khi ghi rõ thuần chay)
                candidates.sort(key=lambda c: c.key != "dau_hu")
            if role == "dairy" and meal == "snack":
                candidates.sort(key=lambda c: c.key != "sua_chua")
            if candidates:
                chosen.append(candidates[rotation % len(candidates)])
        for component in chosen:
            food, info = _pick_food(repo, component)
            if food is None:
                plan["warnings"].append(f"Không tìm được thực phẩm thật cho “{component.name_vi}”: "
                                        f"{info.get('reason')}")
                continue
            share = role_shares.get(component.role, 0.4)
            grams = _grams_for_budget(info["kcal_per_100g"], budget * share, component)
            if constraints["prioritise_protein"] and component.role == "protein":
                grams = _round5(min(component.grams_max, grams * 1.25))
            factor = grams / 100.0
            per = info["per_100g"]
            items.append({
                "component_key": component.key,
                "name_vi": component.name_vi,
                "food_id": info["food_id"],
                "food_name": info["name"],
                "role": component.role,
                "grams": grams,
                "kcal_per_100g": info["kcal_per_100g"],
                "kcal": round(info["kcal_per_100g"] * factor, 1),
                "protein_g": round(per["protein_g"] * factor, 1) if per.get("protein_g") is not None else None,
                "fat_g": round(per["fat_g"] * factor, 1) if per.get("fat_g") is not None else None,
                "carbohydrate_g": (round(per["carbohydrate_g"] * factor, 1)
                                   if per.get("carbohydrate_g") is not None else None),
                "fiber_g": round(per["fiber_g"] * factor, 1) if per.get("fiber_g") is not None else None,
                "sugar_g": round(per["sugar_g"] * factor, 1) if per.get("sugar_g") is not None else None,
                "missing_nutrients": [k for k in nutrition.KEYS_FOR_REPORT if per.get(k) is None],
                "search_hits": info.get("search_hits"),
            })
        items, trim_note = _fit_budget(items, budget)
        meal_items_kcal = round(sum(item["kcal"] for item in items), 1)
        entry = {
            "meal_type": meal, "meal_type_vi": MEAL_LABELS_VI[meal],
            "budget_kcal": round(budget, 1), "items": items,
            "planned_kcal": meal_items_kcal,
            "difference_kcal": round(meal_items_kcal - budget, 1),
        }
        if trim_note:
            entry["fit_note"] = trim_note
        plan["meals"].append(entry)
    return plan


def _fit_budget(items: list[dict], budget: float, tolerance: float = 0.08) -> tuple[list[dict], str | None]:
    """Co lại khẩu phần để tổng kcal của bữa không vượt ngân sách quá `tolerance`.

    Ưu tiên giữ nguyên phần đạm (không cắt bớt đạm), chỉ giảm tinh bột/rau; nếu vẫn vượt thì mới
    giảm tất cả. Khối lượng được làm tròn về bội số 5 g và không xuống dưới khối lượng tối thiểu
    hợp lý của từng nguyên liệu.
    """
    total = sum(item["kcal"] for item in items)
    if not items or total <= budget * (1 + tolerance):
        return items, None
    note_parts = []

    def scale(allowed_kcal: float, roles: tuple[str, ...]) -> None:
        subset = [item for item in items if item["role"] in roles]
        current = sum(item["kcal"] for item in subset)
        if current <= 0 or allowed_kcal <= 0:
            return
        ratio = allowed_kcal / current
        for item in subset:
            component = next((c for c in COMPONENTS if c.key == item["component_key"]), None)
            floor = component.grams_min if component else 20.0
            new_grams = _round5(max(floor, item["grams"] * ratio))
            if new_grams >= item["grams"]:
                continue
            factor = new_grams / item["grams"]
            item["kcal"] = round(item["kcal"] * factor, 1)
            for field_name in ("protein_g", "fat_g", "carbohydrate_g", "fiber_g", "sugar_g"):
                if item.get(field_name) is not None:
                    item[field_name] = round(item[field_name] * factor, 1)
            item["grams"] = new_grams

    def allowed_for(roles: tuple[str, ...]) -> float:
        """kcal còn được phép cho nhóm nguyên liệu này = ngân sách − phần của các nguyên liệu khác."""
        return budget - sum(item["kcal"] for item in items if item["role"] not in roles)

    scale(allowed_for(("carb", "veg")), ("carb", "veg"))
    if sum(item["kcal"] for item in items) > budget * (1 + tolerance):
        scale(allowed_for(("protein", "fruit", "dairy")), ("protein", "fruit", "dairy"))
        note_parts.append("phải giảm cả phần đạm để khớp ngân sách")
    if sum(item["kcal"] for item in items) > budget * (1 + tolerance):
        note_parts.append("vẫn vượt ngân sách sau khi co khẩu phần (khối lượng đã chạm mức tối thiểu)")
    if sum(item["kcal"] for item in items) > budget * (1 + tolerance) and len(items) > 1:
        # Ngân sách quá nhỏ cho cả bộ nguyên liệu: bỏ món góp ít kcal nhất (thường là rau/trái cây).
        smallest = min(items, key=lambda item: item["kcal"])
        items = [item for item in items if item is not smallest]
        note_parts.append(f"bỏ bớt “{smallest['name_vi']}” vì ngân sách bữa quá nhỏ")
    if not note_parts:
        note_parts.append("đã co khẩu phần tinh bột/rau để khớp ngân sách")
    return items, "; ".join(note_parts)
