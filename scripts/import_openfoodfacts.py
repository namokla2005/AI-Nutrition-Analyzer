"""Import the curated Open Food Facts CSV into the frozen food schema.

The importer streams the CSV, commits in bounded batches, and upserts foods by
(source_id, source_ref). Open Food Facts sodium is expressed in g/100 g and is
converted to the application's sodium_mg unit by multiplying by 1,000.

Missing nutrient fields are persisted as NULL FoodNutrient values, never as 0.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.utils import normalize_name  # noqa: E402
from app.models import Food, FoodSource, Nutrient  # noqa: E402
from app.repositories.food_repository import FoodRepository  # noqa: E402

DEFAULT_CSV = BASE_DIR / "data" / "external" / "openfoodfacts" / "off_subset.csv"
SOURCE_CODE = "openfoodfacts"
EXPECTED_COLUMNS = [
    "code",
    "product_name",
    "brands",
    "countries_tags",
    "countries_en",
    "pnns_groups_1",
    "categories_en",
    "energy-kcal_100g",
    "proteins_100g",
    "carbohydrates_100g",
    "fat_100g",
    "fiber_100g",
    "sugars_100g",
    "sodium_100g",
]
# nutrient code -> (OFF CSV field, application unit, OFF-to-application multiplier)
NUTRIENT_MAPPING = {
    "energy_kcal": ("energy-kcal_100g", "kcal", 1.0),
    "protein_g": ("proteins_100g", "g", 1.0),
    "carbohydrate_g": ("carbohydrates_100g", "g", 1.0),
    "fat_g": ("fat_100g", "g", 1.0),
    "fiber_g": ("fiber_100g", "g", 1.0),
    "sugar_g": ("sugars_100g", "g", 1.0),
    "sodium_mg": ("sodium_100g", "mg", 1000.0),
}


def parse_amount(raw: str | None, *, field: str) -> float | None:
    """Parse one OFF amount; blank means missing, while invalid values fail."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"{field}: giá trị không phải số {text!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"{field}: giá trị không hữu hạn {text!r}")
    if value < 0:
        raise ValueError(f"{field}: giá trị âm {text!r}")
    return value


def nutrient_values(row: Mapping[str, str]) -> dict[str, float | None]:
    """Map OFF nutrients to application codes, including g-to-mg sodium."""
    values: dict[str, float | None] = {}
    for code, (field, _unit, multiplier) in NUTRIENT_MAPPING.items():
        value = parse_amount(row.get(field), field=field)
        values[code] = None if value is None else value * multiplier
    return values


def _optional_text(raw: str | None, limit: int) -> str | None:
    text = (raw or "").strip()
    return text[:limit] if text else None


def food_fields(row: Mapping[str, str]) -> dict[str, str | None]:
    """Build Food fields according to the frozen Open Food Facts mapping."""
    source_ref = (row.get("code") or "").strip()
    if not source_ref:
        raise ValueError("code: thiếu barcode")
    if len(source_ref) > 120:
        raise ValueError("code: barcode dài quá 120 ký tự")

    product_name = (row.get("product_name") or "").strip()
    brand = (row.get("brands") or "").strip()
    searchable_name = f"{brand} {product_name}" if brand else product_name

    return {
        "source_ref": source_ref,
        "name_en": product_name[:240] or None,
        "name_vi": None,
        "name_normalized": normalize_name(searchable_name)[:240],
        "food_group": _optional_text(row.get("pnns_groups_1"), 80),
        "category": _optional_text(row.get("categories_en"), 80),
        "cooking_state": "processed",
    }


