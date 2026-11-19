"""Bảng nhật ký ăn uống: meals, meal_items (có snapshot dinh dưỡng)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")


class Meal(Base, TimestampMixin):
    __tablename__ = "meals"
    __table_args__ = (
        Index("ix_meals_user_eaten_at", "user_id", "eaten_at"),
        CheckConstraint(
            "meal_type IN ('breakfast','lunch','dinner','snack')", name="ck_meals_type"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    eaten_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="meals")  # noqa: F821
    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan", order_by="MealItem.id"
    )


class MealItem(Base, TimestampMixin):
    """Một dòng trong bữa ăn.

    Giá trị kcal/protein/... là SNAPSHOT tại thời điểm ghi nhận (§7.4) - để báo cáo
    lịch sử không đổi khi dữ liệu thực phẩm nguồn được cập nhật về sau.
    """

    __tablename__ = "meal_items"
    __table_args__ = (Index("ix_meal_items_food", "food_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    food_id: Mapped[int] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False
    )
    weight_grams: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0, server_default="1", nullable=False)

    # Snapshot năng lượng/dinh dưỡng cho toàn bộ khối lượng đã ăn
    kcal: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    carbohydrate_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    fiber_g: Mapped[float | None] = mapped_column(Float)
    sugar_g: Mapped[float | None] = mapped_column(Float)
    sodium_mg: Mapped[float | None] = mapped_column(Float)

    # Snapshot chi tiết + nguồn dữ liệu tại thời điểm ghi nhận
    nutrition_snapshot: Mapped[dict | None] = mapped_column(JSON)
    kcal_source: Mapped[str | None] = mapped_column(String(24))  # measured/model/estimated

    meal: Mapped[Meal] = relationship(back_populates="items")
    food: Mapped["Food"] = relationship()  # noqa: F821
