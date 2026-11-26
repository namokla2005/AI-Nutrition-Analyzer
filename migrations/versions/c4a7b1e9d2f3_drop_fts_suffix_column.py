"""bo cot suffix_norm khoi chi muc FTS5 (khong con khop giua chuoi)

Revision ID: c4a7b1e9d2f3
Revises: 9b1c2d3e4f5a
Create Date: 2026-11-28

Ly do: cot `suffix_norm` chua MOI hau to cua moi tu trong ten (sinh bang truy van de quy) nen
- CSDL phinh them 66 MB (68,8 MB -> 135,1 MB, +96%);
- khop bay ngay ket qua dau: 'nem ran' -> "Medite-rran-e", 'ga' -> "Grow & ga-in".
Da bo cot; tra cuu dung khop tien to theo tung tu tren hai cot name_norm/alias_norm.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.core.food_search import (
    FOOD_SEARCH_BACKFILL_SQL,
    FOOD_SEARCH_CREATE_SQL,
    FOOD_SEARCH_TRIGGER_NAMES,
    FOOD_SEARCH_TRIGGER_SQL,
    FOOD_SEARCH_VIEW_SQL,
)


revision: str = "c4a7b1e9d2f3"
down_revision: str | None = "9b1c2d3e4f5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _drop_index_objects() -> None:
    bind = op.get_bind()
    for name in FOOD_SEARCH_TRIGGER_NAMES:
        bind.exec_driver_sql(f"DROP TRIGGER IF EXISTS {name}")
    bind.exec_driver_sql("DROP VIEW IF EXISTS food_search_documents")
    bind.exec_driver_sql("DROP TABLE IF EXISTS food_search")


def _create_index_objects() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(FOOD_SEARCH_CREATE_SQL.replace("IF NOT EXISTS ", ""))
    bind.exec_driver_sql(FOOD_SEARCH_VIEW_SQL.replace("IF NOT EXISTS ", ""))
    bind.exec_driver_sql(FOOD_SEARCH_BACKFILL_SQL)
    for statement in FOOD_SEARCH_TRIGGER_SQL:
        bind.exec_driver_sql(statement.replace("IF NOT EXISTS ", ""))


def upgrade() -> None:
    # Dựng lại bảng ảo không có cột suffix_norm rồi nạp lại toàn bộ tên thực phẩm.
    _drop_index_objects()
    _create_index_objects()


def downgrade() -> None:
    # Không khôi phục cột hậu tố (đã chứng minh gây lỗi kết quả); chỉ dựng lại chỉ mục hiện hành.
    _drop_index_objects()
    _create_index_objects()
