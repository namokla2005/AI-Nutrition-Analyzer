"""API hồ sơ người dùng. Mọi endpoint chỉ tác động lên tài khoản đang đăng nhập."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_user
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    MessageOut,
    UserDetailOut,
    UserUpdateRequest,
)
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserDetailOut, summary="Xem hồ sơ cá nhân")
def get_me(user: User = Depends(require_user)) -> User:
    return user


@router.put("/me", response_model=UserDetailOut, summary="Cập nhật hồ sơ cá nhân")
def update_me(
    payload: UserUpdateRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> User:
    fields: dict = {}
    if payload.full_name is not None:
        fields["full_name"] = payload.full_name.strip() or None
    if payload.profile is not None:
        fields.update(payload.profile.model_dump())
    auth_service.update_profile(db, user, **fields)
    db.refresh(user)
    return user


@router.put("/me/password", response_model=MessageOut, summary="Đổi mật khẩu")
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    try:
        auth_service.change_password(db, user, payload.current_password, payload.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    return MessageOut(detail="Đã đổi mật khẩu. Hãy đăng nhập lại.")


@router.delete("/me", response_model=MessageOut, summary="Xóa tài khoản")
def delete_me(
    payload: DeleteAccountRequest,
    response: Response,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    if payload.confirm != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Để xác nhận xóa tài khoản, hãy gõ chính xác DELETE.",
        )
    try:
        auth_service.delete_account(db, user, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    response.delete_cookie(key="ana_session", path="/")
    return MessageOut(detail="Tài khoản và toàn bộ dữ liệu liên quan đã được xóa.")
