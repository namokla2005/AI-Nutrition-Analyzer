"""Kiểm thử tích hợp API xác thực và quản lý tài khoản (chạy trên DB tạm)."""
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
from app.models import Base, FoodSource, Nutrient, User

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = PROJECT_ROOT / "scripts" / "seed_reference_data.py"


def _load_seed_module():
    spec = importlib.util.spec_from_file_location("_seed_ref", SEED_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def api():
    """(client, Session) với database tạm trong bộ nhớ, đã nạp danh mục tham chiếu."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)

    seed = _load_seed_module()
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


GOOD_PASSWORD = "Matkhau123"


def _register(client: TestClient, email: str = "nam@example.com", password: str = GOOD_PASSWORD):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Nam Phạm"},
    )


class TestRegister:
    def test_dang_ky_thanh_cong(self, api):
        client, _ = api
        r = _register(client)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == "nam@example.com"
        assert body["full_name"] == "Nam Phạm"
        assert "password" not in r.text and "hash" not in r.text

    def test_dang_ky_tu_dong_dang_nhap(self, api):
        client, _ = api
        _register(client)
        assert client.cookies.get("ana_session") is not None
        assert client.get("/api/v1/users/me").status_code == 200

    def test_email_trung_tra_ve_409(self, api):
        client, _ = api
        _register(client)
        r = _register(client, email="nam@example.com")
        assert r.status_code == 409
        assert "đã được đăng ký" in r.json()["detail"]

    def test_email_khong_phan_biet_chu_hoa_thuong(self, api):
        client, _ = api
        _register(client, email="Nam@Example.com")
        r = _register(client, email="nam@example.com")
        assert r.status_code == 409

    def test_mat_khau_yeu_bi_tu_choi(self, api):
        client, _ = api
        for bad in ["1234567", "abcdefgh", "12345678"]:
            r = _register(client, email=f"x{len(bad)}@example.com", password=bad)
            assert r.status_code == 422, f"mật khẩu {bad!r} lẽ ra phải bị từ chối"

    def test_email_sai_dinh_dang_bi_tu_choi(self, api):
        client, _ = api
        r = _register(client, email="khong-phai-email")
        assert r.status_code == 422

    def test_mat_khau_khong_bi_luu_dang_tho(self, api):
        client, SessionLocal = api
        _register(client)
        with SessionLocal() as db:
            user = db.query(User).one()
            assert GOOD_PASSWORD not in user.password_hash
            assert user.password_hash.startswith("$argon2id$")


class TestLogin:
    def test_dang_nhap_dung(self, api):
        client, _ = api
        _register(client)
        client.post("/api/v1/auth/logout")
        r = client.post("/api/v1/auth/login", json={"email": "nam@example.com", "password": GOOD_PASSWORD})
        assert r.status_code == 200, r.text
        assert r.json()["email"] == "nam@example.com"

    def test_dang_nhap_sai_mat_khau(self, api):
        client, _ = api
        _register(client)
        r = client.post("/api/v1/auth/login", json={"email": "nam@example.com", "password": "SaiMatKhau9"})
        assert r.status_code == 401

    def test_dang_nhap_email_khong_ton_tai_cung_thong_bao(self, api):
        client, _ = api
        r = client.post("/api/v1/auth/login", json={"email": "khong@example.com", "password": GOOD_PASSWORD})
        assert r.status_code == 401
        assert r.json()["detail"] == "Email hoặc mật khẩu không đúng."

    def test_cap_nhat_last_login(self, api):
        client, SessionLocal = api
        _register(client)
        client.post("/api/v1/auth/logout")
        client.post("/api/v1/auth/login", json={"email": "nam@example.com", "password": GOOD_PASSWORD})
        with SessionLocal() as db:
            assert db.query(User).one().last_login_at is not None


class TestSession:
    def test_chua_dang_nhap_thi_401(self, api):
        client, _ = api
        r = client.get("/api/v1/users/me")
        assert r.status_code == 401

    def test_dang_xuat_xoa_phien(self, api):
        client, _ = api
        _register(client)
        r = client.post("/api/v1/auth/logout")
        assert r.status_code == 200
        assert client.get("/api/v1/users/me").status_code == 401

    def test_cookie_gia_bi_tu_choi(self, api):
        client, _ = api
        client.cookies.set("ana_session", "token.gia.mao")
        assert client.get("/api/v1/users/me").status_code == 401

    def test_khong_the_xem_du_lieu_nguoi_khac(self, api):
        """§7.8: user_id lấy từ phiên, không nhận từ client."""
        client, SessionLocal = api
        _register(client, email="a@example.com")
        _register(client, email="b@example.com")  # phiên hiện tại là B
        body = client.get("/api/v1/users/me").json()
        assert body["email"] == "b@example.com"
        # thử giả mạo id qua query string cũng không đổi được người dùng trả về
        body2 = client.get("/api/v1/users/me?user_id=1").json()
        assert body2["email"] == "b@example.com"


class TestProfileAndPassword:
    def test_cap_nhat_ho_so(self, api):
        client, _ = api
        _register(client)
        r = client.put(
            "/api/v1/users/me",
            json={
                "full_name": "Phạm Văn Nam",
                "profile": {"gender": "male", "height_cm": 170, "weight_kg": 65,
                            "activity_level": "moderate", "goal": "maintain", "daily_kcal_target": 2100},
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["full_name"] == "Phạm Văn Nam"
        assert body["profile"]["height_cm"] == 170
        assert body["profile"]["daily_kcal_target"] == 2100

    def test_ho_so_sai_gia_tri_bi_tu_choi(self, api):
        client, _ = api
        _register(client)
        r = client.put("/api/v1/users/me", json={"profile": {"height_cm": 500}})
        assert r.status_code == 422

    def test_doi_mat_khau(self, api):
        client, _ = api
        _register(client)
        r = client.put(
            "/api/v1/users/me/password",
            json={"current_password": GOOD_PASSWORD, "new_password": "Matkhaumoi9"},
        )
        assert r.status_code == 200, r.text
        client.post("/api/v1/auth/logout")
        assert client.post("/api/v1/auth/login", json={"email": "nam@example.com", "password": GOOD_PASSWORD}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"email": "nam@example.com", "password": "Matkhaumoi9"}).status_code == 200

    def test_doi_mat_khau_sai_mat_khau_hien_tai(self, api):
        client, _ = api
        _register(client)
        r = client.put(
            "/api/v1/users/me/password",
            json={"current_password": "SaiMatKhau1", "new_password": "Matkhaumoi9"},
        )
        assert r.status_code == 400

    def test_xoa_tai_khoan_can_xac_nhan(self, api):
        client, _ = api
        _register(client)
        r = client.request("DELETE", "/api/v1/users/me", json={"password": GOOD_PASSWORD, "confirm": "xoa"})
        assert r.status_code == 400

    def test_xoa_tai_khoan_xoa_du_lieu_lien_quan(self, api):
        client, SessionLocal = api
        _register(client)
        r = client.request("DELETE", "/api/v1/users/me", json={"password": GOOD_PASSWORD, "confirm": "DELETE"})
        assert r.status_code == 200, r.text
        with SessionLocal() as db:
            assert db.query(User).count() == 0
        assert client.get("/api/v1/users/me").status_code == 401
