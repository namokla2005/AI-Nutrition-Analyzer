"""API trợ lý AI (Qwen qua Ollama)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_user
from app.integrations.ollama_client import get_ollama_client
from app.models import User
from app.schemas.assistant import (
    AssistantChatIn,
    AssistantChatOut,
    AssistantStatusOut,
    ChatHistoryOut,
)
from app.services import assistant_service
from app.services.assistant_service import AssistantError

router = APIRouter(prefix="/assistant", tags=["assistant"])

GROUNDED_POLICY = (
    "Trợ lý chỉ diễn giải dữ liệu dinh dưỡng do backend dựng từ database của chính người "
    "dùng; không tạo số liệu, không truy cập SQLite, không thấy dữ liệu của tài khoản khác."
)


@router.get("/status", response_model=AssistantStatusOut, summary="Trạng thái trợ lý AI")
def assistant_status(user: User = Depends(require_user)) -> dict:
    return {
        "ollama": get_ollama_client().status(),
        "model": settings.ollama_model,
        "grounded_policy": GROUNDED_POLICY,
        "context_budget_chars": settings.assistant_max_context_chars,
    }


@router.post("/chat", response_model=AssistantChatOut, summary="Hỏi trợ lý AI")
def chat(
    payload: AssistantChatIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.integrations.ollama_client import OllamaUnavailable

    try:
        return assistant_service.answer(db, user, payload.message, payload.session_id)
    except AssistantError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=exc.message) from exc
    except OllamaUnavailable as exc:
        # Các chức năng khác (nhận diện, tra cứu, tính dinh dưỡng) vẫn hoạt động bình thường
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        ) from exc


@router.get("/history", response_model=ChatHistoryOut, summary="Lịch sử trò chuyện")
def get_history(
    session_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return assistant_service.history(db, user, session_id, limit)
    except AssistantError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
