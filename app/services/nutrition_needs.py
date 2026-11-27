"""Tính nhu cầu năng lượng từ chỉ số cơ thể (không bịa số: thiếu dữ liệu thì nói rõ thiếu gì).

Công thức dùng:
- BMR theo Mifflin–St Jeor (1990):
    nam:   10 × cân nặng(kg) + 6,25 × chiều cao(cm) − 5 × tuổi + 5
    nữ:    10 × cân nặng(kg) + 6,25 × chiều cao(cm) − 5 × tuổi − 161
- TDEE = BMR × hệ số vận động (sedentary 1,2 · light 1,375 · moderate 1,55 · active 1,725 ·
  very_active 1,9).
- Điều chỉnh theo mục tiêu cân nặng: giảm 500 kcal/ngày (khoảng 0,45 kg/tuần), giữ nguyên 0,
  tăng 300 kcal/ngày.
Mọi hệ số đều là hằng số công khai, không phụ thuộc dữ liệu người dùng.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

ACTIVITY_FACTORS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
ACTIVITY_LABELS_VI: dict[str, str] = {
    "sedentary": "ít vận động (ngồi nhiều)",
    "light": "vận động nhẹ (đi lại, 1-3 buổi/tuần)",
    "moderate": "vận động vừa (3-5 buổi/tuần)",
    "active": "vận động nhiều (6-7 buổi/tuần)",
    "very_active": "vận động rất nhiều (lao động nặng/thể thao 2 lần/ngày)",
}
GOAL_DELTA_KCAL: dict[str, float] = {"lose": -500.0, "maintain": 0.0, "gain": 300.0}
GOAL_LABELS_VI: dict[str, str] = {"lose": "giảm cân", "maintain": "giữ cân", "gain": "tăng cân"}
# Ngưỡng an toàn: không bao giờ đề xuất dưới mức này dù công thức ra thấp hơn.
MIN_SAFE_KCAL = {"male": 1500.0, "female": 1200.0, "other": 1200.0}
REQUIRED_FIELDS = ("gender", "birth_year", "height_cm", "weight_kg", "activity_level")


@dataclass
class EnergyNeeds:
    """Kết quả tính nhu cầu năng lượng. Trường nào không tính được thì để None."""

    age: int | None = None
    bmr: float | None = None
    activity_level: str | None = None
    activity_factor: float | None = None
    tdee: float | None = None
    goal: str | None = None
    goal_delta_kcal: float | None = None
    suggested_kcal: float | None = None
    applied_safety_floor: bool = False
    missing_fields: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "age": self.age,
            "bmr_kcal": self.bmr,
            "activity_level": self.activity_level,
            "activity_factor": self.activity_factor,
            "tdee_kcal": self.tdee,
            "goal": self.goal,
            "goal_delta_kcal": self.goal_delta_kcal,
            "suggested_kcal": self.suggested_kcal,
            "applied_safety_floor": self.applied_safety_floor,
            "missing_fields": self.missing_fields,
            "notes": self.notes,
        }


def age_from_birth_year(birth_year: int | None, today: date | None = None) -> int | None:
    """Tuổi = năm hiện tại − năm sinh (theo múi giờ Việt Nam)."""
    if not birth_year:
        return None
    ref = today or date.today()
    age = ref.year - int(birth_year)
    return age if 0 < age <= 120 else None


def compute_needs(profile, today: date | None = None) -> EnergyNeeds:
    """Tính BMR/TDEE/đề xuất kcal từ hồ sơ. Thiếu trường nào thì ghi vào `missing_fields`."""
    needs = EnergyNeeds()
    if profile is None:
        needs.missing_fields = list(REQUIRED_FIELDS)
        return needs

    missing = [name for name in REQUIRED_FIELDS if getattr(profile, name, None) in (None, "")]
    needs.missing_fields = missing
    needs.age = age_from_birth_year(getattr(profile, "birth_year", None), today)
    if getattr(profile, "birth_year", None) and needs.age is None:
        needs.notes.append("Năm sinh không hợp lệ nên không tính được tuổi.")

    gender = getattr(profile, "gender", None)
    weight = getattr(profile, "weight_kg", None)
    height = getattr(profile, "height_cm", None)
    activity = getattr(profile, "activity_level", None)
    goal = getattr(profile, "goal", None)
    needs.activity_level = activity
    needs.goal = goal

    if gender in ("male", "female", "other") and weight and height and needs.age is not None:
        base = 10.0 * float(weight) + 6.25 * float(height) - 5.0 * needs.age
        needs.bmr = round(base + (5.0 if gender == "male" else -161.0), 1)
        if gender == "other":
            needs.notes.append("Giới tính 'khác': dùng hệ số của nữ (−161) và ghi rõ để người dùng biết.")
    elif not missing:
        needs.notes.append("Thiếu hoặc sai định dạng chỉ số cơ thể nên không tính được BMR.")

    if needs.bmr is not None and activity in ACTIVITY_FACTORS:
        needs.activity_factor = ACTIVITY_FACTORS[activity]
        needs.tdee = round(needs.bmr * needs.activity_factor, 1)

    if needs.tdee is not None:
        delta = GOAL_DELTA_KCAL.get(goal or "maintain", 0.0)
        needs.goal_delta_kcal = delta
        suggested = needs.tdee + delta
        floor = MIN_SAFE_KCAL.get(gender or "other", 1200.0)
        if suggested < floor:
            suggested = floor
            needs.applied_safety_floor = True
            needs.notes.append(
                f"Đề xuất theo công thức thấp hơn ngưỡng an toàn nên đã nâng lên {floor:.0f} kcal.")
        needs.suggested_kcal = round(suggested)
    return needs


def exercise_suggestion(needs: EnergyNeeds, remaining_kcal: float | None) -> dict:
    """Gợi ý vận động — chỉ dựa trên mức vận động trong hồ sơ và số kcal còn lại (nếu có)."""
    level = needs.activity_level
    mapping = {
        "sedentary": ("nhẹ", "đi bộ nhanh 20–30 phút hoặc giãn cơ tại nhà"),
        "light": ("nhẹ", "đi bộ nhanh 30 phút hoặc đạp xe nhẹ 20 phút"),
        "moderate": ("vừa", "30–45 phút cardio vừa (chạy bộ, đạp xe, bơi) và 2 buổi kháng lực/tuần"),
        "active": ("nặng", "45–60 phút cardio và 3 buổi kháng lực/tuần, có thể tăng dần cường độ"),
        "very_active": ("nặng", "duy trì 60 phút/ngày, chú ý nghỉ ngơi và bù nước"),
    }
    if level in mapping and remaining_kcal is not None and remaining_kcal < 0:
        intensity, detail = mapping[level]
        detail += " (hôm nay đang vượt mục tiêu nên chỉ nên vận động ở mức duy trì, không tăng thêm)"
    elif level in mapping:
        intensity, detail = mapping[level]
    else:
        return {"available": False, "reason": "chưa có mức vận động trong hồ sơ",
                "activity_level": level}
    return {"available": True, "activity_level": level,
            "activity_level_vi": ACTIVITY_LABELS_VI.get(level or "", ""),
            "intensity": intensity, "suggestion": detail}
