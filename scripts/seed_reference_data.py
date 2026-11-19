"""Nạp dữ liệu tham chiếu cố định: danh mục chất dinh dưỡng và các nguồn dữ liệu.

Chạy:  .venv\\Scripts\\python.exe scripts\\seed_reference_data.py
Idempotent: chạy lại nhiều lần không tạo bản ghi trùng.

LƯU Ý: script này KHÔNG nạp dữ liệu thực phẩm. Dữ liệu thực phẩm thật được nạp
bằng scripts/import_*.py từ nguồn có ghi rõ xuất xứ (xem docs/DATA_SOURCES.md).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.utils import utcnow  # noqa: E402
from app.models import FoodSource, Nutrient  # noqa: E402

# (code, tên tiếng Việt, tên tiếng Anh, đơn vị, là năng lượng)
NUTRIENTS: list[tuple[str, str, str, str, int]] = [
    ("energy_kcal", "Năng lượng", "Energy", "kcal", 1),
    ("energy_kj", "Năng lượng (kJ)", "Energy (kJ)", "kJ", 0),
    ("protein_g", "Chất đạm", "Protein", "g", 0),
    ("fat_g", "Chất béo", "Total lipid (fat)", "g", 0),
    ("carbohydrate_g", "Chất bột đường", "Carbohydrate, by difference", "g", 0),
    ("fiber_g", "Chất xơ", "Fiber, total dietary", "g", 0),
    ("sugar_g", "Đường tổng", "Sugars, total", "g", 0),
    ("sodium_mg", "Natri", "Sodium, Na", "mg", 0),
    ("moisture_g", "Độ ẩm", "Water", "g", 0),
    ("ash_g", "Tro", "Ash", "g", 0),
    ("cholesterol_mg", "Cholesterol", "Cholesterol", "mg", 0),
    ("calcium_mg", "Canxi", "Calcium, Ca", "mg", 0),
    ("iron_mg", "Sắt", "Iron, Fe", "mg", 0),
    ("potassium_mg", "Kali", "Potassium, K", "mg", 0),
    ("vitamin_c_mg", "Vitamin C", "Vitamin C, total ascorbic acid", "mg", 0),
]

# (code, tên, loại, url, giấy phép, url giấy phép, ghi chú)
SOURCES: list[tuple[str, str, str, str | None, str | None, str | None, str | None]] = [
    (
        "usda_sr_legacy",
        "USDA FoodData Central - SR Legacy",
        "usda",
        "https://fdc.nal.usda.gov/download-datasets.html",
        None,  # điền sau khi đọc trang điều khoản (xem data/reports/usda_inventory.md)
        "https://fdc.nal.usda.gov/data-documentation.html",
        "Dữ liệu thành phần dinh dưỡng cơ bản của USDA (bản 2018-04).",
    ),
    (
        "usda_foundation",
        "USDA FoodData Central - Foundation Foods",
        "usda",
        "https://fdc.nal.usda.gov/download-datasets.html",
        None,
        "https://fdc.nal.usda.gov/data-documentation.html",
        "Dữ liệu nền tảng, có thông tin mẫu phân tích chi tiết.",
    ),
    (
        "usda_fndds",
        "USDA FoodData Central - Survey / FNDDS",
        "usda",
        "https://fdc.nal.usda.gov/download-datasets.html",
        None,
        "https://fdc.nal.usda.gov/data-documentation.html",
        "Dữ liệu khảo sát tiêu thụ thực phẩm, món ăn đã chế biến.",
    ),
    (
        "openfoodfacts",
        "Open Food Facts",
        "openfoodfacts",
        "https://world.openfoodfacts.org/",
        "Open Database License (ODbL) v1.0",
        "https://world.openfoodfacts.org/data",
        "Dữ liệu sản phẩm đóng gói do cộng đồng đóng góp; cần ghi nguồn khi tái sử dụng.",
    ),
    (
        "vn_fct",
        "Bảng thành phần dinh dưỡng thực phẩm Việt Nam",
        "vn_fct",
        "https://viendinhduong.vn/",
        None,
        None,
        "Nhập thủ công từ bảng thành phần dinh dưỡng (xem data/external/vn_fct_template.csv).",
    ),
    (
        "manual",
        "Nhập thủ công / do người vận hành cung cấp",
        "manual",
        None,
        None,
        None,
        "Bản ghi do người vận hành tự nhập kèm trích dẫn nguồn trong trường ghi chú.",
    ),
]


def main() -> int:
    added_n = added_s = 0
    with SessionLocal() as db:
        for code, vi, en, unit, is_energy in NUTRIENTS:
            row = db.scalar(select(Nutrient).where(Nutrient.code == code))
            if row is None:
                db.add(
                    Nutrient(code=code, name_vi=vi, name_en=en, unit=unit, is_energy=is_energy)
                )
                added_n += 1
            else:
                row.name_vi, row.name_en, row.unit, row.is_energy = vi, en, unit, is_energy

        for code, name, kind, url, lic, lic_url, note in SOURCES:
            row = db.scalar(select(FoodSource).where(FoodSource.code == code))
            if row is None:
                db.add(
                    FoodSource(
                        code=code,
                        name=name,
                        kind=kind,
                        url=url,
                        license=lic,
                        license_url=lic_url,
                        note=note,
                        retrieved_at=datetime.utcnow() if kind != "manual" else None,
                    )
                )
                added_s += 1
            else:
                row.name, row.kind, row.url = name, kind, url
                row.license, row.license_url, row.note = lic, lic_url, note

        db.commit()

    total_n = 0
    total_s = 0
    from sqlalchemy import func

    with SessionLocal() as db:
        total_n = db.scalar(select(func.count()).select_from(Nutrient)) or 0
        total_s = db.scalar(select(func.count()).select_from(FoodSource)) or 0

    print(f"[OK] nutrients: +{added_n} mới, tổng {total_n}")
    print(f"[OK] food_sources: +{added_s} mới, tổng {total_s}")
    print(f"[i]  Thời điểm chạy: {utcnow().isoformat(timespec='seconds')}Z")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
