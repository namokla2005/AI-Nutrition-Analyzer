"""Bảng dữ liệu thực phẩm: food_sources, foods, nutrients, food_nutrients, food_aliases, food_images."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

COOKING_STATES = ("raw", "cooked", "processed", "unknown")


class FoodSource(Base, TimestampMixin):
    """Nguồn dữ liệu tách riêng khỏi thông tin thực phẩm (yêu cầu §7.5)."""

    __tablename__ = "food_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)  # usda / openfoodfacts / vn_fct / manual
    url: Mapped[str | None] = mapped_column(String(400))
    license: Mapped[str | None] = mapped_column(String(160))
    license_url: Mapped[str | None] = mapped_column(String(400))
    citation: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime)
    version_label: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)

    foods: Mapped[list["Food"]] = relationship(back_populates="source")


class Nutrient(Base):
    """Danh mục chất dinh dưỡng (đơn vị chuẩn hóa)."""

    __tablename__ = "nutrients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)
    name_vi: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)  # kcal / g / mg / µg
    is_energy: Mapped[bool] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    food_nutrients: Mapped[list["FoodNutrient"]] = relationship(back_populates="nutrient")


class Food(Base, TimestampMixin):
    """Một loại thực phẩm/món ăn. Giá trị dinh dưỡng chuẩn nằm ở food_nutrients."""

    __tablename__ = "foods"
    __table_args__ = (
        Index("ix_foods_name_normalized", "name_normalized"),
        Index("ix_foods_category_state", "category", "cooking_state"),
        UniqueConstraint("source_id", "source_ref", name="uq_foods_source_ref"),
        CheckConstraint(
            "cooking_state IN ('raw','cooked','processed','unknown')",
            name="ck_foods_cooking_state",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("food_sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    source_ref: Mapped[str | None] = mapped_column(String(120))  # FDC ID / OFF barcode
    name_vi: Mapped[str | None] = mapped_column(String(240))
    name_en: Mapped[str | None] = mapped_column(String(240))
    name_normalized: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    food_group: Mapped[str | None] = mapped_column(String(80))  # pnns_groups_1 / nhóm VN
    cooking_state: Mapped[str] = mapped_column(
        String(16), default="unknown", server_default="unknown", nullable=False
    )
    # Bản sao tiện lợi của năng lượng (kcal/100g) để tra cứu/sắp xếp nhanh.
    # Nguồn chuẩn vẫn là food_nutrients (xem docs/TECHNICAL_DECISIONS.md).
    energy_kcal_per_100g: Mapped[float | None] = mapped_column(Float, index=True)
    default_serving_g: Mapped[float | None] = mapped_column(Float)
    image_class: Mapped[str | None] = mapped_column(String(64), index=True)  # nhãn nhận diện ảnh
    is_verified: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    data_note: Mapped[str | None] = mapped_column(Text)

    source: Mapped[FoodSource] = relationship(back_populates="foods")
    nutrients: Mapped[list["FoodNutrient"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )
    aliases: Mapped[list["FoodAlias"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        return self.name_vi or self.name_en or f"Food#{self.id}"


class FoodNutrient(Base):
    """Giá trị dinh dưỡng trên 100 g. amount_per_100g = None nghĩa là THIẾU (không phải 0)."""

    __tablename__ = "food_nutrients"
    __table_args__ = (
        UniqueConstraint("food_id", "nutrient_id", name="uq_food_nutrient"),
        Index("ix_food_nutrients_nutrient", "nutrient_id"),
        CheckConstraint(
            "amount_per_100g IS NULL OR amount_per_100g >= 0",
            name="ck_food_nutrients_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_id: Mapped[int] = mapped_column(
        ForeignKey("foods.id", ondelete="CASCADE"), index=True, nullable=False
    )
    nutrient_id: Mapped[int] = mapped_column(
        ForeignKey("nutrients.id", ondelete="RESTRICT"), nullable=False
    )
    amount_per_100g: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    data_quality: Mapped[str | None] = mapped_column(String(24))  # measured/derived/estimated
    source_note: Mapped[str | None] = mapped_column(String(240))

    food: Mapped[Food] = relationship(back_populates="nutrients")
    nutrient: Mapped[Nutrient] = relationship(back_populates="food_nutrients")


class FoodAlias(Base):
    """Tên gọi khác (tiếng Việt không dấu, tiếng Anh, tên thương mại) để tìm kiếm."""

    __tablename__ = "food_aliases"
    __table_args__ = (Index("ix_food_aliases_normalized", "alias_normalized"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_id: Mapped[int] = mapped_column(
        ForeignKey("foods.id", ondelete="CASCADE"), index=True, nullable=False
    )
    alias: Mapped[str] = mapped_column(String(240), nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(240), nullable=False)
    lang: Mapped[str] = mapped_column(String(8), default="vi", server_default="vi", nullable=False)

    food: Mapped[Food] = relationship(back_populates="aliases")


class FoodImage(Base, TimestampMixin):
    """Ảnh người dùng tải lên (chính sách lưu trữ có thời hạn, xem retained_until)."""

    __tablename__ = "food_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id", ondelete="SET NULL"))
    rel_path: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(200))
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(
        String(24), default="recognition", server_default="recognition", nullable=False
    )
    retained_until: Mapped[datetime | None] = mapped_column(DateTime)
