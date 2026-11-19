"""Nhập CSV bảng thành phần thực phẩm Việt Nam với kiểm tra nghiêm ngặt."""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "external" / "vn_fct_template.csv"
DEFAULT_REPORT = ROOT / "data" / "reports" / "vn_fct_import_report.md"

EXPECTED_HEADER = (
    "food_name_vi", "food_name_en", "food_group", "cooking_state", "edible_portion",
    "energy_kcal_per_100g", "protein_g_per_100g", "fat_g_per_100g",
    "carbohydrate_g_per_100g", "fiber_g_per_100g", "sugar_g_per_100g",
    "sodium_mg_per_100g", "moisture_g_per_100g", "ash_g_per_100g",
    "source_name", "source_url", "source_note",
)

NUMERIC_RANGES = {
    "edible_portion": (0.0, 100.0),
    "energy_kcal_per_100g": (0.0, 1000.0),
    "protein_g_per_100g": (0.0, 100.0),
    "fat_g_per_100g": (0.0, 100.0),
    "carbohydrate_g_per_100g": (0.0, 100.0),
    "fiber_g_per_100g": (0.0, 100.0),
    "sugar_g_per_100g": (0.0, 100.0),
    "sodium_mg_per_100g": (0.0, 40000.0),
    "moisture_g_per_100g": (0.0, 100.0),
    "ash_g_per_100g": (0.0, 100.0),
}

NUTRIENT_COLUMNS = {
    "energy_kcal_per_100g": "energy_kcal",
    "protein_g_per_100g": "protein_g",
    "fat_g_per_100g": "fat_g",
    "carbohydrate_g_per_100g": "carbohydrate_g",
    "fiber_g_per_100g": "fiber_g",
    "sugar_g_per_100g": "sugar_g",
    "sodium_mg_per_100g": "sodium_mg",
    "moisture_g_per_100g": "moisture_g",
    "ash_g_per_100g": "ash_g",
}
COOKING_STATES = {"raw", "cooked", "processed", "unknown"}


def resolved_database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip() or (
        f"sqlite+pysqlite:///{(ROOT / 'data' / 'nutrition.db').as_posix()}"
    )


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def validate_row(
    row: dict[str, str], line_number: int
) -> tuple[dict[str, Any], list[str], bool]:
    """Trả về (dòng chuẩn hóa, lỗi, có dùng ước tính Atwater)."""
    parsed: dict[str, Any] = {key: _text(row.get(key)) for key in EXPECTED_HEADER}
    errors: list[str] = []

    if not parsed["food_name_vi"]:
        errors.append(f"dòng {line_number}: food_name_vi là bắt buộc để tạo source_ref ổn định")
    elif len(parsed["food_name_vi"]) > 240:
        errors.append(f"dòng {line_number}: food_name_vi dài quá 240 ký tự")
    if parsed["food_name_en"] and len(parsed["food_name_en"]) > 240:
        errors.append(f"dòng {line_number}: food_name_en dài quá 240 ký tự")
    if parsed["food_group"] and len(parsed["food_group"]) > 80:
        errors.append(f"dòng {line_number}: food_group dài quá 80 ký tự")
    if not parsed["source_name"]:
        errors.append(f"dòng {line_number}: source_name là bắt buộc (truy xuất nguồn)")

    state = parsed["cooking_state"]
    if state not in COOKING_STATES:
        errors.append(
            f"dòng {line_number}: cooking_state={state!r} không thuộc raw/cooked/processed/unknown"
        )

    for field, (minimum, maximum) in NUMERIC_RANGES.items():
        raw = parsed[field]
        if raw is None:
            continue
        try:
            value = float(raw)
        except ValueError:
            errors.append(f"dòng {line_number}: {field}={raw!r} không phải số")
            parsed[field] = None
            continue
        if not math.isfinite(value):
            errors.append(f"dòng {line_number}: {field} phải là số hữu hạn")
        elif not minimum <= value <= maximum:
            errors.append(
                f"dòng {line_number}: {field}={value:g} ngoài khoảng {minimum:g}..{maximum:g}"
            )
        parsed[field] = value

    estimated = False
    macros = (
        parsed["protein_g_per_100g"], parsed["carbohydrate_g_per_100g"],
        parsed["fat_g_per_100g"],
    )
    if parsed["energy_kcal_per_100g"] is None and all(value is not None for value in macros):
        protein, carbohydrate, fat = macros
        estimate = 4.0 * protein + 4.0 * carbohydrate + 9.0 * fat
        if estimate > 1000.0:
            errors.append(
                f"dòng {line_number}: năng lượng Atwater ước tính {estimate:g} ngoài khoảng 0..1000"
            )
        else:
            parsed["energy_kcal_per_100g"] = estimate
            estimated = True
    return parsed, errors, estimated


def read_and_validate(path: Path) -> tuple[list[tuple[int, dict[str, Any], bool]], list[str]]:
    accepted: list[tuple[int, dict[str, Any], bool]] = []
    errors: list[str] = []
    header: list[str] | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        try:
            for fields in reader:
                line_number = reader.line_num
                if not fields or (fields[0].lstrip().startswith("#")):
                    continue
                if header is None:
                    header = fields
                    if tuple(header) != EXPECTED_HEADER:
                        errors.append(
                            f"dòng {line_number}: tiêu đề không đúng 17 cột yêu cầu; nhận được {fields!r}"
                        )
                    continue
                if tuple(header) != EXPECTED_HEADER:
                    continue
                if len(fields) != len(EXPECTED_HEADER):
                    errors.append(
                        f"dòng {line_number}: có {len(fields)} cột, phải có {len(EXPECTED_HEADER)} cột"
                    )
                    continue
                parsed, row_errors, estimated = validate_row(
                    dict(zip(EXPECTED_HEADER, fields, strict=True)), line_number
                )
                errors.extend(row_errors)
                if not row_errors:
                    accepted.append((line_number, parsed, estimated))
        except csv.Error as exc:
            errors.append(f"lỗi cú pháp CSV gần dòng {reader.line_num}: {exc}")
    if header is None:
        errors.append("không tìm thấy hàng tiêu đề sau các dòng chú thích")
    return accepted, errors


