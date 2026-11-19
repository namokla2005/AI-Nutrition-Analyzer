"""Pydantic schemas cho nhật ký ăn uống và thống kê."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class MealItemIn(BaseModel):
    food_id: int = Field(gt=0)
    weight_grams: float = Field(gt=0, le=20000, description="Khối lượng mỗi phần (gam)")
    quantity: float = Field(default=1.0, gt=0, le=100, description="Số phần")


class MealCreateIn(BaseModel):
    meal_type: MealType
    eaten_at: datetime | None = Field(
        default=None, description="Mốc thời gian UTC; để trống = thời điểm hiện tại"
    )
    note: str | None = Field(default=None, max_length=500)
    items: list[MealItemIn] = Field(min_length=1, max_length=50)


class MealUpdateIn(BaseModel):
    meal_type: MealType | None = None
    eaten_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)
    items: list[MealItemIn] | None = Field(default=None, min_length=1, max_length=50)


class MealItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    food_id: int
    food_name: str | None = None
    weight_grams: float
    quantity: float
    kcal: float | None = None
    protein_g: float | None = None
    carbohydrate_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None
    kcal_source: str | None = None


class TotalsOut(BaseModel):
    totals: dict[str, float | None]
    missing_fields: list[str] = Field(default_factory=list)
    item_count: int = 0
    items_without_energy: int = 0


class MealOut(BaseModel):
    id: int
    eaten_at: datetime
    eaten_at_local: datetime
    meal_type: str
    note: str | None = None
    items: list[MealItemOut] = Field(default_factory=list)
    totals: TotalsOut
    macro_energy_split: dict = Field(default_factory=dict)


class MealListOut(BaseModel):
    items: list[MealOut]
    total: int
    limit: int
    offset: int


class MealTypeBreakdown(BaseModel):
    meal_type: str
    calories: float | None = None
    protein_g: float | None = None
    carbohydrate_g: float | None = None
    fat_g: float | None = None
    item_count: int = 0


class DailyStatsOut(BaseModel):
    date_local: date
    timezone: str
    totals: TotalsOut
    by_meal_type: list[MealTypeBreakdown] = Field(default_factory=list)
    macro_energy_split: dict = Field(default_factory=dict)
    target: dict = Field(default_factory=dict)


class SeriesPoint(BaseModel):
    date_local: date
    kcal: float | None = None
    protein_g: float | None = None
    carbohydrate_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    item_count: int = 0


class PeriodStatsOut(BaseModel):
    period: str
    start_date: date
    end_date: date
    timezone: str
    series: list[SeriesPoint] = Field(default_factory=list)
    totals: TotalsOut
    average_per_day: dict[str, float | None] = Field(default_factory=dict)
    days_with_data: int = 0
    target: dict = Field(default_factory=dict)
