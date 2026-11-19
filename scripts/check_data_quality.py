"""Kiểm toán chất lượng dữ liệu dinh dưỡng SQLite ở chế độ chỉ đọc."""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "reports" / "data_quality_report.md"
SECTION_TITLES = (
    "Trùng lặp",
    "Đồng bộ bộ nhớ đệm năng lượng",
    "Thiếu năng lượng",
    "Giá trị phi lý",
    "Hồ sơ giá trị thiếu",
    "Trạng thái chế biến",
    "Đối chiếu Atwater",
)


def resolved_database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip() or (
        f"sqlite+pysqlite:///{(ROOT / 'data' / 'nutrition.db').as_posix()}"
    )


def sqlite_path(database_url: str) -> Path:
    prefixes = ("sqlite+pysqlite:///", "sqlite:///")
    raw = next((database_url[len(p):] for p in prefixes if database_url.startswith(p)), None)
    if raw is None or raw == ":memory:":
        raise ValueError("chỉ hỗ trợ DATABASE_URL SQLite dạng tệp")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _read_only_connection(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _safe(value: Any) -> str:
    return str(value if value is not None else "NULL").replace("|", "\\|").replace("\n", " ")


def _examples_table(rows: list[sqlite3.Row], columns: tuple[str, ...]) -> list[str]:
    if not rows:
        return ["Không có."]
    output = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in rows:
        output.append("| " + " | ".join(_safe(row[column]) for column in columns) + " |")
    return output


def build_report(connection: sqlite3.Connection, database_url: str) -> str:
    total = int(connection.execute("SELECT COUNT(*) FROM foods").fetchone()[0])
    lines = [
        "# Báo cáo chất lượng dữ liệu", "",
        f"- CSDL: `{database_url}`",
        "- Chế độ truy cập: **chỉ đọc** (`mode=ro`, `PRAGMA query_only=ON`)",
        f"- Tổng thực phẩm: **{total}**", "",
    ]
    warning_reasons: list[str] = []

    exact_count = int(connection.execute("""
        SELECT COUNT(*) FROM (
          SELECT source_id, source_ref FROM foods
          GROUP BY source_id, source_ref HAVING COUNT(*) > 1
        )
    """).fetchone()[0])
    exact_examples = connection.execute("""
        SELECT source_id, source_ref, COUNT(*) AS so_luong
        FROM foods GROUP BY source_id, source_ref HAVING COUNT(*) > 1
        ORDER BY so_luong DESC, source_id, source_ref LIMIT 30
    """).fetchall()
    near_count = int(connection.execute("""
        SELECT COUNT(*) FROM (
          SELECT name_normalized FROM foods
          WHERE name_normalized IS NOT NULL AND name_normalized <> ''
          GROUP BY name_normalized HAVING COUNT(DISTINCT source_id) > 1
        )
    """).fetchone()[0])
    near_examples = connection.execute("""
        SELECT f.name_normalized, COUNT(*) AS so_luong,
               COUNT(DISTINCT f.source_id) AS so_nguon,
               GROUP_CONCAT(DISTINCT s.code) AS nguon
        FROM foods f JOIN food_sources s ON s.id=f.source_id
        WHERE f.name_normalized IS NOT NULL AND f.name_normalized <> ''
        GROUP BY f.name_normalized HAVING COUNT(DISTINCT f.source_id) > 1
        ORDER BY so_luong DESC, f.name_normalized LIMIT 30
    """).fetchall()
    lines.extend([
        f"## 1. {SECTION_TITLES[0]}", "",
        f"- Nhóm trùng chính xác theo `source_id + source_ref`: **{exact_count}**",
        f"- Nhóm gần trùng theo `name_normalized` ở nhiều nguồn: **{near_count}** (tối đa 30 ví dụ)", "",
        "### Trùng chính xác", "",
        *_examples_table(exact_examples, ("source_id", "source_ref", "so_luong")), "",
        "### Gần trùng khác nguồn", "",
        *_examples_table(near_examples, ("name_normalized", "so_luong", "so_nguon", "nguon")), "",
    ])
    if exact_count or near_count:
        warning_reasons.append("trùng lặp")

    mismatch_rows = connection.execute("""
        SELECT f.id, COALESCE(f.name_vi, f.name_en, f.name_normalized) AS ten,
               f.energy_kcal_per_100g AS cache_kcal, e.amount_per_100g AS canonical_kcal
        FROM foods f
        LEFT JOIN (
          SELECT fn.food_id, fn.amount_per_100g
          FROM food_nutrients fn JOIN nutrients n ON n.id=fn.nutrient_id
          WHERE n.code='energy_kcal'
        ) e ON e.food_id=f.id
        WHERE (f.energy_kcal_per_100g IS NULL AND e.amount_per_100g IS NOT NULL)
           OR (f.energy_kcal_per_100g IS NOT NULL AND e.amount_per_100g IS NULL)
           OR (f.energy_kcal_per_100g IS NOT NULL AND e.amount_per_100g IS NOT NULL
               AND ABS(f.energy_kcal_per_100g-e.amount_per_100g)>0.000001)
        ORDER BY f.id LIMIT 30
    """).fetchall()
    mismatch_count = int(connection.execute("""
        SELECT COUNT(*) FROM foods f LEFT JOIN (
          SELECT fn.food_id, fn.amount_per_100g FROM food_nutrients fn
          JOIN nutrients n ON n.id=fn.nutrient_id WHERE n.code='energy_kcal'
        ) e ON e.food_id=f.id
        WHERE (f.energy_kcal_per_100g IS NULL AND e.amount_per_100g IS NOT NULL)
           OR (f.energy_kcal_per_100g IS NOT NULL AND e.amount_per_100g IS NULL)
           OR (f.energy_kcal_per_100g IS NOT NULL AND e.amount_per_100g IS NOT NULL
               AND ABS(f.energy_kcal_per_100g-e.amount_per_100g)>0.000001)
    """).fetchone()[0])
    lines.extend([
        f"## 2. {SECTION_TITLES[1]}", "",
        f"Số thực phẩm cache khác hàng `food_nutrients.energy_kcal`: **{mismatch_count}**.", "",
        *_examples_table(mismatch_rows, ("id", "ten", "cache_kcal", "canonical_kcal")), "",
    ])
    if mismatch_count:
        warning_reasons.append("cache năng lượng không đồng bộ")

    missing_rows = connection.execute("""
        SELECT f.id, COALESCE(f.name_vi, f.name_en, f.name_normalized) AS ten
        FROM foods f LEFT JOIN (
          SELECT fn.food_id, fn.amount_per_100g FROM food_nutrients fn
          JOIN nutrients n ON n.id=fn.nutrient_id WHERE n.code='energy_kcal'
        ) e ON e.food_id=f.id
        WHERE f.energy_kcal_per_100g IS NULL AND e.amount_per_100g IS NULL
        ORDER BY f.id LIMIT 30
    """).fetchall()
    missing_energy_count = int(connection.execute("""
        SELECT COUNT(*) FROM foods f LEFT JOIN (
          SELECT fn.food_id, fn.amount_per_100g FROM food_nutrients fn
          JOIN nutrients n ON n.id=fn.nutrient_id WHERE n.code='energy_kcal'
        ) e ON e.food_id=f.id
        WHERE f.energy_kcal_per_100g IS NULL AND e.amount_per_100g IS NULL
    """).fetchone()[0])
    lines.extend([
        f"## 3. {SECTION_TITLES[2]}", "",
        f"Thực phẩm không có năng lượng ở cả cache lẫn bảng chuẩn: **{missing_energy_count}**.", "",
        *_examples_table(missing_rows, ("id", "ten")), "",
    ])
    if missing_energy_count:
        warning_reasons.append("thiếu năng lượng")

    pivot = """
      SELECT fn.food_id,
        MAX(CASE WHEN n.code='energy_kcal' THEN fn.amount_per_100g END) energy,
        MAX(CASE WHEN n.code='protein_g' THEN fn.amount_per_100g END) protein,
        MAX(CASE WHEN n.code='carbohydrate_g' THEN fn.amount_per_100g END) carbohydrate,
        MAX(CASE WHEN n.code='fat_g' THEN fn.amount_per_100g END) fat,
        MAX(CASE WHEN n.code='sodium_mg' THEN fn.amount_per_100g END) sodium
      FROM food_nutrients fn JOIN nutrients n ON n.id=fn.nutrient_id GROUP BY fn.food_id
    """
    high_energy_count = int(connection.execute(f"""
        SELECT COUNT(*) FROM foods f LEFT JOIN ({pivot}) p ON p.food_id=f.id
        WHERE COALESCE(p.energy, f.energy_kcal_per_100g)>900
    """).fetchone()[0])
    macro_count = int(connection.execute(f"""
        SELECT COUNT(*) FROM ({pivot}) p
        WHERE COALESCE(p.protein,0)+COALESCE(p.carbohydrate,0)+COALESCE(p.fat,0)>100
    """).fetchone()[0])
    negative_count = int(connection.execute("""
        SELECT COUNT(DISTINCT food_id) FROM food_nutrients WHERE amount_per_100g<0
    """).fetchone()[0])
    negative_cache_count = int(connection.execute(
        "SELECT COUNT(*) FROM foods WHERE energy_kcal_per_100g<0"
    ).fetchone()[0])
    sodium_count = int(connection.execute(f"""
        SELECT COUNT(*) FROM ({pivot}) p WHERE p.sodium>40000
    """).fetchone()[0])
    implausible_rows = connection.execute(f"""
        SELECT f.id, COALESCE(f.name_vi, f.name_en, f.name_normalized) ten,
               COALESCE(p.energy, f.energy_kcal_per_100g) energy,
               COALESCE(p.protein,0)+COALESCE(p.carbohydrate,0)+COALESCE(p.fat,0) macro_sum,
               p.sodium
        FROM foods f LEFT JOIN ({pivot}) p ON p.food_id=f.id
        WHERE COALESCE(p.energy, f.energy_kcal_per_100g)>900
           OR COALESCE(p.protein,0)+COALESCE(p.carbohydrate,0)+COALESCE(p.fat,0)>100
           OR p.sodium>40000 OR f.energy_kcal_per_100g<0
           OR EXISTS (SELECT 1 FROM food_nutrients x WHERE x.food_id=f.id AND x.amount_per_100g<0)
        ORDER BY f.id LIMIT 30
    """).fetchall()
    lines.extend([
        f"## 4. {SECTION_TITLES[3]}", "",
        f"- Năng lượng > 900 kcal/100 g: **{high_energy_count}**",
        f"- Tổng protein + carbohydrate + fat > 100 g/100 g: **{macro_count}**",
        f"- Giá trị âm trong `food_nutrients`: **{negative_count}** thực phẩm",
        f"- Cache năng lượng âm: **{negative_cache_count}** thực phẩm",
        f"- Natri > 40000 mg/100 g: **{sodium_count}**", "",
        *_examples_table(implausible_rows, ("id", "ten", "energy", "macro_sum", "sodium")), "",
    ])
    if any((high_energy_count, macro_count, negative_count, negative_cache_count, sodium_count)):
        warning_reasons.append("giá trị phi lý")

    profile_rows = connection.execute("""
        SELECT n.code,
               SUM(CASE WHEN fn.amount_per_100g IS NOT NULL THEN 1 ELSE 0 END) AS co_gia_tri
        FROM nutrients n LEFT JOIN food_nutrients fn ON fn.nutrient_id=n.id
        GROUP BY n.id, n.code ORDER BY n.code
    """).fetchall()
    lines.extend([
        f"## 5. {SECTION_TITLES[4]}", "",
        "`NULL` gồm cả trường hợp không có hàng chất dinh dưỡng và hàng có `amount_per_100g=NULL`.", "",
        "| nutrient_code | Có giá trị | NULL | Độ phủ | Đánh giá |",
        "|---|---:|---:|---:|---|",
    ])
    for row in profile_rows:
        present = int(row["co_gia_tri"] or 0)
        null_count = total - present
        coverage = (100.0 * present / total) if total else 0.0
        sparsity = "thưa" if coverage < 50.0 else "đủ hơn"
        lines.append(f"| {_safe(row['code'])} | {present} | {null_count} | {coverage:.1f}% | {sparsity} |")
    lines.append("")

    unknown_count = int(connection.execute(
        "SELECT COUNT(*) FROM foods WHERE cooking_state='unknown'"
    ).fetchone()[0])
    unknown_share = (100.0 * unknown_count / total) if total else 0.0
    lines.extend([
        f"## 6. {SECTION_TITLES[5]}", "",
        f"`cooking_state='unknown'`: **{unknown_count}/{total} ({unknown_share:.1f}%)**.", "",
    ])

    atwater_cursor = connection.execute("""
        SELECT f.id, COALESCE(f.name_vi, f.name_en, f.name_normalized) AS ten,
               e.amount_per_100g AS measured,
               p.amount_per_100g AS protein, c.amount_per_100g AS carbohydrate,
               fat.amount_per_100g AS fat
        FROM foods f
        JOIN food_nutrients e ON e.food_id=f.id
        JOIN nutrients ne ON ne.id=e.nutrient_id AND ne.code='energy_kcal'
        JOIN food_nutrients p ON p.food_id=f.id JOIN nutrients np ON np.id=p.nutrient_id AND np.code='protein_g'
        JOIN food_nutrients c ON c.food_id=f.id JOIN nutrients nc ON nc.id=c.nutrient_id AND nc.code='carbohydrate_g'
        JOIN food_nutrients fat ON fat.food_id=f.id JOIN nutrients nf ON nf.id=fat.nutrient_id AND nf.code='fat_g'
        WHERE e.amount_per_100g IS NOT NULL AND p.amount_per_100g IS NOT NULL
          AND c.amount_per_100g IS NOT NULL AND fat.amount_per_100g IS NOT NULL
          AND LOWER(COALESCE(e.data_quality, 'measured')) = 'measured'
        ORDER BY f.id
    """)
    atwater_count = over_25 = 0
    absolute_sum = 0.0
    outlier_examples: list[dict[str, Any]] = []
    for row in atwater_cursor:
        measured = float(row["measured"])
        estimate = 4.0 * float(row["protein"]) + 4.0 * float(row["carbohydrate"]) + 9.0 * float(row["fat"])
        difference = abs(measured - estimate)
        absolute_sum += difference
        atwater_count += 1
        relative = 0.0 if measured == 0.0 and estimate == 0.0 else (
            math.inf if measured == 0.0 else difference / abs(measured)
        )
        if relative > 0.25:
            over_25 += 1
            if len(outlier_examples) < 30:
                outlier_examples.append({
                    "id": row["id"], "ten": row["ten"], "measured": f"{measured:.3f}",
                    "atwater": f"{estimate:.3f}",
                    "chenh_lech_pct": "∞" if math.isinf(relative) else f"{relative * 100:.1f}%",
                })
    mean_absolute = absolute_sum / atwater_count if atwater_count else 0.0
    lines.extend([
        f"## 7. {SECTION_TITLES[6]}", "",
        "Chỉ xét năng lượng `measured` (giá trị NULL của dữ liệu cũ được xem là measured) và có đủ protein/carbohydrate/fat.", "",
        f"- Số thực phẩm đối chiếu: **{atwater_count}**",
        f"- Sai khác tuyệt đối trung bình: **{mean_absolute:.3f} kcal/100 g**",
        f"- Sai khác lớn hơn 25%: **{over_25}**", "",
    ])
    if outlier_examples:
        lines.extend([
            "| id | ten | measured | atwater | chenh_lech_pct |",
            "|---:|---|---:|---:|---:|",
            *(
                f"| {_safe(r['id'])} | {_safe(r['ten'])} | {r['measured']} | {r['atwater']} | {r['chenh_lech_pct']} |"
                for r in outlier_examples
            ), "",
        ])
    else:
        lines.extend(["Không có ví dụ sai khác trên 25%.", ""])
    if over_25:
        warning_reasons.append("đối chiếu Atwater lệch trên 25%")

    if total == 0:
        warning_reasons.append("CSDL chưa có thực phẩm")
    status = "WARN" if warning_reasons else "PASS"
    reasons = ", ".join(dict.fromkeys(warning_reasons)) if warning_reasons else "không phát hiện cảnh báo"
    lines.extend(["## Tổng kết", "", f"**{status}** — {reasons}.", ""])
    return "\n".join(lines)


def error_report(database_url: str, exc: Exception) -> str:
    return "\n".join([
        "# Báo cáo chất lượng dữ liệu", "",
        f"- CSDL: `{database_url}`", "",
        "## Tổng kết", "",
        f"**WARN** — không thể kiểm toán: {type(exc).__name__}: {exc}", "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None,
                        help="DATABASE_URL của SQLite cần kiểm toán (mặc định: cấu hình của ứng dụng)")
    parser.add_argument("--out", default=None, help="Đường dẫn file báo cáo markdown")
    parser.add_argument("--json", dest="json_out", default=None, help="Xuất thêm bản JSON tổng kết")
    args = parser.parse_args()

    global REPORT_PATH
    report_path = Path(args.out).resolve() if args.out else REPORT_PATH
    database_url = args.db or resolved_database_url()
    print(f"[DB] {database_url}", flush=True)

    # Thiếu database là LỖI, không phải một bản kiểm toán hợp lệ: không ghi đè báo cáo cũ
    try:
        path = sqlite_path(database_url)
    except ValueError as exc:
        print(f"[X] DATABASE_URL không hợp lệ: {exc}")
        return 2
    if not path.exists():
        print(f"[X] Không tìm thấy database: {path}")
        print("    Hãy chạy migration + seed trước, hoặc truyền --db cho đúng đường dẫn.")
        return 2

    with _read_only_connection(path) as connection:
        report = build_report(connection, database_url)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"[REPORT] {report_path}")
    if args.json_out:
        summary = {"database_url": database_url, "report_path": str(report_path),
                   "status": "WARN" if "**WARN**" in report else "PASS"}
        Path(args.json_out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[JSON] {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
