"""Kiểm thử lớp kiểm chứng số liệu của trợ lý AI.

Mục đích: bảo đảm trợ lý KHÔNG bao giờ để lọt con số có đơn vị mà dữ liệu thật không có,
đồng thời không "buộc tội oan" những con số hợp lệ (làm tròn, ngày tháng, đơn vị thiếu
tham chiếu trong ngữ cảnh).
"""
from __future__ import annotations

from app.services.assistant_service import (
    context_numbers,
    official_numbers_text,
    verify_numbers,
)

CONTEXT = {
    "today_totals": {"energy_kcal": 842.0, "protein_g": 21.28, "fat_g": 2.08},
    "today_by_meal_type": [{"meal_type": "lunch", "calories": 842.0, "item_count": 2}],
    "today_target": {"target_kcal": 2150.0, "percent": 39.2, "remaining_kcal": 1308.0},
    "today_meals": [{"meal_type": "lunch",
                     "items": [{"name": "RICE-A-RONI", "weight_grams": 200, "kcal": 712.0}]}],
    "week": {"totals": {"energy_kcal": 842.0}, "days_with_data": 1},
}


class TestVerifyNumbers:
    def test_so_dung_thi_dat(self):
        result = verify_numbers("Tổng năng lượng hôm nay là 842 kcal.", CONTEXT)
        assert result["verified"] is True
        assert result["checked"] == 1
        assert result["unsupported"] == []

    def test_chap_nhan_lam_tron_trong_1_5_kcal(self):
        assert verify_numbers("Bạn đã ăn 841,7 kcal.", CONTEXT)["verified"] is True
        assert verify_numbers("Bạn đã ăn 843 kcal.", CONTEXT)["verified"] is True
        assert verify_numbers("Bạn đã ăn 844 kcal.", CONTEXT)["verified"] is False

    def test_bat_duoc_so_bia(self):
        result = verify_numbers("Hôm nay bạn đã ăn 260 kcal.", CONTEXT)
        assert result["verified"] is False
        assert result["unsupported"] == ["260 kcal"]
        assert result["checked"] == 1

    def test_bat_duoc_so_gram_bia(self):
        result = verify_numbers("Bạn nạp 99 g đạm.", CONTEXT)
        assert result["verified"] is False
        assert result["unsupported"] == ["99 g"]

    def test_bo_qua_so_khong_co_don_vi(self):
        # ngày tháng và số trần không đủ căn cứ để kết luận -> không đánh dấu sai
        result = verify_numbers("Ngày 27/11/2026 bạn ăn 842 kcal.", CONTEXT)
        assert result["verified"] is True
        assert result["checked"] == 1

    def test_bo_qua_don_vi_khong_co_tham_chieu(self):
        # ngữ cảnh không có số phần trăm nào -> không buộc tội con số phần trăm
        context = {"today_totals": {"energy_kcal": 100.0}}
        assert verify_numbers("Bạn đã đạt 87%.", context)["verified"] is True

    def test_cau_tra_loi_rong_thi_dat(self):
        assert verify_numbers("", CONTEXT)["verified"] is True
        assert verify_numbers(None, CONTEXT)["verified"] is True

    def test_chua_co_bua_an_nao_thi_moi_so_kcal_deu_la_bia(self):
        empty = {"today_totals": {"energy_kcal": None}, "today_meals": [],
                 "today_by_meal_type": [], "today_meal_count": 0}
        result = verify_numbers("Hôm nay bạn đã ăn 260 kcal.", empty)
        assert result["verified"] is False
        assert result["unsupported"] == ["260 kcal"]
        assert result["absent_kinds"] == ["energy", "mass"]
        # nói đúng "0 kcal" thì phải được chấp nhận
        assert verify_numbers("Hôm nay bạn chưa ăn gì (0 kcal).", empty)["verified"] is True

    def test_co_bua_an_thi_khong_ap_danh_dau_trong(self):
        assert "absent_kinds" in verify_numbers("ok", CONTEXT)
        assert verify_numbers("ok", CONTEXT)["absent_kinds"] == []

    def test_so_kieu_viet_nam_co_hang_nghin(self):
        context = {"today_totals": {"energy_kcal": 1842.0}}
        assert verify_numbers("Hôm nay 1.842 kcal.", context)["verified"] is True

    def test_khong_bao_dong_nham_so_thap_phan_kieu_anh(self):
        # '260.0 kcal' / '200.0 g' là số ĐÚNG, không được đọc thành 2600 / 2000 rồi báo sai
        ctx = {"today_totals": {"energy_kcal": 260.0, "protein_g": 5.2},
               "today_meals": [{"items": [{"name": "Cơm", "weight_grams": 200.0, "kcal": 260.0}]}]}
        result = verify_numbers("Bữa ăn 200.0 g cung cấp 260.0 kcal.", ctx)
        assert result["verified"] is True, result["unsupported"]
        assert result["checked"] == 2

    def test_so_kieu_viet_nam_co_ca_hang_nghin_lan_thap_phan(self):
        assert verify_numbers("Hôm nay 1.842,5 kcal.",
                              {"today_totals": {"energy_kcal": 1842.5}})["verified"] is True
        assert verify_numbers("Hôm nay 1,842.5 kcal.",
                              {"today_totals": {"energy_kcal": 1842.5}})["verified"] is True


class TestContextNumbers:
    def test_phan_loai_theo_don_vi(self):
        buckets = context_numbers(CONTEXT)
        assert 842.0 in buckets["energy"]
        assert 2150.0 in buckets["energy"]
        assert 712.0 in buckets["energy"]
        assert 21.28 in buckets["mass"]
        assert 200.0 in buckets["mass"]
        assert 39.2 in buckets["percent"]

    def test_ngu_canh_rong(self):
        assert context_numbers({}) == {"energy": [], "mass": [], "percent": []}


def test_official_numbers_text_lay_tu_du_lieu():
    text = official_numbers_text(CONTEXT)
    assert "842,0 kcal" in text
    assert "đạm 21,3 g" in text
    assert "mục tiêu 2150 kcal" in text
    assert "lunch 842,0 kcal" in text


def test_official_numbers_text_khi_chua_co_du_lieu():
    # không có dữ liệu thì phải nói thẳng là chưa có, không trả chuỗi rỗng
    assert official_numbers_text({}) == "hôm nay chưa ghi nhận bữa ăn nào (0 kcal)"
    assert official_numbers_text({"today_totals": {}, "today_by_meal_type": []}) == (
        "hôm nay chưa ghi nhận bữa ăn nào (0 kcal)")
