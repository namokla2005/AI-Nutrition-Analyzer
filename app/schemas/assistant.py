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
