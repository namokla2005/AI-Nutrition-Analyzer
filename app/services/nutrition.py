"""Nghiệp vụ tính toán khẩu phần dinh dưỡng (§5.3 của yêu cầu).

Quy tắc bắt buộc:
- Kcal = kcal_per_100g × weight_grams / 100 (tương tự cho mọi chất khác).
- Giá trị thiếu (None) phải giữ nguyên là None, KHÔNG được coi là 0.
- Không trộn lẫn "100 g thực phẩm sống" với "100 g thực phẩm đã nấu chín": mọi hàm
  ở đây nhận giá trị trên 100 g của CHÍNH trạng thái chế biến của thực phẩm đó.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

# Số chữ số thập phân khi làm tròn theo từng chất (kcal: 1, đa lượng: 2, vi lượng: 1)
ROUNDING: dict[str, int] = {
    "energy_kcal": 1,
    "protein_g": 2,
    "fat_g": 2,
    "carbohydrate_g": 2,
    "fiber_g": 2,
    "sugar_g": 2,
    "sodium_mg": 1,
    "moisture_g": 2,
    "ash_g": 2,
}
DEFAULT_DIGITS = 2

# Chất dinh dưỡng dùng khi báo cáo/tóm tắt (dùng cả cho ngữ cảnh của trợ lý AI)
KEYS_FOR_REPORT = [
    "energy_kcal",
    "protein_g",
    "carbohydrate_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
    "moisture_g",
    "ash_g",
]


class InvalidWeightError(ValueError):
    """Khối lượng không hợp lệ (âm, bằng 0 hoặc không phải số)."""


def _check_weight(weight_g: float, quantity: float) -> float:
    try:
        w = float(weight_g)
        q = float(quantity)
    except (TypeError, ValueError) as exc:
        raise InvalidWeightError("Khối lượng phải là số.") from exc
    if w <= 0:
        raise InvalidWeightError("Khối lượng phải lớn hơn 0 g.")
    if w > 20000:
        raise InvalidWeightError("Khối lượng vượt 20 kg - hãy kiểm tra lại.")
    if q <= 0:
        raise InvalidWeightError("Số lượng phải lớn hơn 0.")
    return w * q


def portion_amount(amount_per_100g: float | None, weight_g: float, quantity: float = 1.0) -> float | None:
    """Giá trị của một chất cho khối lượng đã ăn. None nếu nguồn không có số liệu."""
    total_weight = _check_weight(weight_g, quantity)
    if amount_per_100g is None:
        return None
    return float(amount_per_100g) * total_weight / 100.0


def portion_values(
    per_100g: Mapping[str, float | None],
    weight_g: float,
    quantity: float = 1.0,
) -> dict[str, float | None]:
    """Áp dụng công thức khẩu phần cho toàn bộ các chất trong `per_100g`."""
    total_weight = _check_weight(weight_g, quantity)
    out: dict[str, float | None] = {}
    for code, amount in per_100g.items():
        out[code] = None if amount is None else float(amount) * total_weight / 100.0
    return out


def round_nutrients(values: Mapping[str, float | None]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for code, value in values.items():
        if value is None:
            out[code] = None
        else:
            out[code] = round(float(value), ROUNDING.get(code, DEFAULT_DIGITS))
    return out


@dataclass
class DayTotals:
    """Tổng dinh dưỡng trong ngày/tuần/tháng."""

    totals: dict[str, float | None] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    item_count: int = 0
    items_without_energy: int = 0

    @property
    def energy_kcal(self) -> float | None:
        return self.totals.get("energy_kcal")

    def as_dict(self) -> dict:
        return {
            "totals": round_nutrients(self.totals),
            "missing_fields": sorted(self.missing_fields),
            "item_count": self.item_count,
            "items_without_energy": self.items_without_energy,
        }


def aggregate(items: Iterable[Mapping[str, float | None]], nutrient_codes: Iterable[str]) -> DayTotals:
    """Cộng dồn nhiều dòng.

    - Chất nào KHÔNG có số liệu ở ít nhất một dòng sẽ được ghi vào `missing_fields`
      (để giao diện nói rõ là thiếu dữ liệu thay vì hiển thị con số sai).
    - Tổng của một chất chỉ là None khi TẤT CẢ các dòng đều thiếu chất đó.
    """
    codes = list(nutrient_codes)
    sums: dict[str, float] = {c: 0.0 for c in codes}
    present: dict[str, int] = {c: 0 for c in codes}
    total_rows = 0
    rows_without_energy = 0

    for row in items:
        total_rows += 1
        if row.get("energy_kcal") is None:
            rows_without_energy += 1
        for code in codes:
            value = row.get(code)
            if value is not None:
                sums[code] += float(value)
                present[code] += 1

    totals: dict[str, float | None] = {}
    missing: list[str] = []
    for code in codes:
        if present[code] == 0:
            totals[code] = None
            missing.append(code)
        else:
            totals[code] = sums[code]
            if present[code] < total_rows:
                missing.append(code)

    return DayTotals(
        totals=totals,
        missing_fields=missing,
        item_count=total_rows,
        items_without_energy=rows_without_energy,
    )


def target_progress(total_kcal: float | None, target_kcal: float | None) -> dict:
    """Tỷ lệ đạt mục tiêu calo (None nếu thiếu dữ liệu - không bịa số)."""
    if total_kcal is None or not target_kcal:
        return {"target_kcal": target_kcal, "percent": None, "remaining_kcal": None}
    pct = total_kcal / float(target_kcal) * 100.0
    return {
        "target_kcal": round(float(target_kcal), 1),
        "percent": round(pct, 1),
        "remaining_kcal": round(float(target_kcal) - total_kcal, 1),
    }


def macro_energy_split(totals: Mapping[str, float | None]) -> dict[str, float | None]:
    """Phân bổ năng lượng theo 3 đa lượng (4/4/9 kcal mỗi g). None nếu thiếu dữ liệu."""
    protein = totals.get("protein_g")
    carb = totals.get("carbohydrate_g")
    fat = totals.get("fat_g")
    if protein is None or carb is None or fat is None:
        return {"protein_kcal": None, "carbohydrate_kcal": None, "fat_kcal": None,
                "protein_percent": None, "carbohydrate_percent": None, "fat_percent": None}
    p_kcal, c_kcal, f_kcal = protein * 4.0, carb * 4.0, fat * 9.0
    total = p_kcal + c_kcal + f_kcal
    if total <= 0:
        return {"protein_kcal": 0.0, "carbohydrate_kcal": 0.0, "fat_kcal": 0.0,
                "protein_percent": None, "carbohydrate_percent": None, "fat_percent": None}
    return {
        "protein_kcal": round(p_kcal, 1),
        "carbohydrate_kcal": round(c_kcal, 1),
        "fat_kcal": round(f_kcal, 1),
        "protein_percent": round(p_kcal / total * 100.0, 1),
        "carbohydrate_percent": round(c_kcal / total * 100.0, 1),
        "fat_percent": round(f_kcal / total * 100.0, 1),
    }


def kcal_per_100g_from_macros(protein_g: float | None, carb_g: float | None, fat_g: float | None) -> float | None:
    """Ước lượng năng lượng từ 3 đa lượng (hệ số Atwater 4/4/9).

    Chỉ dùng khi nguồn KHÔNG có sẵn giá trị năng lượng, và phải ghi rõ là giá trị ước lượng.
    """
    if protein_g is None or carb_g is None or fat_g is None:
        return None
    return round(protein_g * 4.0 + carb_g * 4.0 + fat_g * 9.0, 1)
