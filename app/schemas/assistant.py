"""Pydantic schemas cho trợ lý AI."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AssistantChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: int | None = Field(default=None, gt=0, description="Bỏ trống để tạo phiên mới")


class AssistantChatOut(BaseModel):
    session_id: int
    answer: str
    model: str
    latency_ms: int | None = None
    tokens_out: int | None = None
    context_used: dict = Field(default_factory=dict)
    grounded: bool = True
    numbers_verified: bool = Field(
        default=True, description="Mọi con số có đơn vị trong câu trả lời đều khớp dữ liệu thật")
    numbers_checked: int = Field(default=0, description="Số con số có đơn vị đã đối chiếu")
    unsupported_numbers: list[str] = Field(
        default_factory=list, description="Con số không có trong dữ liệu (nếu có)")
    missing_numbers: bool = Field(
        default=False, description="Câu hỏi hỏi số liệu nhưng câu trả lời không nêu con số nào")
    retried: bool = Field(default=False, description="Đã hỏi lại model vì số liệu sai")
    notice: str | None = None


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    model_name: str | None = None
    latency_ms: int | None = None
    created_at: datetime


class ChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatHistoryOut(BaseModel):
    session_id: int | None = None
    sessions: list[ChatSessionOut] = Field(default_factory=list)
    messages: list[ChatMessageOut] = Field(default_factory=list)


class AssistantStatusOut(BaseModel):
    ollama: dict
    model: str
    grounded_policy: str
    context_budget_chars: int
