"""Kiểm thử với Qwen THẬT qua Ollama (chỉ chạy khi bật rõ ràng).

    $env:ANA_LIVE_OLLAMA="1"; .venv\\Scripts\\python.exe -m pytest tests/integration/test_assistant_ollama_live.py -v

Mục đích: chứng minh tích hợp Ollama chạy thật (không phải chỉ client giả), đồng thời
kiểm tra phát hiện quan trọng: qwen3.5:0.8b là model "thinking" nên phải gửi think=false,
nếu không `content` sẽ rỗng vì token bị tiêu hết vào phần suy luận.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, FoodSource, Nutrient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = PROJECT_ROOT / "scripts" / "seed_reference_data.py"

pytestmark = pytest.mark.skipif(
    os.environ.get("ANA_LIVE_OLLAMA") != "1",
    reason="Chỉ chạy khi đặt ANA_LIVE_OLLAMA=1 (cần Ollama thật đang chạy)",
)


@pytest.fixture()
def client():
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
    c = TestClient(app, follow_redirects=False)
    try:
        yield c
    finally:
        app.dependency_overrides.clear()


def test_ollama_that_chay_va_tra_loi_duoc(client: TestClient):
    from app.integrations.ollama_client import get_ollama_client, reset_client

    reset_client()
    status = get_ollama_client().status()
    print("\n[trạng thái Ollama]", status)
    assert status["available"] is True, status["reason"]

    assert client.post("/api/v1/auth/register",
                       json={"email": "live@example.com", "password": "Matkhau123"}).status_code == 201

    food = client.post("/api/v1/foods", json={
        "name_vi": "Cơm trắng chín", "cooking_state": "cooked", "energy_kcal_per_100g": 130.0,
        "protein_g_per_100g": 2.7, "fat_g_per_100g": 0.3, "carbohydrate_g_per_100g": 28.2,
        "source_name": "kiểm thử trực tiếp",
    }).json()
    client.post("/api/v1/meals", json={
        "meal_type": "lunch", "items": [{"food_id": food["id"], "weight_grams": 200}],
    })

    r = client.post("/api/v1/assistant/chat", json={"message": "Hôm nay tôi đã ăn bao nhiêu calo?"})
    assert r.status_code == 200, r.text
    body = r.json()
    print("\n[câu trả lời của Qwen]", body["answer"])
    print("[độ trễ ms]", body["latency_ms"], "| token sinh:", body["tokens_out"])
    print("[ngữ cảnh kcal hôm nay]", body["context_used"]["today_totals"]["energy_kcal"])

    assert body["answer"].strip(), "Qwen phải trả về nội dung (nếu rỗng: kiểm tra think=false)"
    assert body["model"] == "qwen3.5:0.8b"
    assert body["context_used"]["today_totals"]["energy_kcal"] == pytest.approx(260.0)
    # Model 0,8B rất nhỏ: chỉ kiểm tra nó có nhắc tới con số thật trong ngữ cảnh
    assert "260" in body["answer"] or "calo" in body["answer"].lower()