def import_csv(csv_path: Path, batch_size: int) -> dict[str, object]:
    if batch_size < 1:
        raise ValueError("batch_size phải lớn hơn 0")

    summary: dict[str, object] = {
        "rows_read": 0,
        "foods_inserted": 0,
        "foods_updated": 0,
        "foods_skipped": 0,
        "skip_reasons": Counter(),
        "batches_committed": 0,
    }

    with SessionLocal() as db:
        source = db.scalar(select(FoodSource).where(FoodSource.code == SOURCE_CODE))
        if source is None:
            raise RuntimeError(f"Không tìm thấy food_sources.code={SOURCE_CODE!r}")
        source_id = source.id

        nutrient_rows = list(
            db.scalars(select(Nutrient).where(Nutrient.code.in_(NUTRIENT_MAPPING))).all()
        )
        nutrient_by_code = {row.code: (row.id, row.unit) for row in nutrient_rows}
        missing_codes = sorted(set(NUTRIENT_MAPPING) - set(nutrient_by_code))
        if missing_codes:
            raise RuntimeError(f"Thiếu nutrient code đã seed: {', '.join(missing_codes)}")
        for code, (_field, expected_unit, _multiplier) in NUTRIENT_MAPPING.items():
            actual_unit = nutrient_by_code[code][1]
            if actual_unit != expected_unit:
                raise RuntimeError(
                    f"Sai đơn vị nutrient {code}: DB={actual_unit!r}, cần={expected_unit!r}"
                )

        repo = FoodRepository(db)
        pending_rows = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != EXPECTED_COLUMNS:
                raise RuntimeError(
                    "CSV không đúng 14 cột mong đợi: "
                    f"nhận={reader.fieldnames!r}, cần={EXPECTED_COLUMNS!r}"
                )

            for row in reader:
                summary["rows_read"] = int(summary["rows_read"]) + 1
                try:
                    fields = food_fields(row)
                    values = nutrient_values(row)
                except ValueError as exc:
                    summary["foods_skipped"] = int(summary["foods_skipped"]) + 1
                    reason = str(exc)
                    skip_reasons = summary["skip_reasons"]
                    assert isinstance(skip_reasons, Counter)
                    skip_reasons[reason] += 1
                    continue

                food = repo.find_by_source_ref(source_id, str(fields["source_ref"]))
                if food is None:
                    food = Food(source_id=source_id, **fields)
                    db.add(food)
                    db.flush()
                    summary["foods_inserted"] = int(summary["foods_inserted"]) + 1
                else:
                    for key, value in fields.items():
                        setattr(food, key, value)
                    db.flush()
                    summary["foods_updated"] = int(summary["foods_updated"]) + 1

                for code, amount in values.items():
                    nutrient_id, unit = nutrient_by_code[code]
                    repo.upsert_nutrient(
                        food.id,
                        nutrient_id,
                        amount,
                        unit,
                        quality="reported",
                    )
                repo.sync_energy_cache(food.id)

                brand = (row.get("brands") or "").strip()
                if brand:
                    repo.add_alias(food.id, brand[:240], lang="en")

                pending_rows += 1
                if pending_rows >= batch_size:
                    db.commit()
                    db.expunge_all()
                    summary["batches_committed"] = int(summary["batches_committed"]) + 1
                    pending_rows = 0

        if pending_rows:
            db.commit()
            summary["batches_committed"] = int(summary["batches_committed"]) + 1

    skip_reasons = summary["skip_reasons"]
    assert isinstance(skip_reasons, Counter)
    summary["skip_reasons"] = dict(sorted(skip_reasons.items()))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Đường dẫn off_subset.csv")
    parser.add_argument("--batch-size", type=int, default=500, help="Số sản phẩm mỗi commit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = args.csv.resolve()
    if not csv_path.is_file():
        print(f"[ERROR] Không tìm thấy CSV: {csv_path}", file=sys.stderr)
        return 2

    rendered_url = engine.url.render_as_string(hide_password=True)
    database_name = engine.url.database
    resolved_path = Path(database_name).resolve() if database_name else None
    print(f"[DB] engine_url={rendered_url}")
    print(f"[DB] resolved_path={resolved_path or '(không phải SQLite)'}")
    print(f"[INPUT] csv={csv_path}")
    try:
        summary = import_csv(csv_path, args.batch_size)
    except Exception as exc:
        print(f"[ERROR] Import thất bại: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
