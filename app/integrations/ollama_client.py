"""Client gọi Ollama (Qwen3.5-0.8B) qua HTTP API nội bộ.

Bài học đo được từ môi trường thật (xem docs/ENVIRONMENT_REPORT.md mục 5):
`qwen3.5:0.8b` là model "thinking" — nếu không tắt, toàn bộ token bị tiêu vào trường
`thinking` và `content` trả về RỖNG. Vì vậy client mặc định gửi `think=false`, và vẫn
giữ lại phần `thinking` để ghi log (không hiển thị cho người dùng).

Nguyên tắc bảo mật (§13): chỉ gọi service nội bộ tại 127.0.0.1, không expose ra Internet,
không để model truy cập file hệ thống hay SQLite.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    content: str
    model: str
    thinking: str = ""
    tokens_out: int | None = None
    latency_ms: int | None = None
    raw: dict = field(default_factory=dict)


class OllamaUnavailable(RuntimeError):
    """Không kết nối được Ollama (chưa chạy hoặc sai địa chỉ)."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None,
                 timeout: float | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout_s

    # ---------- trạng thái ----------

    def list_models(self) -> list[dict[str, Any]]:
        import httpx

        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            r.raise_for_status()
        except Exception as exc:
            raise OllamaUnavailable(
                "Không kết nối được Ollama. Hãy kiểm tra Ollama đã chạy chưa.",
                f"{type(exc).__name__}: {exc}",
            ) from exc
        return list(r.json().get("models") or [])

    def is_available(self) -> bool:
        try:
            models = self.list_models()
        except OllamaUnavailable:
            return False
        names = {m.get("name") or m.get("model") for m in models}
        return self.model in names

    def status(self) -> dict:
        try:
            models = self.list_models()
        except OllamaUnavailable as exc:
            return {"available": False, "base_url": self.base_url, "model": self.model,
                    "reason": exc.message, "models": []}
        names = [m.get("name") for m in models]
        ok = self.model in names
        return {
            "available": ok,
            "base_url": self.base_url,
            "model": self.model,
            "models": names,
            "reason": None if ok else f"Model {self.model} chưa được tải (ollama pull {self.model}).",
        }

    # ---------- hội thoại ----------

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2,
             num_predict: int | None = None, think: bool | None = None) -> ChatResult:
        """Gọi POST /api/chat (không streaming). Ném OllamaUnavailable nếu không gọi được."""
        import httpx

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": settings.ollama_think if think is None else think,
            "options": {
                "temperature": temperature,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": num_predict or settings.ollama_num_predict,
            },
        }
        started = time.perf_counter()
        try:
            r = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            raise OllamaUnavailable(
                "Trợ lý AI đang không khả dụng (không gọi được Ollama).",
                f"{type(exc).__name__}: {exc}",
            ) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        message = data.get("message") or {}
        content = (message.get("content") or "").strip()
        thinking = (message.get("thinking") or "").strip()
        tokens_out = data.get("eval_count")

        if not content:
            # Nếu model đốt hết token vào phần suy luận thì phải nói rõ, không trả chuỗi rỗng
            note = (
                "Model không sinh ra nội dung trả lời (có thể đã dùng hết token cho phần suy luận)."
                if thinking
                else "Model không sinh ra nội dung trả lời."
            )
            logger.warning("Ollama trả về content rỗng (thinking=%d ký tự)", len(thinking))
            return ChatResult(content="", model=self.model, thinking=thinking,
                              tokens_out=tokens_out, latency_ms=latency_ms, raw={"note": note, **data})

        return ChatResult(content=content, model=self.model, thinking=thinking,
                          tokens_out=tokens_out, latency_ms=latency_ms, raw=data)

    def chat_debug(self) -> dict:
        """Gọi thử để chẩn đoán; dùng cho endpoint trạng thái."""
        try:
            result = self.chat(
                [{"role": "user", "content": "Trả lời đúng một từ: OK"}],
                num_predict=16,
            )
        except OllamaUnavailable as exc:
            return {"ok": False, "reason": exc.message, "detail": exc.detail}
        return {
            "ok": bool(result.content),
            "content": result.content[:80],
            "latency_ms": result.latency_ms,
            "tokens_out": result.tokens_out,
        }


_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


def reset_client() -> None:
    """Dùng trong kiểm thử để nạp lại cấu hình."""
    global _client
    _client = None
