"""Nghiệp vụ thống kê dinh dưỡng theo ngày / tuần / tháng.

Tất cả đều lọc theo user_id lấy từ phiên server. Ngày được hiểu theo giờ địa phương
(UTC+07:00, xem app/core/timeutil.py), dữ liệu lưu UTC.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.timeutil import date_range, local_day_bounds, local_today, local_week_bounds
from app.core.utils import utcnow
from app.models import Meal
from app.services import meal_service, nutrition

TARGET_KEYS = ("energy_kcal", "protein_g", "carbohydrate_g", "fat_g", "fiber_g")


def _totals_for_meals(meals: list[Meal]) -> nutrition.DayTotals:
    rows = []
    for meal in meals:
        for item in meal.items:
            rows.append(
                {
                    "energy_kcal": item.kcal,
                    "protein_g": item.protein_g,
                    "carbohydrate_g": item.carbohydrate_g,
                    "fat_g": item.fat_g,
                    "fiber_g": item.fiber_g,
                    "sugar_g": item.sugar_g,
                    "sodium_mg": item.sodium_mg,
                }
            )
    return nutrition.aggregate(rows, meal_service.MEAL_NUTRIENT_CODES)


def daily(db: Session, user_id: int, day: date | None = None, daily_kcal_target: float | None = None) -> dict:
    day = day or local_today()
    start, end = local_day_bounds(day)
    meals = meal_service.meals_in_range(db, user_id, start, end)
    totals = _totals_for_meals(meals)

    by_type: dict[str, dict] = {}
    for meal in meals:
        bucket = by_type.setdefault(
            meal.meal_type,
            {"meal_type": meal.meal_type, "calories": 0.0, "protein_g": 0.0,
             "carbohydrate_g": 0.0, "fat_g": 0.0, "item_count": 0,
             "has_missing_energy": False},
        )
        for item in meal.items:
            bucket["item_count"] += 1
            if item.kcal is None:
                bucket["has_missing_energy"] = True
            else:
                bucket["calories"] += float(item.kcal)
            for key in ("protein_g", "carbohydrate_g", "fat_g"):
                value = getattr(item, key)
                if value is not None:
                    bucket[key] += float(value)

    breakdown = []
    for meal_type in ("breakfast", "lunch", "dinner", "snack"):
        if meal_type not in by_type:
            continue
        bucket = by_type[meal_type]
        breakdown.append(
            {
                "meal_type": meal_type,
                "calories": round(bucket["calories"], 1),
                # Báo rõ khi trong bữa có món thiếu số liệu năng lượng -> tổng bị thiếu
                "calories_incomplete": bucket["has_missing_energy"],
                "protein_g": round(bucket["protein_g"], 2),
                "carbohydrate_g": round(bucket["carbohydrate_g"], 2),
                "fat_g": round(bucket["fat_g"], 2),
                "item_count": bucket["item_count"],
            }
        )

    return {
        "date_local": day,
        "timezone": "UTC+07:00",
        "totals": totals.as_dict(),
        "by_meal_type": breakdown,
        "macro_energy_split": nutrition.macro_energy_split(totals.totals),
        "target": nutrition.target_progress(totals.totals.get("energy_kcal"), daily_kcal_target),
    }


def _period(db: Session, user_id: int, start: date, end: date, label: str,
            daily_kcal_target: float | None = None) -> dict:
    start_utc, _ = local_day_bounds(start)
    _, end_utc = local_day_bounds(end)
    meals = meal_service.meals_in_range(db, user_id, start_utc, end_utc)
    grouped = meal_service.group_by_local_day(meals)

    series: list[dict] = []
    all_rows: list[dict] = []
    for day in date_range(start, end):
        day_meals = grouped.get(day, [])
        totals = _totals_for_meals(day_meals)
        item_count = sum(len(m.items) for m in day_meals)
        rows = [
            {"energy_kcal": i.kcal, "protein_g": i.protein_g, "carbohydrate_g": i.carbohydrate_g,
             "fat_g": i.fat_g, "fiber_g": i.fiber_g, "sugar_g": i.sugar_g, "sodium_mg": i.sodium_mg}
            for m in day_meals for i in m.items
        ]
        all_rows.extend(rows)
        series.append(
            {
                "date_local": day,
                "kcal": nutrition.round_nutrients({"energy_kcal": totals.totals["energy_kcal"]})["energy_kcal"],
                "protein_g": nutrition.round_nutrients({"protein_g": totals.totals["protein_g"]})["protein_g"],
                "carbohydrate_g": nutrition.round_nutrients({"carbohydrate_g": totals.totals["carbohydrate_g"]})["carbohydrate_g"],
                "fat_g": nutrition.round_nutrients({"fat_g": totals.totals["fat_g"]})["fat_g"],
                "fiber_g": nutrition.round_nutrients({"fiber_g": totals.totals["fiber_g"]})["fiber_g"],
                "item_count": item_count,
            }
        )

    overall = nutrition.aggregate(all_rows, meal_service.MEAL_NUTRIENT_CODES)
    days_with_data = sum(1 for point in series if point["item_count"] > 0)
    total_days = len(series) or 1
    average = {}
    for code in TARGET_KEYS:
        value = overall.totals.get(code)
        average[code] = None if value is None else round(value / total_days, 2)

    return {
        "period": label,
        "start_date": start,
        "end_date": end,
        "timezone": "UTC+07:00",
        "series": series,
        "totals": overall.as_dict(),
        "average_per_day": average,
        "days_with_data": days_with_data,
        "target": nutrition.target_progress(overall.totals.get("energy_kcal"), 
                                            (daily_kcal_target * total_days) if daily_kcal_target else None),
    }


def weekly(db: Session, user_id: int, any_day: date | None = None, daily_kcal_target: float | None = None) -> dict:
    reference = any_day or local_today()
    start, end = local_week_bounds(reference)
    return _period(db, user_id, start, end, "weekly", daily_kcal_target)


def monthly(db: Session, user_id: int, year: int | None = None, month: int | None = None,
            daily_kcal_target: float | None = None) -> dict:
    today = local_today()
    year = year or today.year
    month = month or today.month
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    return _period(db, user_id, start, end, "monthly", daily_kcal_target)
