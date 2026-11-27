"""Kiểm thử tính nhu cầu năng lượng (BMR/TDEE) và bộ máy đề xuất thực đơn."""
from __future__ import annotations

from datetime import date

import pytest

from app.services import plan_service
from app.services.nutrition_needs import (
    MIN_SAFE_KCAL,
    age_from_birth_year,
    compute_needs,
    exercise_suggestion,
)


class FakeProfile:
    def __init__(self, **kwargs) -> None:
        for key in ("gender", "birth_year", "height_cm", "weight_kg", "activity_level", "goal",
                    "daily_kcal_target", "note"):
            setattr(self, key, kwargs.get(key))


class TestEnergyNeeds:
    def test_cong_thuc_nam_khop_so_tinh_tay(self):
        # nam 65 kg, 172 cm, tuổi 22: 10×65 + 6,25×172 − 5×22 + 5 = 650 + 1075 − 110 + 5 = 1620
        profile = FakeProfile(gender="male", birth_year=2004, height_cm=172, weight_kg=65,
                              activity_level="light", goal="maintain")
        needs = compute_needs(profile, date(2026, 11, 28))
        assert needs.age == 22
        assert needs.bmr == pytest.approx(1620.0, abs=0.05)
        assert needs.tdee == pytest.approx(2227.5, abs=0.1)  # 1620 × 1,375
        assert needs.suggested_kcal == 2228  # giữ cân: không cộng trừ

    def test_cong_thuc_nu_va_muc_tieu_giam_can(self):
        # nữ 55 kg, 160 cm, tuổi 26: 10×55 + 6,25×160 − 5×26 − 161 = 1259
        profile = FakeProfile(gender="female", birth_year=2000, height_cm=160, weight_kg=55,
                              activity_level="moderate", goal="lose")
        needs = compute_needs(profile, date(2026, 11, 28))
        assert needs.bmr == pytest.approx(1259.0, abs=0.05)
        assert needs.goal_delta_kcal == -500.0
        # mã làm tròn TDEE trước rồi mới trừ 500: round(1951,5 − 500) = 1452
        assert needs.suggested_kcal == 1452

    def test_nguong_an_toan_khong_de_xuat_qua_thap(self):
        profile = FakeProfile(gender="female", birth_year=1960, height_cm=150, weight_kg=45,
                              activity_level="sedentary", goal="lose")
        needs = compute_needs(profile, date(2026, 11, 28))
        assert needs.applied_safety_floor is True
        assert needs.suggested_kcal == MIN_SAFE_KCAL["female"]
        assert any("ngưỡng an toàn" in note for note in needs.notes)

    def test_thieu_chi_so_thi_bao_ro_thieu_gi(self):
        needs = compute_needs(FakeProfile(gender="male", weight_kg=70))
        assert needs.bmr is None and needs.tdee is None and needs.suggested_kcal is None
        assert "height_cm" in needs.missing_fields and "birth_year" in needs.missing_fields
        assert "activity_level" in needs.missing_fields

    def test_ho_so_rong(self):
        assert compute_needs(None).missing_fields == list(
            ("gender", "birth_year", "height_cm", "weight_kg", "activity_level"))

    def test_tuoi_tu_nam_sinh(self):
        assert age_from_birth_year(2000, date(2026, 11, 28)) == 26
        assert age_from_birth_year(None) is None
        assert age_from_birth_year(1800, date(2026, 11, 28)) is None


class TestExerciseSuggestion:
    def test_theo_muc_van_dong(self):
        needs = compute_needs(FakeProfile(gender="male", birth_year=2000, height_cm=170,
                                         weight_kg=65, activity_level="active"))
        result = exercise_suggestion(needs, 300)
        assert result["available"] is True
        assert result["intensity"] == "nặng" and "45–60 phút" in result["suggestion"]

    def test_chua_khai_van_dong(self):
        result = exercise_suggestion(compute_needs(FakeProfile()), None)
        assert result["available"] is False and "chưa có mức vận động" in result["reason"]

    def test_vuot_muc_tieu_thi_them_canh_bao(self):
        needs = compute_needs(FakeProfile(gender="male", birth_year=2000, height_cm=170,
                                         weight_kg=65, activity_level="light"))
        assert "vượt mục tiêu" in exercise_suggestion(needs, -200)["suggestion"]


class TestNoteConstraints:
    def test_ghi_chu_trong_thi_khong_ap_dung_gi(self):
        result = plan_service.parse_note_constraints("")
        assert result["applied"] == [] and result["exclude_tags"] == []

    def test_di_ung_tom_ca(self):
        result = plan_service.parse_note_constraints("dị ứng tôm cá, không ăn thịt bò")
        assert "seafood" in result["exclude_tags"] and "meat" in result["exclude_tags"]
        assert result["applied"]

    def test_chi_nhac_ten_mon_thi_khong_loai(self):
        # ghi chú chỉ nói "thích ăn cá" -> KHÔNG được hiểu thành dị ứng cá
        result = plan_service.parse_note_constraints("thích ăn cá vào cuối tuần")
        assert "seafood" not in result["exclude_tags"]

    def test_an_chay_va_thuan_chay(self):
        chay = plan_service.parse_note_constraints("ăn chay")
        assert "meat" in chay["exclude_tags"] and "egg" not in chay["exclude_tags"]
        thuan = plan_service.parse_note_constraints("thuần chay")
        assert "egg" in thuan["exclude_tags"] and "dairy" in thuan["exclude_tags"]

    def test_tang_co_va_tieu_duong(self):
        result = plan_service.parse_note_constraints("tập gym, có tiểu đường")
        assert result["prioritise_protein"] is True and result["diabetes"] is True


class TestFitBudget:
    def _item(self, kcal: float, grams: float, role: str, key: str) -> dict:
        return {"component_key": key, "name_vi": key, "kcal": kcal, "grams": grams, "role": role,
                "protein_g": 1.0, "fat_g": 1.0, "carbohydrate_g": 1.0, "fiber_g": None,
                "sugar_g": None}

    def test_co_khau_phan_cho_khop_ngan_sach(self):
        items = [self._item(280.0, 200.0, "carb", "com_trang"),
                 self._item(200.0, 120.0, "protein", "uc_ga")]
        fitted, note = plan_service._fit_budget(items, 300.0)
        total = sum(item["kcal"] for item in fitted)
        assert total <= 300.0 * 1.08
        assert note and ("co khẩu phần" in note or "giảm cả phần đạm" in note)

    def test_khong_dung_den_khi_da_trong_ngan_sach(self):
        items = [self._item(100.0, 100.0, "carb", "com_trang")]
        fitted, note = plan_service._fit_budget(items, 400.0)
        assert note is None and fitted[0]["grams"] == 100.0

    def test_bo_bot_mon_khi_ngan_sach_qua_nho(self):
        items = [self._item(131.0, 150.0, "dairy", "sua_tuoi"),
                 self._item(61.0, 100.0, "fruit", "tao")]
        fitted, note = plan_service._fit_budget(items, 120.0)
        assert len(fitted) == 1 and "bỏ bớt" in note
