"""API xác thực: đăng ký, đăng nhập, đăng xuất."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_user
from app.core.security import create_session_token
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    MessageOut,
    RegisterRequest,
    UserDetailOut,
    UserOut,
)
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user_id),
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",       # chặn cookie bị gửi kèm request POST từ site khác
        secure=settings.cookie_secure,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    try:
        user = auth_service.register_user(db, payload.email, payload.password, payload.full_name)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    _set_session_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserDetailOut, summary="Đăng nhập")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    try:
        user = auth_service.authenticate(db, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Cookie"},
        ) from exc
    _set_session_cookie(response, user.id)
    return user


@router.post("/logout", response_model=MessageOut, summary="Đăng xuất")
def logout(response: Response) -> MessageOut:
    _clear_session_cookie(response)
    return MessageOut(detail="Đã đăng xuất.")


@router.get("/session", response_model=UserOut, summary="Thông tin phiên hiện tại")
def session_info(user: User = Depends(require_user)) -> User:
    return user
