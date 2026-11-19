"""Pydantic schemas cho thực phẩm, tra cứu và tính khẩu phần."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NutrientValueOut(BaseModel):
    code: str
    name_vi: str
    unit: str
    amount_per_100g: float | None = None
    data_quality: str | None = None


class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_vi: str | None = None
    name_en: str | None = None
    category: str | None = None
    food_group: str | None = None
    cooking_state: str
    energy_kcal_per_100g: float | None = None
    default_serving_g: float | None = None
    source_code: str | None = None
    is_verified: bool = False


class FoodDetailOut(FoodOut):
    source_ref: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_license: str | None = None
    image_class: str | None = None
    nutrients: list[NutrientValueOut] = Field(default_factory=list)


class FoodListOut(BaseModel):
    items: list[FoodOut]
    total: int
    limit: int
    offset: int


class FoodCreateRequest(BaseModel):
    """Tạo thực phẩm mới (nhập tay). Bắt buộc khai báo nguồn dữ liệu để truy vết."""

    name_vi: str | None = Field(default=None, max_length=240)
    name_en: str | None = Field(default=None, max_length=240)
    category: str | None = Field(default=None, max_length=80)
    food_group: str | None = Field(default=None, max_length=80)
    cooking_state: str = Field(default="unknown", pattern="^(raw|cooked|processed|unknown)$")
    energy_kcal_per_100g: float | None = Field(default=None, ge=0, le=1000)
    protein_g_per_100g: float | None = Field(default=None, ge=0, le=100)
    fat_g_per_100g: float | None = Field(default=None, ge=0, le=100)
    carbohydrate_g_per_100g: float | None = Field(default=None, ge=0, le=100)
    fiber_g_per_100g: float | None = Field(default=None, ge=0, le=100)
    sugar_g_per_100g: float | None = Field(default=None, ge=0, le=100)
    sodium_mg_per_100g: float | None = Field(default=None, ge=0, le=40000)
    moisture_g_per_100g: float | None = Field(default=None, ge=0, le=100)
    ash_g_per_100g: float | None = Field(default=None, ge=0, le=100)
    source_name: str | None = Field(default=None, max_length=160)
    source_url: str | None = Field(default=None, max_length=400)
    source_note: str | None = Field(default=None, max_length=500)
    aliases: list[str] = Field(default_factory=list, max_length=20)


class PortionItemOut(BaseModel):
    code: str
    name_vi: str
    unit: str
    per_100g: float | None
    total: float | None


class PortionOut(BaseModel):
    food_id: int
    food_name: str
    weight_grams: float
    quantity: float
    total_weight_grams: float
    cooking_state: str
    caffeine: None = None  # (không dùng - giữ chỗ tránh nhầm với trường khác)
    values: list[PortionItemOut]
    missing_nutrients: list[str] = Field(default_factory=list)
    kcal: float | None = None
    kcal_source: str
    macro_energy_split: dict = Field(default_factory=dict)
    formula: str = "kcal = kcal_per_100g * weight_grams / 100"
