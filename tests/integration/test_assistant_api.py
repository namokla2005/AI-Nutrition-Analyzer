"""Kiểm thử trợ lý AI: dựng ngữ cảnh, grounding, phiên, quyền sở hữu, trường hợp Ollama lỗi.

Model được thay bằng client giả để bài kiểm thử chạy nhanh và tất định.
Việc gọi Qwen THẬT được kiểm tra riêng ở tests/integration/test_assistant_ollama_live.py
(chạy khi đặt biến môi trường ANA_LIVE_OLLAMA=1).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.assistant_service as assistant_service
from app.core.database import get_db
from app.integrations.ollama_client import ChatResult, OllamaUnavailable
from app.main import app
from app.models import Base, ChatMessage, ChatSession, FoodSource, Nutrient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = PROJECT_ROOT / "scripts" / "seed_reference_data.py"

RICE = {
    "name_vi": "Cơm trắng chín",
    "cooking_state": "cooked",
    "energy_kcal_per_100g": 130.0,
    "protein_g_per_100g": 2.7,
    "fat_g_per_100g": 0.3,
    "carbohydrate_g_per_100g": 28.2,
    "fiber_g_per_100g": 0.4,
    "source_name": "Dữ liệu kiểm thử",
}


class FakeOllama:
    """Client giả: ghi lại messages đã gửi để kiểm tra ngữ cảnh."""

    def __init__(self, content: str = "Hôm nay bạn đã ăn 260 kcal.") -> None:
        self.content = content
        self.calls: list[list[dict]] = []

    def chat(self, messages, **kwargs) -> ChatResult:
        self.calls.append(messages)
        return ChatResult(content=self.content, model="fake-qwen", tokens_out=42, latency_ms=7)

    @property
    def last_system_prompt(self) -> str:
        return self.calls[-1][0]["content"]

    @property
    def last_messages(self) -> list[dict]:
        return self.calls[-1]


class DeadOllama:
    def chat(self, messages, **kwargs):
        raise OllamaUnavailable("Trợ lý AI đang không khả dụng (không gọi được Ollama).")


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)

    spec = importlib.util.spec_from_file_location("_seed_ref", SEED_SCRIPT)
    seed = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(seed)
    with SessionLocal() as db:
        for code, vi, en, unit, is_energy in seed.NUTRIENTS:
            db.add(Nutrient(code=code, name_vi=vi, name_en=en, unit=unit, is_energy=is_energy))
        for code, name, kind, url, lic, lic_url, note in seed.SOURCES:
            db.add(FoodSource(code=code, name=name, kind=kind, url=url, license=lic,
                              license_url=lic_url, note=note))
        db.commit()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    fake = FakeOllama()
    monkeypatch.setattr(assistant_service, "get_ollama_client", lambda: fake)

    def new_client() -> TestClient:
        return TestClient(app, follow_redirects=False)

    try:
        yield new_client, SessionLocal, fake
    finally:
        app.dependency_overrides.clear()


def _register(client: TestClient, email: str = "a@example.com") -> None:
    assert client.post("/api/v1/auth/register",
                       json={"email": email, "password": "Matkhau123"}).status_code == 201


def _seed_meal(client: TestClient) -> None:
    food = client.post("/api/v1/foods", json=RICE).json()
    r = client.post("/api/v1/meals", json={
        "meal_type": "lunch",
        "items": [{"food_id": food["id"], "weight_grams": 200}],
    })
    assert r.status_code == 201


class TestAssistantChat:
    def test_can_dang_nhap(self, api):
        new_client, _, _ = api
        assert new_client().post("/api/v1/assistant/chat", json={"message": "hi"}).status_code == 401

    def test_tra_loi_va_luu_lich_su(self, api):
        new_client, SessionLocal, _ = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/assistant/chat", json={"message": "Bữa ăn của tôi có bao nhiêu calo?"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["answer"] == "Hôm nay bạn đã ăn 260 kcal."
        assert body["model"] == "fake-qwen"
        assert body["session_id"] > 0
        assert body["grounded"] is True

        with SessionLocal() as db:
            messages = db.query(ChatMessage).order_by(ChatMessage.id).all()
            assert [m.role for m in messages] == ["user", "assistant"]
            assert messages[1].context_used is not None
            assert messages[1].model_name == "fake-qwen"
            assert messages[1].tokens_out == 42

    def test_ngu_canh_chua_so_lieu_that_trong_ngay(self, api):
        new_client, _, fake = api
        c = new_client()
        _register(c)
        _seed_meal(c)
        r = c.post("/api/v1/assistant/chat", json={"message": "Hôm nay tôi ăn bao nhiêu calo?"})
        assert r.status_code == 200
        # 130 kcal/100 g × 200 g = 260 kcal phải có trong ngữ cảnh gửi cho model
        assert "260" in fake.last_system_prompt
        assert "DỮ LIỆU" in fake.last_system_prompt
        assert r.json()["context_used"]["today_totals"]["energy_kcal"] == pytest.approx(260.0)

    def test_grounding_va_cau_hoi_nam_cuoi(self, api):
        new_client, _, fake = api
        c = new_client()
        _register(c)
        c.post("/api/v1/assistant/chat", json={"message": "Giải thích thành phần dinh dưỡng."})
        system = fake.last_messages[0]
        last = fake.last_messages[-1]
        assert system["role"] == "system"
        assert "CHỈ trả lời dựa trên" in system["content"]
        assert "không bịa số" in system["content"]
        assert "SQL" in system["content"]  # có quy tắc cấm nhắc tới SQL
        assert last == {"role": "user", "content": "Giải thích thành phần dinh dưỡng."}

    def test_thieu_du_lieu_phai_duoc_bao_trong_ngu_canh(self, api):
        new_client, _, fake = api
        c = new_client()
        _register(c)
        _seed_meal(c)
        c.post("/api/v1/assistant/chat", json={"message": "Bữa ăn có bao nhiêu đường?"})
        prompt = fake.last_system_prompt
        # món cơm không nhập đường và natri -> phải nói rõ là chưa có dữ liệu
        assert "chưa có dữ liệu" in prompt
        assert "sugar_g" in prompt or "đường" in prompt

    def test_tim_thay_mon_duoc_nhac_trong_cau_hoi(self, api):
        new_client, _, fake = api
        c = new_client()
        _register(c)
        c.post("/api/v1/foods", json=RICE)
        r = c.post("/api/v1/assistant/chat", json={"message": "Cơm trắng chín bao nhiêu calo?"})
        assert r.status_code == 200
        mentioned = r.json()["context_used"]["foods_mentioned"]
        assert mentioned, "phải tìm được món được nhắc tới trong câu hỏi"
        assert mentioned[0]["name"] == "Cơm trắng chín"
        assert mentioned[0]["per_100g"]["energy_kcal"] == pytest.approx(130.0)
        assert "Cơm trắng chín" in fake.last_system_prompt

    def test_tim_duoc_mon_khi_hoi_khong_dau(self, api):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        c.post("/api/v1/foods", json=RICE)
        body = c.post("/api/v1/assistant/chat", json={"message": "com trang chin co bao nhieu calo"}).json()
        assert body["context_used"]["foods_mentioned"][0]["name"] == "Cơm trắng chín"

    def test_ngu_canh_bi_gioi_han_do_dai(self, api, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "assistant_max_context_chars", 400)
        new_client, _, fake = api
        c = new_client()
        _register(c)
        _seed_meal(c)
        c.post("/api/v1/assistant/chat", json={"message": "Tổng hợp dinh dưỡng hôm nay."})
        assert "(Ngữ cảnh được hệ thống cắt bớt" in fake.last_system_prompt


class TestSessionsAndHistory:
    def test_tiep_tuc_phien_cu(self, api):
        new_client, _, fake = api
        c = new_client()
        _register(c)
        first = c.post("/api/v1/assistant/chat", json={"message": "Câu 1"}).json()
        c.post("/api/v1/assistant/chat", json={"message": "Câu 2", "session_id": first["session_id"]})
        # lần gọi thứ hai phải kèm lịch sử của phiên (system + user1 + assistant1 + user2)
        assert len(fake.last_messages) >= 4
        assert {"role": "user", "content": "Câu 1"} in fake.last_messages

    def test_lich_su_tra_ve_dung_phien(self, api):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        sid = c.post("/api/v1/assistant/chat", json={"message": "Xin chào"}).json()["session_id"]
        body = c.get("/api/v1/assistant/history").json()
        assert body["session_id"] == sid
        assert len(body["sessions"]) == 1
        assert body["sessions"][0]["message_count"] == 2
        assert [m["role"] for m in body["messages"]] == ["user", "assistant"]

    def test_khong_doc_duoc_phien_cua_nguoi_khac(self, api):
        new_client, _, _ = api
        a, b = new_client(), new_client()
        _register(a, "a@example.com")
        _register(b, "b@example.com")
        sid = a.post("/api/v1/assistant/chat", json={"message": "Bí mật của A"}).json()["session_id"]
        assert b.get("/api/v1/assistant/history", params={"session_id": sid}).status_code == 404
        assert b.post("/api/v1/assistant/chat",
                      json={"message": "x", "session_id": sid}).status_code == 404
        # B không thấy phiên nào của A
        assert b.get("/api/v1/assistant/history").json()["sessions"] == []


class TestOllamaFailure:
    def test_ollama_khong_chay_tra_503(self, api, monkeypatch):
        new_client, SessionLocal, _ = api
        monkeypatch.setattr(assistant_service, "get_ollama_client", lambda: DeadOllama())
        c = new_client()
        _register(c)
        r = c.post("/api/v1/assistant/chat", json={"message": "Hôm nay tôi ăn gì?"})
        assert r.status_code == 503
        assert "không khả dụng" in r.json()["detail"]
        # lỗi phải được ghi lại, không im lặng
        with SessionLocal() as db:
            rows = db.query(ChatMessage).filter(ChatMessage.role == "assistant").all()
            assert rows and rows[0].error

    def test_cac_chuc_nang_khac_van_hoat_dong_khi_ollama_chet(self, api, monkeypatch):
        """§9: Ollama không chạy thì nhận diện/tra cứu/tính dinh dưỡng vẫn phải chạy."""
        new_client, _, _ = api
        monkeypatch.setattr(assistant_service, "get_ollama_client", lambda: DeadOllama())
        c = new_client()
        _register(c)
        food = c.post("/api/v1/foods", json=RICE).json()
        assert c.get("/api/v1/foods", params={"q": "com trang"}).status_code == 200
        r = c.get(f"/api/v1/foods/{food['id']}/portion", params={"weight_g": 150})
        assert r.status_code == 200
        assert r.json()["kcal"] == pytest.approx(195.0)
        assert c.post("/api/v1/assistant/chat", json={"message": "x"}).status_code == 503

    def test_model_tra_ve_rong_thi_bao_ro(self, api, monkeypatch):
        new_client, _, _ = api

        class EmptyOllama:
            def chat(self, messages, **kwargs):
                return ChatResult(content="", model="fake", thinking="suy nghĩ dài",
                                  tokens_out=400, latency_ms=900,
                                  raw={"note": "Model không sinh ra nội dung trả lời (có thể đã dùng hết token cho phần suy luận)."})

        monkeypatch.setattr(assistant_service, "get_ollama_client", lambda: EmptyOllama())
        c = new_client()
        _register(c)
        body = c.post("/api/v1/assistant/chat", json={"message": "câu hỏi"}).json()
        assert body["answer"]  # không trả chuỗi rỗng
        assert body["notice"] is not None

    def test_trang_thai_tro_ly(self, api):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        body = c.get("/api/v1/assistant/status").json()
        assert body["model"] == "qwen3.5:0.8b"
        assert "không tạo số liệu" in body["grounded_policy"]
        assert body["context_budget_chars"] > 0
        assert "available" in body["ollama"]
