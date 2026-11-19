"""Application settings (12-factor style: everything overridable via .env).

Không lưu secret trong source code. SECRET_KEY phải được đặt trong .env.
"""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "AI Nutrition Analyzer"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # --- Security ---
    secret_key: str = ""
    session_cookie_name: str = "ana_session"
    session_ttl_hours: int = 72
    cookie_secure: bool = False  # đặt true khi chạy sau HTTPS

    # --- Database ---
    database_url: str = ""

    # --- Hiển thị theo giờ địa phương ---
    # Dữ liệu lưu UTC; thống kê theo ngày/tuần/tháng phải quy đổi sang giờ Việt Nam
    timezone_offset_hours: float = 7.0
    timezone_label: str = "UTC+07:00"

    # --- Uploads ---
    upload_dir: Path = BASE_DIR / "uploads"
    max_upload_mb: int = 8
    allowed_image_mimes: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    image_storage_days: int = 30  # chính sách lưu trữ ảnh người dùng

    # --- Models ---
    image_model_dir: Path = BASE_DIR / "models" / "image"
    regression_model_dir: Path = BASE_DIR / "models" / "regression"
    backup_dir: Path = BASE_DIR / "data" / "backups"

    # --- Nhận diện ảnh ---
    image_input_size: int = 224
    image_top_k: int = 3
    # Dưới ngưỡng này thì giao diện phải yêu cầu người dùng xác nhận/chọn lại (§5.1)
    image_confidence_threshold: float = 0.55

    # --- Ollama / Qwen ---
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:0.8b"
    ollama_timeout_s: float = 120.0
    ollama_num_ctx: int = 4096
    ollama_num_predict: int = 400
    ollama_think: bool = False  # qwen3.5 là model "thinking": tắt để tránh nuốt hết token
    assistant_max_context_chars: int = 6000

    @field_validator("secret_key")
    @classmethod
    def _secret(cls, v: str) -> str:
        return v.strip()

    @property
    def resolved_database_url(self) -> str:
        """SQLite mặc định nằm trong data/nutrition.db."""
        if self.database_url:
            return self.database_url
        db_path = (BASE_DIR / "data" / "nutrition.db").as_posix()
        return f"sqlite+pysqlite:///{db_path}"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_secret_key(self) -> str:
        """Nếu chưa cấu hình SECRET_KEY: sinh khóa tạm cho phiên chạy này.

        Cảnh báo rõ ràng - phiên đăng nhập sẽ mất hiệu lực khi khởi động lại.
        """
        if not self.secret_key:
            import logging

            self.secret_key = secrets.token_urlsafe(48)
            logging.getLogger(__name__).warning(
                "SECRET_KEY chưa được cấu hình trong .env - đang dùng khóa tạm thời. "
                "Phiên đăng nhập sẽ hết hiệu lực sau khi khởi động lại."
            )
        return self.secret_key

    def ensure_dirs(self) -> None:
        for d in (
            BASE_DIR / "data",
            BASE_DIR / "data" / "raw",
            BASE_DIR / "data" / "processed",
            BASE_DIR / "data" / "external",
            BASE_DIR / "data" / "reports",
            self.backup_dir,
            self.upload_dir,
            self.image_model_dir,
            self.regression_model_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_secret_key()
    return s


settings = get_settings()
