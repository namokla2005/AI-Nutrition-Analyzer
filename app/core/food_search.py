"""DDL SQLite FTS5 cho chỉ mục tra cứu tên thực phẩm và tên thay thế."""
from __future__ import annotations

from sqlalchemy.engine import Connection

FOOD_SEARCH_CREATE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS food_search USING fts5(
    food_id UNINDEXED,
    name_norm,
    alias_norm,
    suffix_norm,
    tokenize='unicode61 remove_diacritics 2'
)
"""

FOOD_SEARCH_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS food_search_documents AS
SELECT f.id AS food_id,
       COALESCE(f.name_normalized, '') AS name_norm,
       COALESCE((
           SELECT group_concat(a.alias_normalized, ' ')
           FROM food_aliases AS a
           WHERE a.food_id = f.id
       ), '') AS alias_norm
FROM foods AS f
"""

_SUFFIXES_SQL = """
COALESCE((
    WITH RECURSIVE
    words(rest, word) AS (
        SELECT trim(d.name_norm || ' ' || d.alias_norm) || ' ', ''
        UNION ALL
        SELECT ltrim(substr(rest, instr(rest, ' ') + 1)),
               substr(rest, 1, instr(rest, ' ') - 1)
        FROM words WHERE rest <> ''
    ),
    suffixes(suffix) AS (
        SELECT word FROM words WHERE word <> ''
        UNION ALL
        SELECT substr(suffix, 2) FROM suffixes WHERE length(suffix) > 1
    )
    SELECT group_concat(suffix, ' ') FROM suffixes
), '')
"""

FOOD_SEARCH_BACKFILL_SQL = f"""
INSERT INTO food_search(rowid, food_id, name_norm, alias_norm, suffix_norm)
SELECT d.food_id, d.food_id, d.name_norm, d.alias_norm, {_SUFFIXES_SQL}
FROM food_search_documents AS d
WHERE NOT EXISTS (SELECT 1 FROM food_search AS s WHERE s.rowid = d.food_id)
"""

def _rebuild_sql(food_id: str) -> str:
    return f"""
        INSERT INTO food_search(rowid, food_id, name_norm, alias_norm, suffix_norm)
        SELECT d.food_id, d.food_id, d.name_norm, d.alias_norm, {_SUFFIXES_SQL}
        FROM food_search_documents AS d WHERE d.food_id = {food_id};
    """


FOOD_SEARCH_TRIGGER_SQL = (
    f"""
    CREATE TRIGGER IF NOT EXISTS foods_fts_ai AFTER INSERT ON foods BEGIN
        {_rebuild_sql("NEW.id")}
    END
    """,
    f"""
    CREATE TRIGGER IF NOT EXISTS foods_fts_au AFTER UPDATE OF name_normalized ON foods BEGIN
        DELETE FROM food_search WHERE rowid = OLD.id;
        {_rebuild_sql("NEW.id")}
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS foods_fts_ad AFTER DELETE ON foods BEGIN
        DELETE FROM food_search WHERE rowid = OLD.id;
    END
    """,
    f"""
    CREATE TRIGGER IF NOT EXISTS food_aliases_fts_ai AFTER INSERT ON food_aliases BEGIN
        DELETE FROM food_search WHERE rowid = NEW.food_id;
        {_rebuild_sql("NEW.food_id")}
    END
    """,
    f"""
    CREATE TRIGGER IF NOT EXISTS food_aliases_fts_au
    AFTER UPDATE OF food_id, alias_normalized ON food_aliases BEGIN
        DELETE FROM food_search WHERE rowid = OLD.food_id;
        {_rebuild_sql("OLD.food_id")}
        DELETE FROM food_search WHERE rowid = NEW.food_id;
        {_rebuild_sql("NEW.food_id")}
    END
    """,
    f"""
    CREATE TRIGGER IF NOT EXISTS food_aliases_fts_ad AFTER DELETE ON food_aliases BEGIN
        DELETE FROM food_search WHERE rowid = OLD.food_id;
        {_rebuild_sql("OLD.food_id")}
    END
    """,
)

FOOD_SEARCH_TRIGGER_NAMES = (
    "foods_fts_ai",
    "foods_fts_au",
    "foods_fts_ad",
    "food_aliases_fts_ai",
    "food_aliases_fts_au",
    "food_aliases_fts_ad",
)


def create_food_search(_target, connection: Connection, **_kwargs) -> None:
    """Tạo và nạp chỉ mục FTS sau ``Base.metadata.create_all`` trên SQLite."""
    if connection.dialect.name != "sqlite":
        return
    connection.exec_driver_sql(FOOD_SEARCH_CREATE_SQL)
    connection.exec_driver_sql(FOOD_SEARCH_VIEW_SQL)
    connection.exec_driver_sql(FOOD_SEARCH_BACKFILL_SQL)
    for statement in FOOD_SEARCH_TRIGGER_SQL:
        connection.exec_driver_sql(statement)
