"""Tiện ích dùng chung: thời gian UTC, chuẩn hóa tên tiếng Việt, kích thước file."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9\s]+")


def utcnow() -> datetime:
    """UTC naive (SQLite không lưu timezone). Toàn bộ DB dùng UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def strip_diacritics(text: str) -> str:
    """'Phở bò' -> 'pho bo' (hỗ trợ tìm kiếm không dấu)."""
    if not text:
        return ""
    # đ/Đ không được NFD tách, phải xử lý riêng
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_name(text: str) -> str:
    """Khóa tìm kiếm: bỏ dấu, hạ chữ thường, bỏ ký tự đặc biệt, gộp khoảng trắng."""
    s = strip_diacritics((text or "").lower())
    s = _NON_ALNUM.sub(" ", s)
    return _WS.sub(" ", s).strip()


def slugify(text: str) -> str:
    return _WS.sub("-", normalize_name(text)).strip("-")


def human_bytes(n: int) -> str:
    step = 1024.0
    val = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < step or unit == "TB":
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= step
    return f"{val:.1f} TB"


def round_or_none(value, digits: int = 2):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None
