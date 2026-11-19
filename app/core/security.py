"""Bảo mật: hash mật khẩu Argon2id + cookie phiên ký bằng itsdangerous.

Nguyên tắc:
- Không bao giờ ghi mật khẩu/token vào log.
- Mật khẩu chỉ tồn tại dưới dạng hash Argon2id trong DB.
- Cookie phiên là token ký (stateless) chứa user_id + mốc thời gian.
"""
from __future__ import annotations

import logging

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

logger = logging.getLogger(__name__)

_hasher = PasswordHasher(
    time_cost=3,       # ~0.1-0.2s trên i5-8400H
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Trả về True/False; không ném lỗi và không log nội dung mật khẩu."""
    if not password or not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def validate_password_strength(password: str) -> list[str]:
    """Trả về danh sách lỗi (rỗng = hợp lệ)."""
    errors: list[str] = []
    if len(password or "") < MIN_PASSWORD_LENGTH:
        errors.append(f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự.")
    if password and not any(c.isalpha() for c in password):
        errors.append("Mật khẩu phải chứa ít nhất một chữ cái.")
    if password and not any(c.isdigit() for c in password):
        errors.append("Mật khẩu phải chứa ít nhất một chữ số.")
    return errors


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.ensure_secret_key(), salt="ana.session.v1")


def create_session_token(user_id: int) -> str:
    return _serializer().dumps({"uid": int(user_id)})


def read_session_token(token: str) -> int | None:
    """Đọc user_id từ cookie phiên; None nếu token sai/hết hạn."""
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=settings.session_ttl_hours * 3600)
    except SignatureExpired:
        return None
    except BadSignature:
        logger.debug("Cookie phiên không hợp lệ (chữ ký sai).")
        return None
    uid = data.get("uid") if isinstance(data, dict) else None
    return int(uid) if isinstance(uid, int) else None
