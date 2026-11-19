#!/usr/bin/env python3
"""Import three USDA FoodData Central CSV datasets into the application database.

The CSV files are streamed with ``utf-8-sig`` decoding and transactions are
committed in bounded batches.  The script is idempotent on
``(foods.source_id, foods.source_ref)`` and refuses to target the checked-in
``data/nutrition.db`` directly.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal, db_path_from_url, engine  # noqa: E402
from app.core.utils import normalize_name  # noqa: E402
from app.models import Food, FoodSource, Nutrient  # noqa: E402
from app.repositories.food_repository import FoodRepository  # noqa: E402

EXPECTED_REVISION = "827db6071a8d"
DEFAULT_DATA_ROOT = BASE_DIR / "data" / "external" / "usda"
PROTECTED_DB = (BASE_DIR / "data" / "nutrition.db").resolve()


@dataclass(frozen=True)
class Dataset:
    key: str
    folder: str
    source_code: str
    label: str


DATASETS = (
    Dataset(
        key="sr_legacy",
        folder="FoodData_Central_sr_legacy_food_csv_2018-04",
        source_code="usda_sr_legacy",
        label="USDA SR Legacy 2018-04",
    ),
    Dataset(
        key="foundation",
        folder="FoodData_Central_foundation_food_csv_2024-10-31",
        source_code="usda_foundation",
        label="USDA Foundation 2024-10-31",
    ),
    Dataset(
        key="survey",
        folder="FoodData_Central_survey_food_csv_2022-10-28",
        source_code="usda_fndds",
        label="USDA Survey/FNDDS 2022-10-28",
    ),
)


@dataclass(frozen=True)
class TargetSpec:
    code: str
    names: tuple[str, ...]
    usda_unit: str
    expected_nbr: str
    app_unit: str


TARGET_SPECS = (
    TargetSpec("energy_kcal", ("Energy",), "KCAL", "208", "kcal"),
    TargetSpec("energy_kj", ("Energy",), "KJ", "268", "kJ"),
    TargetSpec("protein_g", ("Protein",), "G", "203", "g"),
    TargetSpec("fat_g", ("Total lipid (fat)",), "G", "204", "g"),
    TargetSpec("carbohydrate_g", ("Carbohydrate, by difference",), "G", "205", "g"),
    TargetSpec("fiber_g", ("Fiber, total dietary",), "G", "291", "g"),
    TargetSpec("sugar_g", ("Sugars, Total", "Total Sugars"), "G", "269", "g"),
    TargetSpec("sodium_mg", ("Sodium, Na",), "MG", "307", "mg"),
    TargetSpec("moisture_g", ("Water",), "G", "255", "g"),
    TargetSpec("ash_g", ("Ash",), "G", "207", "g"),
    TargetSpec("cholesterol_mg", ("Cholesterol",), "MG", "601", "mg"),
    TargetSpec("calcium_mg", ("Calcium, Ca",), "MG", "301", "mg"),
    TargetSpec("iron_mg", ("Iron, Fe",), "MG", "303", "mg"),
    TargetSpec("potassium_mg", ("Potassium, K",), "MG", "306", "mg"),
    TargetSpec(
        "vitamin_c_mg",
        ("Vitamin C, total ascorbic acid",),
        "MG",
        "401",
        "mg",
    ),
)


@dataclass(frozen=True)
class ResolvedNutrient:
    code: str
    app_unit: str
    usda_id: str
    usda_nbr: str
    usda_name: str
    usda_unit: str
    expected_nbr: str


@dataclass
class DatasetStats:
    dataset: str
    source_code: str
    join_field: str = ""
    id_coverage: int = 0
    nutrient_nbr_coverage: int = 0
    observed_nutrient_keys: int = 0
    nutrient_mapping: list[dict[str, str]] = field(default_factory=list)
    mapping_mismatches: list[str] = field(default_factory=list)
    food_rows_read: int = 0
    foods_added: int = 0
    foods_updated: int = 0
    foods_skipped: int = 0
    aliases_added: int = 0
    raw_assigned: int = 0
    cooked_assigned: int = 0
    unknown_assigned: int = 0
    nutrient_rows_read: int = 0
    nutrient_rows_mapped: int = 0
    nutrient_rows_null: int = 0
    nutrient_rows_missing_food: int = 0
    atwater_rows_skipped: int = 0


_WS = re.compile(r"\s+")
_RAW = re.compile(r"\b(raw|uncooked)\b", re.IGNORECASE)
_COOKED = re.compile(
    r"\b(cooked|boiled|baked|grilled|roasted|fried|steamed|broiled|poached|simmered|microwaved)\b",
    re.IGNORECASE,
)


def clean(value: str | None) -> str:
    return (value or "").strip()


def normalized_pair(name: str, unit: str) -> tuple[str, str]:
    return (_WS.sub(" ", clean(name)).casefold(), clean(unit).upper())


def parse_amount(value: str | None) -> float | None:
    raw = clean(value)
    if not raw:
        return None
    amount = float(raw)
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f"Invalid USDA nutrient amount: {value!r}")
    return amount


def infer_cooking_state(description: str) -> str:
    has_raw = bool(_RAW.search(description))
    has_cooked = bool(_COOKED.search(description))
    if has_raw == has_cooked:
        return "unknown"
    return "raw" if has_raw else "cooked"


def category_for(category_id: str | None, description: str, categories: dict[str, str]) -> str | None:
    catalog = clean(categories.get(clean(category_id)))
    if catalog:
        return catalog[:80]
    first_clause = clean(description).split(",", 1)[0].strip()
    return first_clause[:80] or None


def read_csv(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def derive_nutrient_mapping(
    nutrient_rows: Iterable[dict[str, str]],
) -> tuple[dict[str, ResolvedNutrient], list[str]]:
    """Map by USDA (name, unit); nutrient numbers are only a cross-check."""
    targets: dict[tuple[str, str], TargetSpec] = {}
    for spec in TARGET_SPECS:
        for name in spec.names:
            targets[normalized_pair(name, spec.usda_unit)] = spec

    candidates: dict[str, list[ResolvedNutrient]] = {}
    mismatches: list[str] = []
    for row in nutrient_rows:
        spec = targets.get(normalized_pair(row.get("name", ""), row.get("unit_name", "")))
        if spec is None:
            continue
        usda_id = clean(row.get("id"))
        usda_nbr = clean(row.get("nutrient_nbr"))
        if not usda_id:
            mismatches.append(f"{spec.code}: matched row has no USDA id")
            continue
        resolved = ResolvedNutrient(
            code=spec.code,
            app_unit=spec.app_unit,
            usda_id=usda_id,
            usda_nbr=usda_nbr,
            usda_name=clean(row.get("name")),
            usda_unit=clean(row.get("unit_name")),
            expected_nbr=spec.expected_nbr,
        )
        candidates.setdefault(spec.code, []).append(resolved)
        if usda_nbr != spec.expected_nbr:
            mismatches.append(
                f"{spec.code}: candidate id={usda_id} expected nutrient_nbr={spec.expected_nbr}, "
                f"found {usda_nbr or '<blank>'}"
            )

    mapping: dict[str, ResolvedNutrient] = {}
    for spec in TARGET_SPECS:
        options = candidates.get(spec.code, [])
        if not options:
            continue
        matching = [item for item in options if item.usda_nbr == spec.expected_nbr]
        selected = matching[0] if matching else options[0]
        mapping[selected.usda_id] = selected
        if len(matching) > 1:
            mismatches.append(
                f"{spec.code}: multiple candidates have expected nutrient_nbr={spec.expected_nbr}: "
                + ", ".join(item.usda_id for item in matching)
            )
    return mapping, mismatches


def choose_join_field(
    nutrient_rows: Iterable[dict[str, str]], observed_keys: set[str]
) -> tuple[str, int, int]:
    id_values = {clean(row.get("id")) for row in nutrient_rows}
    nbr_values = {clean(row.get("nutrient_nbr")) for row in nutrient_rows}
    id_count = len(observed_keys & id_values)
    nbr_count = len(observed_keys & nbr_values)
    if id_count == nbr_count:
        raise RuntimeError(
            f"Cannot choose USDA nutrient join: id coverage={id_count}, nutrient_nbr coverage={nbr_count}"
        )
    return ("id" if id_count > nbr_count else "nutrient_nbr", id_count, nbr_count)


def load_categories(folder: Path, dataset: Dataset) -> dict[str, str]:
    if dataset.key != "survey":
        path = folder / "food_category.csv"
        return {clean(row.get("id")): clean(row.get("description")) for row in read_csv(path)}

    category_names = {
        clean(row.get("wweia_food_category")): clean(row.get("wweia_food_category_description"))
        for row in read_csv(folder / "wweia_food_category.csv")
    }
    fdc_to_category = {
        clean(row.get("fdc_id")): clean(row.get("wweia_category_number"))
        for row in read_csv(folder / "survey_fndds_food.csv")
    }
    return {
        fdc_id: category_names[number]
        for fdc_id, number in fdc_to_category.items()
        if number in category_names
    }


def observed_nutrient_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for row in read_csv(path):
        key = clean(row.get("nutrient_id"))
        if key:
            keys.add(key)
    return keys


def validate_schema(allow_production: bool = False) -> None:
    configured_url = settings.resolved_database_url
    db_path = db_path_from_url(configured_url)
    print(f"[DB] engine_url={configured_url}")
    print(f"[DB] sqlite_path={db_path.resolve() if db_path else '<non-sqlite>'}")
    if db_path is None:
        raise RuntimeError("This importer is restricted to SQLite")
    if db_path.resolve() == PROTECTED_DB and not allow_production:
        raise RuntimeError(
            f"Refusing to write protected database: {PROTECTED_DB} "
            "(thêm --allow-production nếu thực sự muốn nạp vào database chính thức)"
        )
    if not db_path.exists():
        raise RuntimeError("Target database does not exist; use a migrated copy with seeded reference data")
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != EXPECTED_REVISION:
        raise RuntimeError(f"Expected Alembic revision {EXPECTED_REVISION}, found {revision!r}")


def load_reference_rows(db) -> tuple[dict[str, FoodSource], dict[str, Nutrient]]:
    sources: dict[str, FoodSource] = {}
    for dataset in DATASETS:
        source = db.scalar(select(FoodSource).where(FoodSource.code == dataset.source_code))
        if source is None:
            raise RuntimeError(f"Missing seeded food source: {dataset.source_code}")
        sources[dataset.source_code] = source

    nutrients: dict[str, Nutrient] = {}
    for spec in TARGET_SPECS:
        nutrient = db.scalar(select(Nutrient).where(Nutrient.code == spec.code))
        if nutrient is None:
            raise RuntimeError(f"Missing seeded nutrient: {spec.code}")
        if nutrient.unit != spec.app_unit:
            raise RuntimeError(
                f"Unit mismatch for {spec.code}: catalog={nutrient.unit!r}, importer={spec.app_unit!r}"
            )
        nutrients[spec.code] = nutrient
    return sources, nutrients


def prepare_mapping(folder: Path, stats: DatasetStats) -> tuple[dict[str, ResolvedNutrient], set[str]]:
    nutrient_rows = list(read_csv(folder / "nutrient.csv"))
    observed = observed_nutrient_keys(folder / "food_nutrient.csv")
    join_field, id_coverage, nbr_coverage = choose_join_field(nutrient_rows, observed)
    by_id, mismatches = derive_nutrient_mapping(nutrient_rows)

    found_codes = {resolved.code for resolved in by_id.values()}
    fatal_mismatches: list[str] = []
    for spec in TARGET_SPECS:
        if spec.code not in found_codes:
            message = f"{spec.code}: no match for names={spec.names!r}, unit={spec.usda_unit}"
            mismatches.append(message)
            fatal_mismatches.append(message)
    for resolved in by_id.values():
        if resolved.usda_nbr != resolved.expected_nbr:
            fatal_mismatches.append(
                f"{resolved.code}: selected id={resolved.usda_id} has nutrient_nbr={resolved.usda_nbr}, "
                f"expected {resolved.expected_nbr}"
            )

    stats.join_field = join_field
    stats.id_coverage = id_coverage
    stats.nutrient_nbr_coverage = nbr_coverage
    stats.observed_nutrient_keys = len(observed)
    stats.mapping_mismatches = mismatches
    stats.nutrient_mapping = [
        {
            "code": item.code,
            "usda_id": item.usda_id,
            "usda_nbr": item.usda_nbr,
            "name": item.usda_name,
            "usda_unit": item.usda_unit,
            "app_unit": item.app_unit,
        }
        for item in sorted(by_id.values(), key=lambda item: item.code)
    ]

    print(
        f"[JOIN] {stats.dataset}: distinct={len(observed)}, "
        f"id={id_coverage}, nutrient_nbr={nbr_coverage}, selected={join_field}"
    )
    for item in stats.nutrient_mapping:
        expected = next(spec.expected_nbr for spec in TARGET_SPECS if spec.code == item["code"])
        marker = "OK" if item["usda_nbr"] == expected else "MISMATCH"
        print(
            f"[MAP:{marker}] {stats.dataset} {item['code']}: "
            f"name={item['name']!r}, unit={item['usda_unit']}, "
            f"id={item['usda_id']}, nbr={item['usda_nbr']}, expected={expected}"
        )
    for mismatch in mismatches:
        print(f"[MAP:MISMATCH] {stats.dataset}: {mismatch}")
    if fatal_mismatches:
        raise RuntimeError(f"Nutrient mapping mismatch in {stats.dataset}")

    by_join: dict[str, ResolvedNutrient] = {}
    for item in by_id.values():
        key = item.usda_id if join_field == "id" else item.usda_nbr
        by_join[key] = item
    atwater_keys = {
        clean(row.get(join_field))
        for row in nutrient_rows
        if clean(row.get("name")).startswith("Energy (Atwater")
    }
    return by_join, atwater_keys


def import_foods(
    db,
    repo: FoodRepository,
    source: FoodSource,
    dataset: Dataset,
    folder: Path,
    batch_size: int,
    stats: DatasetStats,
) -> None:
    categories = load_categories(folder, dataset)
    pending = 0
    for row in read_csv(folder / "food.csv"):
        stats.food_rows_read += 1
        fdc_id = clean(row.get("fdc_id"))
        description = clean(row.get("description"))
        if not fdc_id or not description:
            stats.foods_skipped += 1
            continue

        category_key = fdc_id if dataset.key == "survey" else clean(row.get("food_category_id"))
        category = category_for(category_key, description, categories)
        cooking_state = infer_cooking_state(description)
        food = repo.find_by_source_ref(source.id, fdc_id)
        is_new = food is None
        if food is None:
            food = Food(
                source_id=source.id,
                source_ref=fdc_id,
                name_vi=None,
                name_en=description,
                name_normalized=normalize_name(description),
                category=category,
                cooking_state=cooking_state,
                data_note=f"{dataset.label}; nutrient amounts per 100 g",
                is_verified=0,
            )
            db.add(food)
            db.flush()
            stats.foods_added += 1
        else:
            food.name_vi = None
            food.name_en = description
            food.name_normalized = normalize_name(description)
            food.category = category
            food.cooking_state = cooking_state
            food.data_note = f"{dataset.label}; nutrient amounts per 100 g"
            stats.foods_updated += 1

        if is_new:
            repo.add_alias(food.id, description, lang="en")
            stats.aliases_added += 1
        if cooking_state == "raw":
            stats.raw_assigned += 1
        elif cooking_state == "cooked":
            stats.cooked_assigned += 1
        else:
            stats.unknown_assigned += 1

        pending += 1
        if pending >= batch_size:
            db.commit()
            pending = 0
    if pending:
        db.commit()


def existing_nutrient_values(db, source_id: int) -> dict[tuple[int, int], tuple[float | None, str, str | None]]:
    """Small idempotency cache; values only, never CSV rows or ORM objects."""
    from app.models import FoodNutrient

    rows = db.execute(
        select(
            FoodNutrient.food_id,
            FoodNutrient.nutrient_id,
            FoodNutrient.amount_per_100g,
            FoodNutrient.unit,
            FoodNutrient.data_quality,
        )
        .join(Food, Food.id == FoodNutrient.food_id)
        .where(Food.source_id == source_id)
    )
    return {
        (food_id, nutrient_id): (amount, unit, quality)
        for food_id, nutrient_id, amount, unit, quality in rows
    }


def import_nutrients(
    db,
    repo: FoodRepository,
    source: FoodSource,
    folder: Path,
    mapping: dict[str, ResolvedNutrient],
    atwater_keys: set[str],
    app_nutrients: dict[str, Nutrient],
    batch_size: int,
    stats: DatasetStats,
) -> None:
    food_ids = {
        source_ref: food_id
        for source_ref, food_id in db.execute(
            select(Food.source_ref, Food.id).where(Food.source_id == source.id)
        )
        if source_ref
    }
    existing = existing_nutrient_values(db, source.id)
    pending = 0
    for row in read_csv(folder / "food_nutrient.csv"):
        stats.nutrient_rows_read += 1
        usda_key = clean(row.get("nutrient_id"))
        if usda_key in atwater_keys:
            stats.atwater_rows_skipped += 1
            continue
        resolved = mapping.get(usda_key)
        if resolved is None:
            continue
        food_id = food_ids.get(clean(row.get("fdc_id")))
        if food_id is None:
            stats.nutrient_rows_missing_food += 1
            continue

        amount = parse_amount(row.get("amount"))
        if amount is None:
            stats.nutrient_rows_null += 1
        nutrient = app_nutrients[resolved.code]
        quality = "measured" if resolved.code == "energy_kcal" else None
        current = existing.get((food_id, nutrient.id))
        desired = (amount, resolved.app_unit, quality)
        if current != desired:
            repo.upsert_nutrient(
                food_id,
                nutrient.id,
                amount,
                resolved.app_unit,
                quality=quality,
            )
            existing[(food_id, nutrient.id)] = desired
            if resolved.code == "energy_kcal":
                repo.sync_energy_cache(food_id)
            pending += 1
        stats.nutrient_rows_mapped += 1
        if pending >= batch_size:
            db.commit()
            pending = 0
    if pending:
        db.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Cho phép ghi trực tiếp vào data/nutrition.db. Mặc định script TỪ CHỐI để "
        "tránh vô tình sửa database thật; phải bật cờ này khi nạp dữ liệu chính thức.",
    )
    return parser.parse_args()


def run(data_root: Path, batch_size: int, allow_production: bool = False) -> dict[str, object]:
    if batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    validate_schema(allow_production=allow_production)
    data_root = data_root.resolve()
    results: list[DatasetStats] = []

    with SessionLocal() as db:
        sources, app_nutrients = load_reference_rows(db)
        for dataset in DATASETS:
            folder = data_root / dataset.folder
            required = ("food.csv", "food_nutrient.csv", "nutrient.csv")
            missing = [name for name in required if not (folder / name).is_file()]
            if missing:
                raise FileNotFoundError(f"{folder}: missing {', '.join(missing)}")

            stats = DatasetStats(dataset=dataset.key, source_code=dataset.source_code)
            mapping, atwater_keys = prepare_mapping(folder, stats)
            source = sources[dataset.source_code]
            repo = FoodRepository(db)
            import_foods(db, repo, source, dataset, folder, batch_size, stats)
            import_nutrients(
                db,
                repo,
                source,
                folder,
                mapping,
                atwater_keys,
                app_nutrients,
                batch_size,
                stats,
            )
            results.append(stats)
            print(
                f"[DONE] {dataset.key}: foods={stats.food_rows_read}, "
                f"added={stats.foods_added}, updated={stats.foods_updated}, "
                f"mapped_nutrients={stats.nutrient_rows_mapped}"
            )

    return {
        "engine_url": settings.resolved_database_url,
        "database_path": str(db_path_from_url(settings.resolved_database_url).resolve()),
        "batch_size": batch_size,
        "datasets": [asdict(item) for item in results],
    }


def main() -> int:
    args = parse_args()
    summary = run(args.data_root, args.batch_size, allow_production=args.allow_production)
    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(payload + os.linesep, encoding="utf-8")
        print(f"[SUMMARY] {args.summary_json.resolve()}")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
