"""FastAPI dependencies: xác thực người dùng qua cookie phiên.

Nguyên tắc bảo mật (§7.7, §7.8): user_id LUÔN lấy từ phiên phía server,
không bao giờ nhận user_id từ client.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import read_session_token
from app.models import User


def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    user_id = read_session_token(token)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để thực hiện thao tác này.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user