def _traceability_note(row: dict[str, Any]) -> str:
    parts = [f"Nguồn: {row['source_name']}"]
    if row["source_url"]:
        parts.append(f"URL: {row['source_url']}")
    if row["source_note"]:
        parts.append(f"Ghi chú nguồn: {row['source_note']}")
    if row["edible_portion"] is not None:
        parts.append(f"Phần ăn được: {row['edible_portion']:g}%")
    return " | ".join(parts)


def import_rows(rows: list[tuple[int, dict[str, Any], bool]]) -> tuple[int, int, list[str]]:
    sys.path.insert(0, str(ROOT))
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.core.utils import normalize_name, slugify
    from app.models import Food, FoodSource, Nutrient
    from app.repositories.food_repository import FoodRepository

    inserted = updated = 0
    estimated_names: list[str] = []
    with SessionLocal() as db:
        source = db.scalar(select(FoodSource).where(FoodSource.code == "vn_fct"))
        if source is None:
            raise RuntimeError("thiếu food_sources.code='vn_fct'; hãy chạy seed_reference_data.py")
        nutrients = {
            nutrient.code: nutrient
            for nutrient in db.scalars(
                select(Nutrient).where(Nutrient.code.in_(tuple(NUTRIENT_COLUMNS.values())))
            )
        }
        missing = sorted(set(NUTRIENT_COLUMNS.values()) - set(nutrients))
        if missing:
            raise RuntimeError(f"thiếu nutrient code: {', '.join(missing)}")

        repository = FoodRepository(db)
        for _line_number, row, estimated in rows:
            source_ref = slugify(row["food_name_vi"])
            if not source_ref:
                raise RuntimeError(f"không thể tạo source_ref từ {row['food_name_vi']!r}")
            if len(source_ref) > 120:
                raise RuntimeError(f"source_ref dài quá 120 ký tự: {source_ref!r}")
            food = repository.find_by_source_ref(source.id, source_ref)
            if food is None:
                food = Food(source_id=source.id, source_ref=source_ref, name_normalized="")
                db.add(food)
                db.flush()
                inserted += 1
            else:
                updated += 1
            food.name_vi = row["food_name_vi"]
            food.name_en = row["food_name_en"]
            food.name_normalized = normalize_name(row["food_name_vi"] or row["food_name_en"] or "")
            food.food_group = row["food_group"]
            food.cooking_state = row["cooking_state"]
            food.data_note = _traceability_note(row)
            food.is_verified = 0

            for column, code in NUTRIENT_COLUMNS.items():
                amount = row[column]
                quality = None if amount is None else "measured"
                if code == "energy_kcal" and estimated:
                    quality = "estimated"
                repository.upsert_nutrient(
                    food.id, nutrients[code].id, amount, nutrients[code].unit, quality
                )
            repository.sync_energy_cache(food.id)
            if estimated:
                estimated_names.append(row["food_name_vi"])
        db.commit()
    return inserted, updated, estimated_names


def render_report(
    input_path: Path, accepted_count: int, inserted: int, updated: int,
    errors: list[str], estimated_names: list[str], database_url: str,
) -> str:
    lines = [
        "# Báo cáo nhập VN FCT", "",
        f"- CSDL: `{database_url}`",
        f"- Tệp đầu vào: `{input_path.as_posix()}`",
        f"- Dòng hợp lệ: **{accepted_count}**",
        f"- Dòng thêm mới: **{inserted}**",
        f"- Dòng cập nhật: **{updated}**",
        f"- Vi phạm/lỗi được báo cáo: **{len(errors)}**", "",
        "Giá trị trống được lưu dưới dạng `NULL`, không đổi thành 0.", "",
        "## Ước tính Atwater", "",
    ]
    if estimated_names:
        lines.append(
            f"Có **{len(estimated_names)}** thực phẩm được tính năng lượng theo 4/4/9 và lưu "
            "với `data_quality='estimated'`:"
        )
        lines.extend(f"- {name}" for name in estimated_names)
    else:
        lines.append("Không có dòng nào dùng ước tính Atwater.")
    lines.extend(["", "## Vi phạm", ""])
    lines.extend(f"- {error}" for error in errors) if errors else lines.append("Không có vi phạm.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    database_url = resolved_database_url()
    print(f"[DB] {database_url}", flush=True)
    inserted = updated = 0
    estimated_names: list[str] = []
    errors: list[str] = []
    accepted: list[tuple[int, dict[str, Any], bool]] = []
    try:
        accepted, errors = read_and_validate(args.input)
        if accepted:
            inserted, updated, estimated_names = import_rows(accepted)
    except Exception as exc:  # báo cáo rõ và không để giao dịch dở dang
        errors.append(f"lỗi nhập dữ liệu: {type(exc).__name__}: {exc}")

    report = render_report(
        args.input, len(accepted), inserted, updated, errors, estimated_names, database_url
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"[REPORT] {args.report}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
