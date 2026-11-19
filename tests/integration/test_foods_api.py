"""Kiểm thử tích hợp API thực phẩm: tra cứu, tạo mới, tính khẩu phần."""
from __future__ import annotations

import importlib.util
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

PHO = {
    "name_vi": "Phở bò",
    "name_en": "Beef pho",
    "category": "Món nước",
    "cooking_state": "cooked",
    "energy_kcal_per_100g": 95.0,
    "protein_g_per_100g": 6.5,
    "fat_g_per_100g": 1.8,
    "carbohydrate_g_per_100g": 12.4,
    "fiber_g_per_100g": 0.5,
    "source_name": "Nhập tay theo bảng thành phần dinh dưỡng Việt Nam",
    "source_note": "Bản ghi kiểm thử",
    "aliases": ["pho bo", "Phở"],
}


@pytest.fixture()
def api():
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
    client = TestClient(app, follow_redirects=False)
    try:
        yield client, SessionLocal
    finally:
        app.dependency_overrides.clear()


def _login(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "tester@example.com", "password": "Matkhau123"},
    )


class TestPublicLookup:
    def test_danh_sach_rong_ban_dau(self, api):
        client, _ = api
        r = client.get("/api/v1/foods")
        assert r.status_code == 200
        assert r.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}

    def test_khong_tim_thay_thuc_pham(self, api):
        client, _ = api
        assert client.get("/api/v1/foods/9999").status_code == 404

    def test_khoi_tao_duoc_khi_chua_co_du_lieu(self, api):
        client, _ = api
        r = client.get("/api/v1/foods/filters")
        assert r.status_code == 200
        assert r.json()["cooking_states"] == ["raw", "cooked", "processed", "unknown"]


class TestCreateFood:
    def test_tao_thuc_pham_can_dang_nhap(self, api):
        client, _ = api
        assert client.post("/api/v1/foods", json=PHO).status_code == 401

    def test_tao_thanh_cong_va_du_lieu_truy_vet(self, api):
        client, _ = api
        _login(client)
        r = client.post("/api/v1/foods", json=PHO)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name_vi"] == "Phở bò"
        assert body["cooking_state"] == "cooked"
        assert body["energy_kcal_per_100g"] == pytest.approx(95.0)  # đồng bộ từ food_nutrients
        assert body["source_code"] == "manual"

    def test_thieu_ten_bi_tu_choi(self, api):
        client, _ = api
        _login(client)
        payload = dict(PHO)
        payload.pop("name_vi")
        payload.pop("name_en")
        r = client.post("/api/v1/foods", json=payload)
        assert r.status_code == 400

    def test_thieu_nguon_du_lieu_bi_tu_choi(self, api):
        """§6: mọi bản ghi phải ghi rõ nguồn."""
        client, _ = api
        _login(client)
        payload = dict(PHO)
        payload.pop("source_name")
        r = client.post("/api/v1/foods", json=payload)
        assert r.status_code == 400
        assert "nguồn" in r.json()["detail"]

    def test_gia_tri_phi_ly_bi_tu_choi(self, api):
        client, _ = api
        _login(client)
        payload = dict(PHO)
        payload["energy_kcal_per_100g"] = 5000
        assert client.post("/api/v1/foods", json=payload).status_code == 422

    def test_trang_thai_che_bien_sai_bi_tu_choi(self, api):
        client, _ = api
        _login(client)
        payload = dict(PHO)
        payload["cooking_state"] = "chua_nau"
        assert client.post("/api/v1/foods", json=payload).status_code == 422


