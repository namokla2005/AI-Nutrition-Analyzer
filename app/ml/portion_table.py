"""Khẩu phần tham khảo cho một suất ăn của từng món nhận diện được từ ảnh.

Đây là con số THAM KHẢO (một suất ăn thông thường ở Việt Nam), không phải kết quả đo từ ảnh:
model thị giác 0,8B không ước lượng được khối lượng (đã đo: cùng một ảnh phở, model trả 400 g
nhưng ảnh cơm tấm trả "6 g"). Vì vậy giao diện điền sẵn khẩu phần tham khảo này và người dùng
sửa lại theo thực tế; mọi giá trị dinh dưỡng vẫn tính từ CSDL theo đúng khối lượng đó.
"""
from __future__ import annotations

REFERENCE_PORTION_G: dict[str, float] = {
    # món nước (một tô)
    "pho_bo": 450, "pho_ga": 450, "bun_bo_hue": 450, "bun_rieu": 450, "hu_tieu": 450,
    "mi_quang": 400, "banh_canh": 450, "bun_mam": 450, "banh_da_cua": 450, "chao": 350,
    "mi_xao": 350,
    # bún/trộn (một suất)
    "bun_cha": 400, "bun_thit_nuong": 400, "bun_dau_mam_tom": 400, "banh_uot": 250,
    # cơm (một đĩa)
    "com_tam": 350, "com_chien": 350, "com_ga": 350, "bo_kho": 350,
    # món ăn kèm / cuốn / chiên
    "banh_mi": 150, "banh_xeo": 200, "banh_cuon": 250, "banh_beo": 200, "banh_khot": 200,
    "banh_chung": 200, "banh_bao": 120, "banh_tom": 150, "banh_trang_nuong": 120,
    "goi_cuon": 120, "nem_ran": 150, "goi_ga": 250, "cha_ca": 200,
    # canh / món kho / xôi / chè
    "canh_chua": 300, "thit_kho_trung": 250, "ca_kho_to": 250, "xoi": 300, "xoi_xeo": 300,
    "che_ba_mau": 250,
    # món phương Tây (Food-101)
    "pizza": 300, "hamburger": 220, "sushi": 250, "pasta": 350, "salad": 200, "steak": 250,
    "fried_chicken": 200,
}
DEFAULT_PORTION_G = 300.0
PORTION_NOTE = ("Khẩu phần tham khảo cho một suất ăn thông thường; hãy sửa lại theo lượng thật "
                "trong ảnh trước khi ghi vào nhật ký.")


def reference_portion(label: str) -> dict:
    """Trả về khẩu phần tham khảo (gam) cho nhãn lớp. Nhãn lạ -> dùng mức mặc định và nói rõ."""
    grams = REFERENCE_PORTION_G.get(label)
    if grams is None:
        return {"label": label, "grams": DEFAULT_PORTION_G, "is_reference": False,
                "note": f"Chưa có khẩu phần tham khảo cho “{label}”: dùng mức mặc định "
                        f"{DEFAULT_PORTION_G:.0f} g, cần người dùng sửa lại."}
    return {"label": label, "grams": float(grams), "is_reference": True, "note": PORTION_NOTE}
