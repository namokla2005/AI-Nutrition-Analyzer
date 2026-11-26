"""Tên hiển thị tiếng Việt và từ khoá tra cứu cho nhãn lớp của model nhận diện ảnh.

Nhãn trong checkpoint là mã lớp dạng snake_case không dấu (`banh_khot`). Giao diện
cần tên tiếng Việt để hiển thị, và phần gợi ý thực phẩm cần từ khoá tiếng Việt
(bảng Open Food Facts Việt Nam lưu tên có dấu trong `name_en`) để tra cứu ra món thật
thay vì danh sách rỗng.

Quy tắc: nhãn không có trong bảng thì hiển thị chính nó (đổi `_` thành khoảng trắng),
KHÔNG bịa tên món.
"""
from __future__ import annotations

# Nhãn lớp -> tên hiển thị tiếng Việt (29 lớp hiện có của model ảnh)
LABEL_VI: dict[str, str] = {
    # Món Việt Nam
    "pho_bo": "Phở bò",
    "pho_ga": "Phở gà",
    "bun_bo_hue": "Bún bò Huế",
    "bun_cha": "Bún chả",
    "bun_rieu": "Bún riêu",
    "bun_thit_nuong": "Bún thịt nướng",
    "bun_dau_mam_tom": "Bún đậu mắm tôm",
    "mi_quang": "Mì Quảng",
    "hu_tieu": "Hủ tiếu",
    "banh_mi": "Bánh mì",
    "banh_xeo": "Bánh xèo",
    "banh_cuon": "Bánh cuốn",
    "banh_beo": "Bánh bèo",
    "banh_khot": "Bánh khọt",
    "banh_chung": "Bánh chưng",
    "goi_cuon": "Gỏi cuốn",
    "nem_ran": "Nem rán (chả giò)",
    "cha_ca": "Chả cá",
    "canh_chua": "Canh chua",
    "com_tam": "Cơm tấm",
    "com_chien": "Cơm chiên",
    "xoi": "Xôi",
    # Món phương Tây (Food-101)
    "pizza": "Pizza",
    "hamburger": "Hamburger",
    "sushi": "Sushi",
    "pasta": "Mì Ý (pasta)",
    "salad": "Salad",
    "steak": "Bít tết",
    "fried_chicken": "Gà rán",
}

# Nhãn lớp -> danh sách từ khoá tra cứu thực phẩm, thử theo thứ tự tới khi có kết quả
SEARCH_TERMS: dict[str, list[str]] = {
    "pho_bo": ["phở bò", "pho bo", "pho", "noodle soup"],
    "pho_ga": ["phở gà", "pho ga", "chicken noodle soup"],
    "bun_bo_hue": ["bún bò huế", "bun bo hue", "bun bo"],
    "bun_cha": ["bún chả", "bun cha", "vermicelli"],
    "bun_rieu": ["bún riêu", "bun rieu", "crab noodle"],
    "bun_thit_nuong": ["bún thịt nướng", "bun thit nuong", "grilled pork noodle"],
    "bun_dau_mam_tom": ["bún đậu", "bun dau", "mắm tôm", "tofu noodle"],
    "mi_quang": ["mì quảng", "mi quang", "turmeric noodle"],
    "hu_tieu": ["hủ tiếu", "hu tieu", "rice noodle"],
    "banh_mi": ["bánh mì", "banh mi", "vietnamese sandwich"],
    "banh_xeo": ["bánh xèo", "banh xeo", "vietnamese pancake"],
    "banh_cuon": ["bánh cuốn", "banh cuon", "steamed rice roll"],
    "banh_beo": ["bánh bèo", "banh beo"],
    "banh_khot": ["bánh khọt", "banh khot"],
    "banh_chung": ["bánh chưng", "banh chung", "sticky rice cake"],
    "goi_cuon": ["gỏi cuốn", "goi cuon", "spring roll", "summer roll"],
    "nem_ran": ["nem rán", "chả giò", "cha gio", "spring roll", "egg roll"],
    "cha_ca": ["chả cá", "cha ca", "fish cake"],
    "canh_chua": ["canh chua", "sour soup"],
    "com_tam": ["cơm tấm", "com tam", "broken rice"],
    "com_chien": ["cơm chiên", "fried rice"],
    "xoi": ["xôi", "xoi", "sticky rice"],
    "pizza": ["pizza"],
    "hamburger": ["hamburger", "burger"],
    "sushi": ["sushi"],
    "pasta": ["pasta", "spaghetti"],
    "salad": ["salad"],
    "steak": ["steak", "beef steak"],
    "fried_chicken": ["fried chicken", "gà rán"],
}


def display_label(label: str) -> str:
    """Tên tiếng Việt để hiển thị; nhãn lạ thì trả về chính nó (đổi `_` thành khoảng trắng)."""
    if not label:
        return ""
    return LABEL_VI.get(label, label.replace("_", " ").strip())


def search_terms(label: str) -> list[str]:
    """Danh sách từ khoá tra cứu thực phẩm cho một nhãn (rỗng thì suy ra từ nhãn)."""
    if not label:
        return []
    return SEARCH_TERMS.get(label, [label.replace("_", " ")])