class TestSearchAndDetail:
    @pytest.fixture()
    def food_id(self, api) -> int:
        client, _ = api
        _login(client)
        return client.post("/api/v1/foods", json=PHO).json()["id"]

    def test_tim_khong_dau(self, api, food_id):
        client, _ = api
        r = client.get("/api/v1/foods", params={"q": "pho bo"})
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["id"] == food_id

    def test_tim_bang_alias(self, api, food_id):
        client, _ = api
        assert client.get("/api/v1/foods", params={"q": "Phở"}).json()["total"] == 1

    def test_loc_theo_trang_thai(self, api, food_id):
        client, _ = api
        assert client.get("/api/v1/foods", params={"cooking_state": "cooked"}).json()["total"] == 1
        assert client.get("/api/v1/foods", params={"cooking_state": "raw"}).json()["total"] == 0

    def test_chi_tiet_co_nguon_va_chat_dinh_duong(self, api, food_id):
        client, _ = api
        r = client.get(f"/api/v1/foods/{food_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["source_name"] is not None
        codes = {n["code"] for n in body["nutrients"]}
        assert {"energy_kcal", "protein_g", "carbohydrate_g"} <= codes
        # chất không nhập thì KHÔNG xuất hiện với giá trị 0
        assert all(n["amount_per_100g"] != 0 for n in body["nutrients"])


class TestPortion:
    @pytest.fixture()
    def food_id(self, api) -> int:
        client, _ = api
        _login(client)
        return client.post("/api/v1/foods", json=PHO).json()["id"]

    def test_cong_thuc_khau_phan_100g(self, api, food_id):
        client, _ = api
        body = client.get(f"/api/v1/foods/{food_id}/portion", params={"weight_g": 100}).json()
        assert body["kcal"] == pytest.approx(95.0)
        assert body["kcal_source"] == "measured"
        by_code = {v["code"]: v for v in body["values"]}
        assert by_code["protein_g"]["total"] == pytest.approx(6.5)

    def test_cong_thuc_khau_phan_250g(self, api, food_id):
        client, _ = api
        body = client.get(f"/api/v1/foods/{food_id}/portion", params={"weight_g": 250}).json()
        assert body["kcal"] == pytest.approx(237.5)  # 95 * 250 / 100
        by_code = {v["code"]: v for v in body["values"]}
        assert by_code["carbohydrate_g"]["total"] == pytest.approx(31.0)
        assert body["total_weight_grams"] == pytest.approx(250.0)

    def test_nhieu_phan(self, api, food_id):
        client, _ = api
        body = client.get(f"/api/v1/foods/{food_id}/portion", params={"weight_g": 150, "quantity": 2}).json()
        assert body["kcal"] == pytest.approx(285.0)  # 95 * 300 / 100
        assert body["total_weight_grams"] == pytest.approx(300.0)

    def test_bao_ro_chat_thieu_du_lieu(self, api, food_id):
        client, _ = api
        body = client.get(f"/api/v1/foods/{food_id}/portion", params={"weight_g": 100}).json()
        # bản ghi này không có đường và natri -> phải được báo là thiếu, không hiển thị 0
        assert "sugar_g" in body["missing_nutrients"]
        assert "sodium_mg" in body["missing_nutrients"]
        assert "energy_kcal" not in body["missing_nutrients"]

    def test_khoi_luong_khong_hop_le(self, api, food_id):
        client, _ = api
        assert client.get(f"/api/v1/foods/{food_id}/portion", params={"weight_g": 0}).status_code == 422
        assert client.get(f"/api/v1/foods/{food_id}/portion", params={"weight_g": -10}).status_code == 422

    def test_thuc_pham_khong_ton_tai(self, api):
        client, _ = api
        assert client.get("/api/v1/foods/4242/portion", params={"weight_g": 100}).status_code == 404

    def test_phan_bo_nang_luong_4_4_9(self, api, food_id):
        client, _ = api
        body = client.get(f"/api/v1/foods/{food_id}/portion", params={"weight_g": 100}).json()
        split = body["macro_energy_split"]
        assert split["protein_kcal"] == pytest.approx(26.0)
        assert split["fat_kcal"] == pytest.approx(16.2)
        assert split["carbohydrate_kcal"] == pytest.approx(49.6)
