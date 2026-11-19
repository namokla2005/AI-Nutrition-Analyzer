"""Nghiệp vụ tài khoản: đăng ký, đăng nhập, đổi mật khẩu, xóa tài khoản."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, needs_rehash, verify_password
from app.core.utils import utcnow
from app.models import User, UserProfile

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Lỗi nghiệp vụ xác thực; thông báo đã ở dạng hiển thị được cho người dùng."""

    def __init__(self, message: str, code: str = "auth_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == normalize_email(email))).first()


def register_user(db: Session, email: str, password: str, full_name: str | None = None) -> User:
    email = normalize_email(email)
    if get_by_email(db, email) is not None:
        raise AuthError("Email này đã được đăng ký.", "email_taken")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=(full_name or None),
        is_active=True,
    )
    user.profile = UserProfile()
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Đã tạo tài khoản mới (id=%s)", user.id)  # không ghi email/mật khẩu vào log
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_by_email(db, email)
    # Luôn thực hiện so khớp để thời gian phản hồi không tiết lộ email có tồn tại hay không.
    if user is None:
        verify_password(password, hash_password("dummy-password-for-timing"))
        raise AuthError("Email hoặc mật khẩu không đúng.", "invalid_credentials")
    if not verify_password(password, user.password_hash):
        raise AuthError("Email hoặc mật khẩu không đúng.", "invalid_credentials")
    if not user.is_active:
        raise AuthError("Tài khoản đã bị khóa.", "inactive")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    user.last_login_at = utcnow()
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Mật khẩu hiện tại không đúng.", "invalid_credentials")
    if verify_password(new_password, user.password_hash):
        raise AuthError("Mật khẩu mới phải khác mật khẩu hiện tại.", "same_password")
    user.password_hash = hash_password(new_password)
    db.commit()


def update_profile(db: Session, user: User, **fields) -> UserProfile:
    profile = user.profile
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    for key, value in fields.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    if fields.get("full_name") is not None:
        user.full_name = fields["full_name"]
    db.commit()
    db.refresh(profile)
    return profile


def delete_account(db: Session, user: User, password: str) -> None:
    """Xóa tài khoản. Xóa theo CASCADE: profile, meals, meal_items, chat, ảnh."""
    if not verify_password(password, user.password_hash):
        raise AuthError("Mật khẩu không đúng.", "invalid_credentials")
    user_id = user.id
    db.delete(user)
    db.commit()
    logger.info("Đã xóa tài khoản id=%s cùng toàn bộ dữ liệu liên quan", user_id)
