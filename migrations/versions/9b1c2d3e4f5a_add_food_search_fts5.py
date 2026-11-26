"""add FTS5 food search index

Revision ID: 9b1c2d3e4f5a
Revises: 827db6071a8d
Create Date: 2026-11-27

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


revision: str = "9b1c2d3e4f5a"
down_revision: str | None = "827db6071a8d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(FOOD_SEARCH_CREATE_SQL.replace("IF NOT EXISTS ", ""))
    bind.exec_driver_sql(FOOD_SEARCH_VIEW_SQL.replace("IF NOT EXISTS ", ""))
    bind.exec_driver_sql(FOOD_SEARCH_BACKFILL_SQL)
    for statement in FOOD_SEARCH_TRIGGER_SQL:
        bind.exec_driver_sql(statement.replace("IF NOT EXISTS ", ""))


def downgrade() -> None:
    bind = op.get_bind()
    for name in FOOD_SEARCH_TRIGGER_NAMES:
        bind.exec_driver_sql(f"DROP TRIGGER IF EXISTS {name}")
    bind.exec_driver_sql("DROP VIEW IF EXISTS food_search_documents")
    bind.exec_driver_sql("DROP TABLE IF EXISTS food_search")
