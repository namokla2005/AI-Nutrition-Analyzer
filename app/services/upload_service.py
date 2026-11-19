"""Lưu ảnh người dùng tải lên một cách an toàn (§13).

Kiểm tra nhiều lớp trước khi lưu:
1. Kích thước (đọc tối đa max+1 byte để không nạp file vô hạn vào RAM).
2. Chữ ký nhị phân (magic bytes) của JPEG/PNG/WEBP.
3. Pillow phải mở và xác thực được ảnh thật.
4. Đuôi file lưu trên đĩa do hệ thống tự quyết theo định dạng phát hiện được
   (không dùng tên file người dùng gửi lên) -> chống ghi đè/đường dẫn thoát.
Không chấp nhận file thực thi/script, kể cả khi đổi đuôi thành .jpg.
"""
from __future__ import annotations

import hashlib
import io
import logging
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import BASE_DIR, settings
from app.core.utils import utcnow
from app.models import FoodImage

logger = logging.getLogger(__name__)

MAGIC_SIGNATURES: dict[bytes, tuple[str, str]] = {
    b"\xff\xd8\xff": ("image/jpeg", "jpg"),
    b"\x89PNG\r\n\x1a\n": ("image/png", "png"),
}
WEBP_PREFIX = b"RIFF"
WEBP_MARK = b"WEBP"

# Đuôi file không bao giờ được chấp nhận, dù nội dung có hợp lệ
FORBIDDEN_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".com", ".scr", ".msi", ".ps1", ".sh",
    ".py", ".js", ".jar", ".php", ".vbs", ".hta", ".zip", ".rar", ".7z",
}


class UploadError(Exception):
    def __init__(self, message: str, code: str = "invalid_upload") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def detect_image_type(prefix: bytes) -> tuple[str, str] | None:
    """Trả về (mime, đuôi file) hoặc None nếu không nhận dạng được."""
    for magic, info in MAGIC_SIGNATURES.items():
        if prefix.startswith(magic):
            return info
    if prefix.startswith(WEBP_PREFIX) and prefix[8:12] == WEBP_MARK:
        return ("image/webp", "webp")
    return None


def validate_image_bytes(content: bytes, declared_name: str | None = None) -> tuple[str, str, int, int]:
    """Trả về (mime, ext, width, height) nếu ảnh hợp lệ; ném UploadError nếu không."""
    if not content:
        raise UploadError("File tải lên rỗng.")
    if len(content) > settings.max_upload_bytes:
        raise UploadError(
            f"Ảnh vượt quá giới hạn {settings.max_upload_mb} MB.", "too_large"
        )

    if declared_name:
        ext = Path(declared_name).suffix.lower()
        if ext in FORBIDDEN_EXTENSIONS:
            raise UploadError(f"Không cho phép tải lên tệp loại {ext}.", "forbidden_type")

    detected = detect_image_type(content[:16])
    if detected is None:
        raise UploadError(
            "Nội dung tệp không phải ảnh JPEG/PNG/WEBP hợp lệ.", "not_an_image"
        )
    mime, ext = detected
    if mime not in settings.allowed_image_mimes:
        raise UploadError(f"Định dạng {mime} không được hỗ trợ.", "unsupported_mime")

    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover
        raise UploadError("Thiếu thư viện Pillow để kiểm tra ảnh.", "no_pillow") from exc

    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()  # kiểm tra cấu trúc file thật sự
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
            real_format = (img.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UploadError("Không đọc được ảnh (file hỏng hoặc bị cắt).", "corrupt_image") from exc

    expected = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}[mime]
    if real_format != expected:
        raise UploadError(
            f"Nội dung ảnh ({real_format or 'không rõ'}) không khớp với định dạng khai báo.",
            "mime_mismatch",
        )
    if width < 32 or height < 32:
        raise UploadError("Ảnh quá nhỏ (tối thiểu 32×32).", "too_small")

    return mime, ext, width, height


def save_user_image(
    db: Session,
    user_id: int,
    filename: str | None,
    content: bytes,
    purpose: str = "recognition",
) -> FoodImage:
    mime, ext, width, height = validate_image_bytes(content, filename)
    digest = hashlib.sha256(content).hexdigest()

    now = utcnow()
    rel_dir = Path(str(user_id)) / f"{now.year:04d}" / f"{now.month:02d}"
    folder = Path(settings.upload_dir) / rel_dir
    folder.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    full_path = folder / stored_name
    full_path.write_bytes(content)

    image = FoodImage(
        user_id=user_id,
        rel_path=str(Path(rel_dir) / stored_name).replace("\\", "/"),
        original_name=(Path(filename).name[:200] if filename else None),
        mime_type=mime,
        size_bytes=len(content),
        width=width,
        height=height,
        sha256=digest,
        purpose=purpose,
        retained_until=now + timedelta(days=settings.image_storage_days),
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    logger.info("Đã lưu ảnh id=%s (%s, %d B) cho user=%s", image.id, mime, len(content), user_id)
    return image


def absolute_path(image: FoodImage) -> Path:
    """Đường dẫn tuyệt đối, có kiểm tra không thoát khỏi thư mục uploads."""
    root = Path(settings.upload_dir).resolve()
    target = (root / image.rel_path).resolve()
    if root not in target.parents and target != root:
        raise UploadError("Đường dẫn ảnh không hợp lệ.", "bad_path")
    return target


def purge_expired(db: Session, user_id: int | None = None) -> int:
    """Xóa ảnh đã quá hạn lưu trữ (cả bản ghi và file trên đĩa)."""
    from sqlalchemy import select

    stmt = select(FoodImage).where(FoodImage.retained_until.is_not(None),
                                   FoodImage.retained_until < utcnow())
    if user_id is not None:
        stmt = stmt.where(FoodImage.user_id == user_id)
    removed = 0
    for image in db.scalars(stmt):
        try:
            absolute_path(image).unlink(missing_ok=True)
        except UploadError:
            pass
        db.delete(image)
        removed += 1
    if removed:
        db.commit()
    return removed
