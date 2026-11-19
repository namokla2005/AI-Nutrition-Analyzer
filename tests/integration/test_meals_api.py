"""Kiểm thử tích hợp nhật ký ăn uống + thống kê (DB tạm, HTTP thật qua TestClient)."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, FoodNutrient, FoodSource, Nutrient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = PROJECT_ROOT / "scripts" / "seed_reference_data.py"

# Cơm trắng chín: 130 kcal/100 g
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


@pytest.fixture()
def api():
    """Trả về (hàm tạo client mới, SessionLocal). Mỗi client có cookie riêng."""
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

    def new_client() -> TestClient:
        return TestClient(app, follow_redirects=False)

    try:
        yield new_client, SessionLocal
    finally:
        app.dependency_overrides.clear()


def _register(client: TestClient, email: str) -> None:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "Matkhau123"})
    assert r.status_code == 201, r.text


def _make_food(client: TestClient, payload: dict | None = None) -> int:
    r = client.post("/api/v1/foods", json=payload or RICE)
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestCreateMeal:
    def test_can_dang_nhap(self, api):
        new_client, _ = api
        c = new_client()
        r = c.post("/api/v1/meals", json={"meal_type": "lunch", "items": [{"food_id": 1, "weight_grams": 100}]})
        assert r.status_code == 401

    def test_them_bua_an_va_tinh_tong(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        r = c.post(
            "/api/v1/meals",
            json={"meal_type": "lunch", "items": [{"food_id": food_id, "weight_grams": 200}]},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        # 130 kcal/100 g × 200 g / 100 = 260 kcal
        assert body["totals"]["totals"]["energy_kcal"] == pytest.approx(260.0)
        assert body["totals"]["totals"]["protein_g"] == pytest.approx(5.4)
        assert body["items"][0]["kcal_source"] == "measured"
        assert body["items"][0]["food_name"] == "Cơm trắng chín"
        assert body["meal_type"] == "lunch"

    def test_nhieu_mon_trong_mot_bua(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")

        # món 1: có năng lượng
        r = c.post("/api/v1/foods", json={**RICE, "name_vi": "Món có năng lượng",
                                          "energy_kcal_per_100g": 100.0})
        f1 = r.json()["id"]
        # món 2: KHÔNG có năng lượng (để kiểm tra xử lý thiếu dữ liệu)
        payload = {k: v for k, v in RICE.items() if k != "energy_kcal_per_100g"}
        payload["name_vi"] = "Món thiếu năng lượng"
        payload["protein_g_per_100g"] = None
        r = c.post("/api/v1/foods", json=payload)
        f2 = r.json()["id"]

        r = c.post("/api/v1/meals", json={"meal_type": "dinner", "items": [
            {"food_id": f1, "weight_grams": 100},
            {"food_id": f2, "weight_grams": 100},
        ]})
        body = r.json()
        assert body["totals"]["item_count"] == 2
        assert body["totals"]["items_without_energy"] == 1
        assert "energy_kcal" in body["totals"]["missing_fields"]
        assert body["items"][1]["kcal"] is None  # thiếu dữ liệu -> None, không phải 0

    def test_thuc_pham_khong_ton_tai(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        r = c.post("/api/v1/meals", json={"meal_type": "lunch", "items": [{"food_id": 999, "weight_grams": 100}]})
        # 404 (không tìm thấy) chứ không phải 400 — thống nhất với các endpoint khác
        assert r.status_code == 404
        assert "Không tìm thấy thực phẩm" in r.json()["detail"]

    def test_danh_sach_mon_rong_bi_tu_choi(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        r = c.post("/api/v1/meals", json={"meal_type": "lunch", "items": []})
        assert r.status_code == 422

    def test_loai_bua_an_sai(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        r = c.post("/api/v1/meals", json={"meal_type": "brunch",
                                          "items": [{"food_id": food_id, "weight_grams": 100}]})
        assert r.status_code == 422

    def test_snapshot_khong_doi_khi_du_lieu_nguon_thay_doi(self, api):
        """§7.4: sửa giá trị dinh dưỡng của thực phẩm KHÔNG được làm đổi lịch sử đã ghi."""
        new_client, SessionLocal = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        r = c.post("/api/v1/meals", json={"meal_type": "lunch",
                                          "items": [{"food_id": food_id, "weight_grams": 100}]})
        before = r.json()["totals"]["totals"]["energy_kcal"]
        assert before == pytest.approx(130.0)

        # đổi năng lượng của thực phẩm trong DB thành 500 kcal
        with SessionLocal() as db:
            nutrient = db.query(Nutrient).filter(Nutrient.code == "energy_kcal").one()
            row = db.query(FoodNutrient).filter(
                FoodNutrient.food_id == food_id, FoodNutrient.nutrient_id == nutrient.id
            ).one()
            row.amount_per_100g = 500.0
            db.commit()

        after = c.get("/api/v1/meals").json()["items"][0]["totals"]["totals"]["energy_kcal"]
        assert after == pytest.approx(130.0), "lịch sử phải giữ nguyên theo snapshot"


class TestOwnership:
    def test_khong_xem_duoc_bua_an_cua_nguoi_khac(self, api):
        new_client, _ = api
        a, b = new_client(), new_client()
        _register(a, "a@example.com")
        _register(b, "b@example.com")
        food_id = _make_food(a)
        meal_id = a.post("/api/v1/meals", json={"meal_type": "lunch",
                                                "items": [{"food_id": food_id, "weight_grams": 100}]}).json()["id"]

        assert b.get(f"/api/v1/meals/{meal_id}").status_code == 404
        assert b.get("/api/v1/meals").json()["total"] == 0
        assert b.put(f"/api/v1/meals/{meal_id}", json={"note": "sửa trộm"}).status_code == 404
        assert b.delete(f"/api/v1/meals/{meal_id}").status_code == 404
        # chủ sở hữu vẫn xem được
        assert a.get(f"/api/v1/meals/{meal_id}").status_code == 200


class TestUpdateDelete:
    def test_sua_bua_an(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        meal_id = c.post("/api/v1/meals", json={"meal_type": "lunch",
                                                "items": [{"food_id": food_id, "weight_grams": 100}]}).json()["id"]
        r = c.put(f"/api/v1/meals/{meal_id}", json={
            "meal_type": "dinner", "note": "đổi sang bữa tối",
            "items": [{"food_id": food_id, "weight_grams": 300}],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["meal_type"] == "dinner"
        assert body["note"] == "đổi sang bữa tối"
        assert len(body["items"]) == 1
        assert body["totals"]["totals"]["energy_kcal"] == pytest.approx(390.0)  # 130 × 300/100

    def test_xoa_bua_an(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        meal_id = c.post("/api/v1/meals", json={"meal_type": "snack",
                                                "items": [{"food_id": food_id, "weight_grams": 50}]}).json()["id"]
        assert c.delete(f"/api/v1/meals/{meal_id}").status_code == 204
        assert c.get(f"/api/v1/meals/{meal_id}").status_code == 404
        assert c.get("/api/v1/meals").json()["total"] == 0

    def test_loc_theo_ngay_va_loai_bua(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        c.post("/api/v1/meals", json={"meal_type": "breakfast", "eaten_at": "2026-11-18T01:00:00",
                                      "items": [{"food_id": food_id, "weight_grams": 100}]})
        c.post("/api/v1/meals", json={"meal_type": "lunch", "eaten_at": "2026-11-18T05:00:00",
                                      "items": [{"food_id": food_id, "weight_grams": 100}]})

        assert c.get("/api/v1/meals", params={"meal_type": "breakfast"}).json()["total"] == 1
        assert c.get("/api/v1/meals", params={"date_from": "2026-11-18", "date_to": "2026-11-18"}).json()["total"] == 2
        assert c.get("/api/v1/meals", params={"date_from": "2026-11-19"}).json()["total"] == 0


class TestStatistics:
    def test_thong_ke_ngay_va_muc_tieu(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        c.put("/api/v1/users/me", json={"profile": {"daily_kcal_target": 2000}})
        c.post("/api/v1/meals", json={"meal_type": "lunch", "eaten_at": "2026-11-18T05:00:00",
                                      "items": [{"food_id": food_id, "weight_grams": 1000}]})

        r = c.get("/api/v1/statistics/daily", params={"day": "2026-11-18"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["totals"]["totals"]["energy_kcal"] == pytest.approx(1300.0)  # 130 × 1000/100
        assert body["target"]["percent"] == pytest.approx(65.0)
        assert body["target"]["remaining_kcal"] == pytest.approx(700.0)
        assert [b["meal_type"] for b in body["by_meal_type"]] == ["lunch"]

    def test_ngay_trong(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        body = c.get("/api/v1/statistics/daily", params={"day": "2026-01-01"}).json()
        assert body["totals"]["totals"]["energy_kcal"] is None  # không có dữ liệu -> None, không phải 0
        assert body["totals"]["item_count"] == 0
        assert body["by_meal_type"] == []

    def test_bien_gio_utc_sang_ngay_dia_phuong(self, api):
        """18:00 UTC ngày 18 = 01:00 ngày 19 giờ Việt Nam -> phải tính vào ngày 19."""
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        c.post("/api/v1/meals", json={"meal_type": "snack", "eaten_at": "2026-11-18T18:00:00",
                                      "items": [{"food_id": food_id, "weight_grams": 100}]})
        assert c.get("/api/v1/statistics/daily", params={"day": "2026-11-19"}).json()["totals"]["item_count"] == 1
        assert c.get("/api/v1/statistics/daily", params={"day": "2026-11-18"}).json()["totals"]["item_count"] == 0

    def test_thong_ke_tuan_co_7_ngay(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        c.post("/api/v1/meals", json={"meal_type": "lunch", "eaten_at": "2026-11-18T05:00:00",
                                      "items": [{"food_id": food_id, "weight_grams": 100}]})
        r = c.get("/api/v1/statistics/weekly", params={"any_day": "2026-11-18"})
        body = r.json()
        assert body["period"] == "weekly"
        assert len(body["series"]) == 7
        assert body["start_date"] == "2026-11-16"  # Thứ Hai
        assert body["end_date"] == "2026-11-22"    # Chủ Nhật
        assert body["days_with_data"] == 1
        idx = [p["date_local"] for p in body["series"]].index("2026-11-18")
        assert body["series"][idx]["kcal"] == pytest.approx(130.0)
        assert body["series"][0]["kcal"] is None  # ngày không có dữ liệu -> None

    def test_thong_ke_thang(self, api):
        new_client, _ = api
        c = new_client()
        _register(c, "a@example.com")
        food_id = _make_food(c)
        c.post("/api/v1/meals", json={"meal_type": "lunch", "eaten_at": "2026-11-18T05:00:00",
                                      "items": [{"food_id": food_id, "weight_grams": 200}]})
        body = c.get("/api/v1/statistics/monthly", params={"year": 2026, "month": 11}).json()
        assert len(body["series"]) == 30  # tháng 11 có 30 ngày
        assert body["totals"]["totals"]["energy_kcal"] == pytest.approx(260.0)
        assert body["days_with_data"] == 1

    def test_thong_ke_chi_tinh_du_lieu_cua_minh(self, api):
        new_client, _ = api
        a, b = new_client(), new_client()
        _register(a, "a@example.com")
        _register(b, "b@example.com")
        food_id = _make_food(a)
        a.post("/api/v1/meals", json={"meal_type": "lunch", "eaten_at": "2026-11-18T05:00:00",
                                      "items": [{"food_id": food_id, "weight_grams": 500}]})
        body = b.get("/api/v1/statistics/daily", params={"day": "2026-11-18"}).json()
        assert body["totals"]["item_count"] == 0
