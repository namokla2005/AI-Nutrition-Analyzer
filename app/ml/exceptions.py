"""Ngoại lệ của lớp Machine Learning."""
from __future__ import annotations


class ModelUnavailableError(RuntimeError):
    """Chưa có model (chưa huấn luyện hoặc thiếu file) - API phải trả 503 kèm lý do."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class PredictionError(RuntimeError):
    """Suy luận thất bại vì đầu vào không hợp lệ."""
