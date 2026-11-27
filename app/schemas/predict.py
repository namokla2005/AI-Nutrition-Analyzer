"""Pydantic schemas cho dự đoán (ảnh và dinh dưỡng)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TopKItem(BaseModel):
    rank: int
    label: str
    display_label: str | None = None
    confidence: float


class SuggestedFood(BaseModel):
    food_id: int
    name: str
    energy_kcal_per_100g: float | None = None
    category: str | None = None
    cooking_state: str | None = None


class PortionOut(BaseModel):
    """Khẩu phần tham khảo cho một suất ăn + giá trị dinh dưỡng tính theo khẩu phần đó."""

    label: str
    display_label: str | None = None
    grams: float
    is_reference_portion: bool = True
    note: str
    food: dict | None = None
    nutrients: dict = Field(default_factory=dict)
    missing_nutrients: list[str] = Field(default_factory=list)
    nutrient_source: str | None = None


class ImagePredictionOut(BaseModel):
    image_id: int
    model: dict = Field(default_factory=dict)
    top_k: list[TopKItem] = Field(default_factory=list)
    confidence: float | None = None
    needs_confirmation: bool
    message: str
    suggested_foods: list[SuggestedFood] = Field(default_factory=list)
    portion: PortionOut | None = None
    latency_ms: int | None = None


class NutritionPredictIn(BaseModel):
    """Ước lượng năng lượng cho một thực phẩm.

    - food_id: ưu tiên số liệu đo trong database (khuyến nghị dùng cách này).
    - Nếu thực phẩm thiếu số liệu năng lượng, backend mới dùng model hồi quy
      (khi model đã được huấn luyện) và ghi rõ đó là giá trị ước lượng.
    """

    food_id: int | None = Field(default=None, gt=0)
    weight_grams: float | None = Field(default=None, gt=0, le=20000,
                                       description="Nếu có, trả luôn giá trị cho khối lượng này")
    features: dict[str, float | str | None] | None = Field(
        default=None, description="Feature thô khi muốn dự đoán trực tiếp (protein_g, fat_g, ...)"
    )


class NutritionPredictOut(BaseModel):
    food_id: int | None = None
    food_name: str | None = None
    source: str  # database | model | unavailable
    energy_kcal_per_100g: float | None = None
    weight_grams: float | None = None
    energy_kcal_for_weight: float | None = None
    model: dict = Field(default_factory=dict)
    message: str
    missing_features: list[str] = Field(default_factory=list)


class ModelStatusOut(BaseModel):
    image_classifier: dict
    regression: dict
    checked_at: datetime
