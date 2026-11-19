"""Nghiệp vụ nhật ký ăn uống.

Nguyên tắc:
- Mọi truy vấn đều lọc theo `user_id` lấy từ phiên server (§7.8).
- Khi ghi một bữa ăn, giá trị dinh dưỡng được TÍNH và LƯU SNAPSHOT ngay (§7.4),
  để lịch sử không đổi khi dữ liệu thực phẩm nguồn được cập nhật về sau.
- Chất thiếu dữ liệu lưu là NULL, không bao giờ 0.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.timeutil import local_date_of, utc_to_local
from app.core.utils import utcnow
from app.models import Food, Meal, MealItem
from app.repositories.food_repository import FoodRepository
from app.services import nutrition

MEAL_NUTRIENT_CODES = [
    "energy_kcal",
    "protein_g",
    "carbohydrate_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
]


class MealServiceError(Exception):
    def __init__(self, message: str, code: str = "meal_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _estimate_kcal(per_100g: dict[str, float | None]) -> tuple[float | None, str]:
    """Năng lượng cho 100 g: ưu tiên số đo, chỉ ước lượng khi thật sự thiếu (nói rõ nguồn)."""
    measured = per_100g.get("energy_kcal")
    if measured is not None:
        return float(measured), "measured"
    estimate = nutrition.kcal_per_100g_from_macros(
        per_100g.get("protein_g"), per_100g.get("carbohydrate_g"), per_100g.get("fat_g")
    )
    if estimate is None:
        return None, "unavailable"
    return estimate, "estimated_atwater"


def _build_item(db: Session, repo: FoodRepository, food: Food, weight_g: float, quantity: float) -> MealItem:
    per_100g = repo.nutrient_values_per_100g(food.id)
    effective_kcal_per_100g, kcal_source = _estimate_kcal(per_100g)

    def total(code: str, override: float | None = None) -> float | None:
        value = per_100g.get(code) if override is None else override
        return nutrition.round_nutrients(
            {code: nutrition.portion_amount(value, weight_g, quantity)}
        )[code]

    item = MealItem(
        food_id=food.id,
        weight_grams=float(weight_g),
        quantity=float(quantity),
        kcal=total("energy_kcal", override=effective_kcal_per_100g),
        protein_g=total("protein_g"),
        carbohydrate_g=total("carbohydrate_g"),
        fat_g=total("fat_g"),
        fiber_g=total("fiber_g"),
        sugar_g=total("sugar_g"),
        sodium_mg=total("sodium_mg"),
        kcal_source=kcal_source,
        nutrition_snapshot={
            "food_id": food.id,
            "food_name": food.display_name,
            "food_name_vi": food.name_vi,
            "food_name_en": food.name_en,
            "cooking_state": food.cooking_state,
            "source_ref": food.source_ref,
            "per_100g": per_100g,
            "weight_grams": float(weight_g),
            "quantity": float(quantity),
            "kcal_source": kcal_source,
            "captured_at_utc": utcnow().isoformat(timespec="seconds"),
        },
    )
    return item


def _load_items(db: Session, items: list) -> list[MealItem]:
    repo = FoodRepository(db)
    built: list[MealItem] = []
    missing: list[int] = []
    for spec in items:
        food_id = spec.food_id if hasattr(spec, "food_id") else spec["food_id"]
        weight = spec.weight_grams if hasattr(spec, "weight_grams") else spec["weight_grams"]
        qty = spec.quantity if hasattr(spec, "quantity") else spec.get("quantity", 1.0)
        food = repo.get(food_id)
        if food is None:
            missing.append(food_id)
            continue
        built.append(_build_item(db, repo, food, weight, qty))
    if missing:
        raise MealServiceError(
            f"Không tìm thấy thực phẩm có id: {', '.join(map(str, missing))}.", "food_not_found"
        )
    if not built:
        raise MealServiceError("Bữa ăn phải có ít nhất một món hợp lệ.", "empty_meal")
    return built


def create_meal(db: Session, user_id: int, payload: dict) -> Meal:
    meal = Meal(
        user_id=user_id,
        eaten_at=payload.get("eaten_at") or utcnow(),
        meal_type=payload["meal_type"],
        note=payload.get("note"),
    )
    meal.items = _load_items(db, payload["items"])
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


def get_meal(db: Session, user_id: int, meal_id: int) -> Meal | None:
    stmt = (
        select(Meal)
        .options(selectinload(Meal.items).selectinload(MealItem.food))
        .where(Meal.id == meal_id, Meal.user_id == user_id)  # quyền sở hữu
    )
    return db.scalars(stmt).first()


def list_meals(
    db: Session,
    user_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    meal_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Meal], int]:
    limit = max(1, min(int(limit), 200))
    stmt = select(Meal).where(Meal.user_id == user_id)
    if date_from is not None:
        from app.core.timeutil import local_day_bounds

        stmt = stmt.where(Meal.eaten_at >= local_day_bounds(date_from)[0])
    if date_to is not None:
        from app.core.timeutil import local_day_bounds

        stmt = stmt.where(Meal.eaten_at < local_day_bounds(date_to)[1])
    if meal_type:
        stmt = stmt.where(Meal.meal_type == meal_type)

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(
            stmt.options(selectinload(Meal.items).selectinload(MealItem.food))
            .order_by(Meal.eaten_at.desc(), Meal.id.desc())
            .limit(limit)
            .offset(max(0, offset))
        )
    )
    return rows, total


def update_meal(db: Session, user_id: int, meal_id: int, payload: dict) -> Meal:
    meal = get_meal(db, user_id, meal_id)
    if meal is None:
        raise MealServiceError("Không tìm thấy bữa ăn.", "not_found")
    if payload.get("meal_type") is not None:
        meal.meal_type = payload["meal_type"]
    if payload.get("eaten_at") is not None:
        meal.eaten_at = payload["eaten_at"]
    if "note" in payload:
        meal.note = payload.get("note")
    if payload.get("items") is not None:
        meal.items = _load_items(db, payload["items"])
    db.commit()
    db.refresh(meal)
    return meal


def delete_meal(db: Session, user_id: int, meal_id: int) -> None:
    meal = get_meal(db, user_id, meal_id)
    if meal is None:
        raise MealServiceError("Không tìm thấy bữa ăn.", "not_found")
    db.delete(meal)  # meal_items xóa theo CASCADE
    db.commit()


def meals_in_range(db: Session, user_id: int, start_utc: datetime, end_utc: datetime) -> list[Meal]:
    stmt = (
        select(Meal)
        .options(selectinload(Meal.items))
        .where(Meal.user_id == user_id, Meal.eaten_at >= start_utc, Meal.eaten_at < end_utc)
        .order_by(Meal.eaten_at.asc())
    )
    return list(db.scalars(stmt))


# ---------- chuyển đổi sang dữ liệu trả về ----------


def item_to_dict(item: MealItem) -> dict:
    snapshot = item.nutrition_snapshot or {}
    name = snapshot.get("food_name") or (item.food.display_name if item.food else None)
    return {
        "id": item.id,
        "food_id": item.food_id,
        "food_name": name,
        "weight_grams": item.weight_grams,
        "quantity": item.quantity,
        "kcal": item.kcal,
        "protein_g": item.protein_g,
        "carbohydrate_g": item.carbohydrate_g,
        "fat_g": item.fat_g,
        "fiber_g": item.fiber_g,
        "sugar_g": item.sugar_g,
        "sodium_mg": item.sodium_mg,
        "kcal_source": item.kcal_source,
    }


def meal_totals(items: list[MealItem]) -> nutrition.DayTotals:
    rows = [
        {
            "energy_kcal": i.kcal,
            "protein_g": i.protein_g,
            "carbohydrate_g": i.carbohydrate_g,
            "fat_g": i.fat_g,
            "fiber_g": i.fiber_g,
            "sugar_g": i.sugar_g,
            "sodium_mg": i.sodium_mg,
        }
        for i in items
    ]
    return nutrition.aggregate(rows, MEAL_NUTRIENT_CODES)


def meal_to_dict(meal: Meal) -> dict:
    totals = meal_totals(meal.items)
    return {
        "id": meal.id,
        "eaten_at": meal.eaten_at,
        "eaten_at_local": utc_to_local(meal.eaten_at),
        "meal_type": meal.meal_type,
        "note": meal.note,
        "items": [item_to_dict(i) for i in meal.items],
        "totals": totals.as_dict(),
        "macro_energy_split": nutrition.macro_energy_split(totals.totals),
    }


def group_by_local_day(meals: list[Meal]) -> dict[date, list[Meal]]:
    grouped: dict[date, list[Meal]] = {}
    for meal in meals:
        grouped.setdefault(local_date_of(meal.eaten_at), []).append(meal)
    return grouped
