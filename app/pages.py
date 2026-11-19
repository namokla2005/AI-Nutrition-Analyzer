"""Các trang giao diện (server-rendered shell) cho website tiếng Việt.

Trang chỉ trả về khung HTML; dữ liệu được nạp từ API /api/v1 bằng JS kèm cookie phiên,
nên không có số liệu nào bị nhúng cứng vào HTML.

Quy ước cho mọi trang kế thừa `base.html`:
- Đặt tên trang:  {% block page_id %}key{% endblock %}  (khớp data-nav trên sidebar)
- Tiêu đề:        {% block heading %}, {% block title %}
- Nội dung:       {% block content %}; script riêng: {% block scripts %}
- Dùng `ANA` (app/static/js/api.js) cho mọi lời gọi API, không tự viết fetch.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
from app.core.database import get_db
from app.core.deps import get_current_user_optional

TEMPLATES_DIR = Path(BASE_DIR) / "app" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)

# (đường dẫn, template, khoá nav, tiêu đề)
PAGES: list[tuple[str, str, str, str]] = [
    ("/dashboard", "dashboard.html", "dashboard", "Tổng quan"),
    ("/recognize", "recognize.html", "recognize", "Nhận diện thực phẩm từ ảnh"),
    ("/foods", "foods.html", "foods", "Tra cứu thực phẩm"),
    ("/diary", "diary.html", "diary", "Nhật ký ăn uống"),
    ("/statistics", "statistics.html", "statistics", "Thống kê dinh dưỡng"),
    ("/assistant", "assistant.html", "assistant", "Trợ lý AI"),
    ("/profile", "profile.html", "profile", "Tài khoản của tôi"),
]

PUBLIC_PAGES = {"/login", "/register"}


def _render(request: Request, template: str, current_user=None, **context) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template,
        {"current_user": current_user, "app_version": "1.0.0", **context},
    )


@router.get("/", include_in_schema=False)
def root(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    user = get_current_user_optional(request, db)
    return RedirectResponse("/dashboard" if user else "/login", status_code=303)


@router.get("/login", include_in_schema=False)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return _render(request, "login.html", None)


@router.get("/register", include_in_schema=False)
def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return _render(request, "register.html", None)


def _make_page(template: str, page_key: str, title: str):
    def _handler(request: Request, db: Session = Depends(get_db)):
        user = get_current_user_optional(request, db)
        if user is None:
            return RedirectResponse(f"/login?next={request.url.path}", status_code=303)
        # Nếu template của trang chưa được xây (giai đoạn 4 đang làm dở),
        # hiển thị thông báo trung thực thay vì lỗi 500.
        target = template if (TEMPLATES_DIR / template).exists() else "pending.html"
        return _render(request, target, user, page_key=page_key, feature=title)

    return _handler


for _path, _template, _key, _title in PAGES:
    router.add_api_route(
        _path,
        _make_page(_template, _key, _title),
        methods=["GET"],
        include_in_schema=False,
        name=f"page{_path.replace('/', '_')}",
    )
