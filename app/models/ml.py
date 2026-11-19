"""Bảng quản lý phiên bản mô hình và lịch sử dự đoán."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ModelVersion(Base, TimestampMixin):
    """metadata của một model đã huấn luyện (ảnh hoặc hồi quy)."""

    __tablename__ = "model_versions"
    __table_args__ = (Index("ix_model_versions_kind_active", "kind", "is_active"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)   # image_classifier / regression
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    algorithm: Mapped[str | None] = mapped_column(String(80))      # mobilenet_v3_small / random_forest ...
    artifact_path: Mapped[str | None] = mapped_column(String(300))
    metrics: Mapped[dict | None] = mapped_column(JSON)             # MAE/RMSE/R2/accuracy... (số thực tế)
    labels: Mapped[list | None] = mapped_column(JSON)              # danh sách lớp cho model ảnh
    feature_names: Mapped[list | None] = mapped_column(JSON)       # danh sách feature cho model hồi quy
    dataset_note: Mapped[str | None] = mapped_column(Text)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class Prediction(Base, TimestampMixin):
    """Lịch sử dự đoán (nhận diện ảnh / hồi quy calo)."""

    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_user_kind", "user_id", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)   # image / nutrition
    image_id: Mapped[int | None] = mapped_column(ForeignKey("food_images.id", ondelete="SET NULL"))
    features: Mapped[dict | None] = mapped_column(JSON)
    top_k: Mapped[list | None] = mapped_column(JSON)               # [{label, confidence}, ...]
    confidence: Mapped[float | None] = mapped_column(Float)
    predicted_value: Mapped[float | None] = mapped_column(Float)
    user_confirmed_label: Mapped[str | None] = mapped_column(String(64))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    model_version: Mapped[ModelVersion | None] = relationship()
