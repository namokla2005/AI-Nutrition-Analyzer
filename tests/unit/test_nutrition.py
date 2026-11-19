"""Kiểm thử công thức khẩu phần dinh dưỡng (§5.3).

Đây là phép tính cốt lõi của hệ thống: nếu sai thì mọi con số calo hiển thị đều sai.
"""
from __future__ import annotations

import pytest

from app.services.nutrition import (
    InvalidWeightError,
    aggregate,
    kcal_per_100g_from_macros,
    macro_energy_split,
    portion_amount,
    portion_values,
    round_nutrients,
    target_progress,
)

# Giá trị tham chiếu lấy từ bảng thành phần dinh dưỡng (ví dụ cơm trắng chín)
RICE = {
    "energy_kcal": 130.0,
    "protein_g": 2.7,
    "fat_g": 0.3,
    "carbohydrate_g": 28.2,
    "fiber_g": 0.4,
    "sodium_mg": 1.0,
}


class TestPortionAmount:
    def test_cong_thuc_co_ban_100g(self):
        # 100 g thì giá trị không đổi
        assert portion_amount(130.0, 100) == pytest.approx(130.0)

    def test_cong_thuc_150g(self):
        # 130 kcal/100 g × 150 g / 100 = 195 kcal
        assert portion_amount(130.0, 150) == pytest.approx(195.0)

    def test_cong_thuc_voi_so_luong(self):
        # 2 bát, mỗi bát 150 g -> 300 g -> 390 kcal
        assert portion_amount(130.0, 150, quantity=2) == pytest.approx(390.0)

    def test_gia_tri_thieu_tra_ve_none_chu_khong_phai_0(self):
        assert portion_amount(None, 150) is None

    def test_khoi_luong_khong_hop_le(self):
        for bad in (0, -50):
            with pytest.raises(InvalidWeightError):
                portion_amount(130.0, bad)

    def test_khoi_luong_vo_ly_bi_tu_choi(self):
        with pytest.raises(InvalidWeightError):
            portion_amount(130.0, 25000)

    def test_dau_vao_khong_phai_so(self):
        with pytest.raises(InvalidWeightError):
            portion_amount(130.0, "abc")  # type: ignore[arg-type]


class TestPortionValues:
    def test_toan_bo_chat_duoc_tinh_dung(self):
        out = portion_values(RICE, 200)
        assert out["energy_kcal"] == pytest.approx(260.0)
        assert out["protein_g"] == pytest.approx(5.4)
        assert out["fat_g"] == pytest.approx(0.6)
        assert out["carbohydrate_g"] == pytest.approx(56.4)

    def test_chat_thieu_van_la_none(self):
        out = portion_values({"energy_kcal": None, "protein_g": 5.0}, 100)
        assert out["energy_kcal"] is None
        assert out["protein_g"] == pytest.approx(5.0)

    def test_khong_tu_dien_0_cho_chat_thieu(self):
        out = portion_values(RICE, 100)
        assert "sugar_g" not in out  # không có trong nguồn thì không tự sinh ra

    def test_gia_tri_ket_hop_voi_map_rong(self):
        assert portion_values({}, 100) == {}


class TestRounding:
    def test_lam_tron_theo_tung_chat(self):
        out = round_nutrients({"energy_kcal": 195.44, "protein_g": 4.056, "sodium_mg": 1.25})
        assert out["energy_kcal"] == 195.4
        assert out["protein_g"] == 4.06
        assert out["sodium_mg"] == 1.2

    def test_none_duoc_giu_nguyen(self):
        assert round_nutrients({"energy_kcal": None})["energy_kcal"] is None


class TestAggregate:
    def test_tong_nhieu_dong(self):
        rows = [
            {"energy_kcal": 260.0, "protein_g": 5.4},
            {"energy_kcal": 195.0, "protein_g": 3.0},
        ]
        res = aggregate(rows, ["energy_kcal", "protein_g"])
        assert res.totals["energy_kcal"] == pytest.approx(455.0)
        assert res.totals["protein_g"] == pytest.approx(8.4)
        assert res.item_count == 2
        assert res.missing_fields == []

    def test_dong_thieu_du_lieu_duoc_bao_ro(self):
        rows = [
            {"energy_kcal": 260.0, "protein_g": 5.4},
            {"energy_kcal": 195.0, "protein_g": None},  # món không có số liệu protein
        ]
        res = aggregate(rows, ["energy_kcal", "protein_g"])
        assert res.totals["protein_g"] == pytest.approx(5.4)
        assert "protein_g" in res.missing_fields
        assert "energy_kcal" not in res.missing_fields
        assert res.items_without_energy == 0

    def test_tat_ca_thieu_thi_tong_la_none(self):
        res = aggregate([{"energy_kcal": None}], ["energy_kcal"])
        assert res.totals["energy_kcal"] is None
        assert res.items_without_energy == 1
        assert res.missing_fields == ["energy_kcal"]

    def test_danh_sach_rong(self):
        res = aggregate([], ["energy_kcal"])
        assert res.item_count == 0
        assert res.totals["energy_kcal"] is None


class TestTargetProgress:
    def test_tinh_phan_tram(self):
        out = target_progress(1500.0, 2000.0)
        assert out["percent"] == pytest.approx(75.0)
        assert out["remaining_kcal"] == pytest.approx(500.0)

    def test_thieu_du_lieu_thi_khong_bia(self):
        assert target_progress(None, 2000.0)["percent"] is None
        assert target_progress(1500.0, None)["percent"] is None


class TestMacroSplit:
    def test_phan_bo_4_4_9(self):
        out = macro_energy_split({"protein_g": 10.0, "carbohydrate_g": 20.0, "fat_g": 10.0})
        assert out["protein_kcal"] == pytest.approx(40.0)
        assert out["carbohydrate_kcal"] == pytest.approx(80.0)
        assert out["fat_kcal"] == pytest.approx(90.0)
        assert out["protein_percent"] == pytest.approx(19.0, abs=0.1)

    def test_thieu_chat_thi_tra_none(self):
        out = macro_energy_split({"protein_g": 10.0, "carbohydrate_g": None, "fat_g": 5.0})
        assert out["protein_percent"] is None


class TestAtwaterEstimate:
    def test_uoc_luong_4_4_9(self):
        # 2.7 g protein, 28.2 g carb, 0.3 g fat -> 10.8 + 112.8 + 2.7 = 126.3 kcal
        assert kcal_per_100g_from_macros(2.7, 28.2, 0.3) == pytest.approx(126.3)

    def test_thieu_du_lieu_tra_none(self):
        assert kcal_per_100g_from_macros(2.7, None, 0.3) is None
