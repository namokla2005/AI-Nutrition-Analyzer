"""Kiểm thử các trang giao diện: chặn truy cập khi chưa đăng nhập, hiển thị trang, điều hướng."""
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

PROTECTED_PAGES = ["/dashboard", "/recognize", "/foods", "/diary", "/statistics", "/assistant", "/profile"]


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

    def new_client() -> TestClient:
        return TestClient(app, follow_redirects=False)

    try:
        yield new_client
    finally:
        app.dependency_overrides.clear()


class TestPublicPages:
    def test_root_chuyen_huong_ve_login_khi_chua_dang_nhap(self, api):
        c = api()
        r = c.get("/")
        assert r.status_code == 303
        assert r.headers["location"] == "/login"

    def test_trang_login_hien_thi_duoc(self, api):
        c = api()
        r = c.get("/login")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "Đăng nhập" in r.text
        assert 'id="login-form"' in r.text
        # trang đăng nhập dùng lớp gọi API dùng chung
        assert "/static/js/api.js" in r.text

    def test_trang_register_hien_thi_duoc(self, api):
        c = api()
        r = c.get("/register")
        assert r.status_code == 200
        assert "Tạo tài khoản" in r.text
        assert "8 ký tự" in r.text

    def test_trang_trang_thai_van_hoat_dong(self, api):
        c = api()
        r = c.get("/status")
        assert r.status_code == 200
        assert "AI Nutrition Analyzer" in r.text


class TestAuthGuard:
    @pytest.mark.parametrize("path", PROTECTED_PAGES)
    def test_chua_dang_nhap_thi_chuyen_ve_login(self, api, path):
        c = api()
        r = c.get(path)
        assert r.status_code == 303
        assert r.headers["location"] == f"/login?next={path}"

    @pytest.mark.parametrize("path", PROTECTED_PAGES)
    def test_da_dang_nhap_thi_vao_duoc(self, api, path):
        c = api()
        assert c.post("/api/v1/auth/register",
                      json={"email": "ui@example.com", "password": "Matkhau123"}).status_code == 201
        r = c.get(path)
        assert r.status_code == 200, r.text
        assert "text/html" in r.headers["content-type"]
        # mọi trang đều có sidebar điều hướng và tên người dùng
        assert 'data-nav="dashboard"' in r.text
        assert "ui@example.com" in r.text or "Đăng xuất" in r.text

    def test_da_dang_nhap_thi_login_chuyen_ve_dashboard(self, api):
        c = api()
        c.post("/api/v1/auth/register", json={"email": "ui2@example.com", "password": "Matkhau123"})
        r = c.get("/login")
        assert r.status_code == 303
        assert r.headers["location"] == "/dashboard"

    def test_moi_trang_deu_co_ten_trang_rieng(self, api):
        c = api()
        c.post("/api/v1/auth/register", json={"email": "ui3@example.com", "password": "Matkhau123"})
        titles = set()
        for path in PROTECTED_PAGES:
            text = c.get(path).text
            assert "<title>" in text
            titles.add(text.split("<title>")[1].split("</title>")[0])
        assert len(titles) == len(PROTECTED_PAGES)  # không trang nào trùng tiêu đề


class TestStaticAssets:
    def test_css_va_js_phuc_vu_duoc(self, api):
        c = api()
        css = c.get("/static/css/app.css")
        assert css.status_code == 200
        assert ".sidebar" in css.text
        js = c.get("/static/js/api.js")
        assert js.status_code == 200
        assert "window.ANA" in js.text
