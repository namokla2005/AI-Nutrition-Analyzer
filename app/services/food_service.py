"""Nghiệp vụ thực phẩm: tra cứu, xem chi tiết, tạo bản ghi nhập tay, tính khẩu phần."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.utils import normalize_name
from app.models import Food, FoodNutrient, FoodSource, Nutrient
from app.repositories.food_repository import FoodRepository
from app.services import nutrition

# Thứ tự hiển thị chất dinh dưỡng trên giao diện
DISPLAY_ORDER = [
    "energy_kcal",
    "protein_g",
    "fat_g",
    "carbohydrate_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
    "moisture_g",
    "ash_g",
    "cholesterol_mg",
    "calcium_mg",
    "iron_mg",
    "potassium_mg",
    "vitamin_c_mg",
    "energy_kj",
]

# Chất dinh dưỡng then chốt cần báo rõ nếu thiếu (không được im lặng bỏ qua)
KEY_NUTRIENTS = [
    "energy_kcal",
    "protein_g",
    "fat_g",
    "carbohydrate_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
]

# Ánh xạ trường trong yêu cầu tạo mới -> mã chất dinh dưỡng
CREATE_FIELD_TO_NUTRIENT = {
    "energy_kcal_per_100g": "energy_kcal",
    "protein_g_per_100g": "protein_g",
    "fat_g_per_100g": "fat_g",
    "carbohydrate_g_per_100g": "carbohydrate_g",
    "fiber_g_per_100g": "fiber_g",
    "sugar_g_per_100g": "sugar_g",
    "sodium_mg_per_100g": "sodium_mg",
    "moisture_g_per_100g": "moisture_g",
    "ash_g_per_100g": "ash_g",
}


class FoodServiceError(Exception):
    def __init__(self, message: str, code: str = "food_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _source_map(db: Session) -> dict[int, FoodSource]:
    return {s.id: s for s in db.scalars(select(FoodSource))}


def serialize_food(food: Food, source: FoodSource | None = None) -> dict:
    return {
        "id": food.id,
        "name_vi": food.name_vi,
        "name_en": food.name_en,
        "category": food.category,
        "food_group": food.food_group,
        "cooking_state": food.cooking_state,
        "energy_kcal_per_100g": food.energy_kcal_per_100g,
        "default_serving_g": food.default_serving_g,
        "source_code": source.code if source else None,
        "is_verified": bool(food.is_verified),
    }


def list_foods(
    db: Session,
    query: str | None = None,
    category: str | None = None,
    food_group: str | None = None,
    cooking_state: str | None = None,
    min_kcal: float | None = None,
    max_kcal: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    repo = FoodRepository(db)
    rows, total = repo.search(
        query=query,
        category=category,
        food_group=food_group,
        cooking_state=cooking_state,
        min_kcal=min_kcal,
        max_kcal=max_kcal,
        limit=limit,
        offset=offset,
    )
    sources = _source_map(db)
    return [serialize_food(f, sources.get(f.source_id)) for f in rows], total


def get_food_detail(db: Session, food_id: int) -> dict | None:
    repo = FoodRepository(db)
    food = repo.get_with_nutrients(food_id)
    if food is None:
        return None
    source = db.get(FoodSource, food.source_id)
    data = serialize_food(food, source)
    data.update(
        {
            "source_ref": food.source_ref,
            "source_name": source.name if source else None,
            "source_url": source.url if source else None,
            "source_license": source.license if source else None,
            "image_class": food.image_class,
            "nutrients": [],
        }
    )
    values = [
        {
            "code": fn.nutrient.code,
            "name_vi": fn.nutrient.name_vi,
            "unit": fn.unit,
            "amount_per_100g": fn.amount_per_100g,
            "data_quality": fn.data_quality,
        }
        for fn in food.nutrients
    ]
    values.sort(key=lambda v: DISPLAY_ORDER.index(v["code"]) if v["code"] in DISPLAY_ORDER else 99)
    data["nutrients"] = values
    return data


def portion_for_food(
    db: Session, food_id: int, weight_grams: float, quantity: float = 1.0
) -> dict:
    """Tính dinh dưỡng theo khối lượng thực tế (§5.3). Không bịa số khi thiếu dữ liệu."""
    repo = FoodRepository(db)
    food = repo.get(food_id)
    if food is None:
        raise FoodServiceError("Không tìm thấy thực phẩm.", "not_found")

    try:
        per_100g = nutrition.portion_values(
            {k: v for k, v in repo.nutrient_values_per_100g(food_id).items() if k != "energy_kj"},
            weight_grams,
            quantity,
        )
    except nutrition.InvalidWeightError as exc:
        raise FoodServiceError(str(exc), "invalid_weight") from exc

    meta = {
        n.code: n
        for n in db.scalars(select(Nutrient).where(Nutrient.code.in_(list(per_100g.keys()))))
    }
    raw_per_100g = repo.nutrient_values_per_100g(food_id)

    values = []
    for code in sorted(per_100g.keys(), key=lambda c: DISPLAY_ORDER.index(c) if c in DISPLAY_ORDER else 99):
        nutrient = meta.get(code)
        total = per_100g[code]
        values.append(
            {
                "code": code,
                "name_vi": nutrient.name_vi if nutrient else code,
                "unit": nutrient.unit if nutrient else "",
                "per_100g": raw_per_100g.get(code),
                "total": nutrition.round_nutrients({code: total})[code],
            }
        )

    # Chất thiếu = chất then chốt KHÔNG có số liệu trong nguồn (kể cả khi bảng
    # food_nutrients hoàn toàn không có dòng nào cho chất đó).
    missing = [code for code in KEY_NUTRIENTS if raw_per_100g.get(code) is None]

    kcal = nutrition.round_nutrients({"energy_kcal": per_100g.get("energy_kcal")})["energy_kcal"]
    if kcal is not None:
        kcal_source = "measured"
    else:
        # Không có số đo năng lượng -> chỉ ước lượng từ 3 đa lượng, và nói rõ là ước lượng
        estimate = nutrition.kcal_per_100g_from_macros(
            raw_per_100g.get("protein_g"), raw_per_100g.get("carbohydrate_g"), raw_per_100g.get("fat_g")
        )
        kcal = (
            nutrition.round_nutrients(
                {"energy_kcal": nutrition.portion_amount(estimate, weight_grams, quantity)}
            )["energy_kcal"]
            if estimate is not None
            else None
        )
        kcal_source = "estimated_atwater" if kcal is not None else "unavailable"

    totals_for_split = {
        code: nutrition.portion_amount(raw_per_100g.get(code), weight_grams, quantity)
        for code in ("protein_g", "carbohydrate_g", "fat_g")
    }

    return {
        "food_id": food.id,
        "food_name": food.display_name,
        "weight_grams": float(weight_grams),
        "quantity": float(quantity),
        "total_weight_grams": round(float(weight_grams) * float(quantity), 2),
        "cooking_state": food.cooking_state,
        "values": values,
        "missing_nutrients": missing,
        "kcal": kcal,
        "kcal_source": kcal_source,
        "macro_energy_split": nutrition.macro_energy_split(totals_for_split),
    }


def create_food(db: Session, payload: dict, user_id: int) -> Food:
    """Tạo thực phẩm nhập tay. Luôn gắn với một nguồn dữ liệu để truy vết (§6)."""
    name_vi = (payload.get("name_vi") or "").strip() or None
    name_en = (payload.get("name_en") or "").strip() or None
    if not name_vi and not name_en:
        raise FoodServiceError("Cần nhập ít nhất tên tiếng Việt hoặc tiếng Anh.", "missing_name")

    source_note = (payload.get("source_note") or "").strip()
    source_url = (payload.get("source_url") or "").strip() or None
    source_name = (payload.get("source_name") or "").strip()
    if not source_name:
        raise FoodServiceError(
            "Bắt buộc khai báo tên nguồn dữ liệu khi thêm thực phẩm mới.", "missing_source"
        )

    source = db.scalars(select(FoodSource).where(FoodSource.code == "manual")).first()
    if source is None:
        raise FoodServiceError("Nguồn dữ liệu 'manual' chưa được khởi tạo.", "no_source")

    food = Food(
        source_id=source.id,
        source_ref=f"user:{user_id}:{normalize_name(name_vi or name_en)}",
        name_vi=name_vi,
        name_en=name_en,
        name_normalized=normalize_name(name_vi or name_en),
        category=(payload.get("category") or None),
        food_group=(payload.get("food_group") or None),
        cooking_state=payload.get("cooking_state") or "unknown",
        default_serving_g=None,
        data_note=f"{source_name}" + (f" | {source_note}" if source_note else "")
        + (f" | {source_url}" if source_url else ""),
        is_verified=0,
    )
    db.add(food)
    db.flush()

    repo = FoodRepository(db)
    nutrient_rows = {
        n.code: n
        for n in db.scalars(select(Nutrient).where(Nutrient.code.in_(CREATE_FIELD_TO_NUTRIENT.values())))
    }
    for field, code in CREATE_FIELD_TO_NUTRIENT.items():
        value = payload.get(field)
        nutrient = nutrient_rows.get(code)
        if nutrient is None:
            continue
        if value is not None:
            repo.upsert_nutrient(food.id, nutrient.id, float(value), nutrient.unit, quality="user_input")
    repo.sync_energy_cache(food.id)

    for alias in payload.get("aliases") or []:
        repo.add_alias(food.id, alias)

    db.commit()
    db.refresh(food)
    return food


def filter_options(db: Session) -> dict:
    repo = FoodRepository(db)
    return {
        "categories": repo.distinct_categories()[:200],
        "food_groups": repo.distinct_food_groups()[:200],
        "cooking_states": ["raw", "cooked", "processed", "unknown"],
        "count_by_source": repo.count_by_source(),
    }
