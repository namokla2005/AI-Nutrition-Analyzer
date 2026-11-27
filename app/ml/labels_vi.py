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
    # Món mới bổ sung (đang thu thập ảnh để huấn luyện)
    "banh_bao": "Bánh bao",
    "chao": "Cháo",
    "banh_canh": "Bánh canh",
    "bun_mam": "Bún mắm",
    "banh_uot": "Bánh ướt",
    "banh_tom": "Bánh tôm",
    "bo_kho": "Bò kho",
    "thit_kho_trung": "Thịt kho trứng",
    "ca_kho_to": "Cá kho tộ",
    "com_ga": "Cơm gà",
    "xoi_xeo": "Xôi xéo",
    "che_ba_mau": "Chè ba màu",
    "banh_da_cua": "Bánh đa cua",
    "goi_ga": "Gỏi gà",
    "banh_trang_nuong": "Bánh tráng nướng",
    "mi_xao": "Mì xào",
    # Món phương Tây (Food-101) — hiển thị kèm tên tiếng Việt cho dễ đọc
    "pizza": "Bánh pizza (Ý)",
    "hamburger": "Bánh kẹp thịt (hamburger)",
    "sushi": "Cơm cuộn sushi (Nhật)",
    "pasta": "Mì Ý (pasta)",
    "salad": "Rau trộn (salad)",
    "steak": "Bít tết (bò nướng)",
    "fried_chicken": "Gà rán",
}

# Nhãn lớp -> danh sách từ khoá tra cứu thực phẩm, thử theo thứ tự tới khi có kết quả
SEARCH_TERMS: dict[str, list[str]] = {
    # lớp mới đang thu thập ảnh
    "banh_bao": ["bánh bao", "banh bao", "steamed bun", "bun"],
    "chao": ["cháo", "chao", "congee", "rice porridge"],
    "banh_canh": ["bánh canh", "banh canh", "thick noodle"],
    "bun_mam": ["bún mắm", "bun mam", "vermicelli"],
    "banh_uot": ["bánh ướt", "banh uot", "steamed rice roll"],
    "banh_tom": ["bánh tôm", "banh tom", "shrimp cake"],
    "bo_kho": ["bò kho", "bo kho", "beef stew"],
    "thit_kho_trung": ["thịt kho", "thit kho", "braised pork"],
    "ca_kho_to": ["cá kho", "ca kho", "braised fish"],
    "com_ga": ["cơm gà", "com ga", "chicken rice"],
    "xoi_xeo": ["xôi xéo", "xoi xeo", "sticky rice"],
    "che_ba_mau": ["chè", "che", "dessert"],
    "banh_da_cua": ["bánh đa cua", "banh da cua", "crab noodle"],
    "goi_ga": ["gỏi gà", "goi ga", "chicken salad"],
    "banh_trang_nuong": ["bánh tráng", "banh trang", "rice paper"],
    "mi_xao": ["mì xào", "mi xao", "fried noodle"],
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
