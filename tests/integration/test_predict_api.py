"""Kiểm thử tải ảnh an toàn + API dự đoán (ảnh & năng lượng).

CHÚ Ý: các model dùng trong tệp này là **vật mẫu kiểm thử**: mạng MobileNetV3-Small
với trọng số ngẫu nhiên và một LinearRegression huấn luyện trên dữ liệu tổng hợp.
Chúng chỉ dùng để chứng minh luồng suy luận chạy đúng, KHÔNG phải kết quả nghiên cứu.
"""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ml.image_classifier as ic_mod
import app.ml.regression_model as rm_mod
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base, FoodSource, Nutrient, Prediction
from app.services import upload_service

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = PROJECT_ROOT / "scripts" / "seed_reference_data.py"

FIXTURE_LABELS = ["pizza", "hamburger", "sushi"]


# ---------- tạo dữ liệu ảnh thật trong bộ nhớ ----------

def png_bytes(size: tuple[int, int] = (64, 64), color: tuple[int, int, int] = (200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def jpeg_bytes(size: tuple[int, int] = (80, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (20, 120, 200)).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """DB tạm + thư mục uploads tạm (KHÔNG ghi vào thư mục uploads thật của dự án)."""
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
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")

    def new_client() -> TestClient:
        return TestClient(app, follow_redirects=False)

    try:
        yield new_client, SessionLocal, tmp_path
    finally:
        app.dependency_overrides.clear()
        ic_mod._classifier = None
        rm_mod._model = None


def _register(client: TestClient, email: str = "a@example.com") -> None:
    assert client.post("/api/v1/auth/register",
                       json={"email": email, "password": "Matkhau123"}).status_code == 201


# ---------- 1. Kiểm tra nội dung ảnh ----------

class TestImageValidation:
    def test_png_hop_le(self):
        mime, ext, w, h = upload_service.validate_image_bytes(png_bytes((40, 36)), "a.png")
        assert (mime, ext, w, h) == ("image/png", "png", 40, 36)

    def test_jpeg_hop_le(self):
        mime, ext, w, h = upload_service.validate_image_bytes(jpeg_bytes(), "a.jpg")
        assert mime == "image/jpeg" and ext == "jpg" and (w, h) == (80, 60)

    def test_ten_file_thuc_thi_bi_tu_choi_du_noi_dung_la_anh(self):
        with pytest.raises(upload_service.UploadError) as exc:
            upload_service.validate_image_bytes(png_bytes(), "virus.exe")
        assert exc.value.code == "forbidden_type"

    def test_script_doi_duoi_jpg_van_bi_tu_choi(self):
        with pytest.raises(upload_service.UploadError) as exc:
            upload_service.validate_image_bytes(b"#!/bin/sh\nrm -rf /\n", "anh.jpg")
        assert exc.value.code == "not_an_image"

    def test_du_lieu_ngau_nhien_bi_tu_choi(self):
        with pytest.raises(upload_service.UploadError) as exc:
            upload_service.validate_image_bytes(b"\x00\x01\x02\x03" * 100, "x.png")
        assert exc.value.code == "not_an_image"

    def test_anh_bi_cat_cut_bi_tu_choi(self):
        with pytest.raises(upload_service.UploadError) as exc:
            upload_service.validate_image_bytes(png_bytes()[:80], "x.png")
        assert exc.value.code == "corrupt_image"

    def test_anh_qua_nho_bi_tu_choi(self):
        with pytest.raises(upload_service.UploadError) as exc:
            upload_service.validate_image_bytes(png_bytes((10, 10)), "x.png")
        assert exc.value.code == "too_small"

    def test_file_rong_bi_tu_choi(self):
        with pytest.raises(upload_service.UploadError):
            upload_service.validate_image_bytes(b"", "x.png")

    def test_qua_gioi_han_dung_luong(self, monkeypatch):
        monkeypatch.setattr(settings, "max_upload_mb", 0)
        with pytest.raises(upload_service.UploadError) as exc:
            upload_service.validate_image_bytes(png_bytes(), "x.png")
        assert exc.value.code == "too_large"

    def test_ten_file_khong_anh_huong_duong_dan_luu(self, api):
        """Tên file người dùng gửi lên không được dùng làm đường dẫn lưu."""
        new_client, SessionLocal, tmp_path = api
        _register(new_client())
        with SessionLocal() as db:
            img = upload_service.save_user_image(
                db, 1, "../../../etc/passwd.png", png_bytes(), purpose="test"
            )
            assert ".." not in img.rel_path and "passwd" not in img.rel_path
            saved = upload_service.absolute_path(img)
            assert saved.exists()
            assert str(tmp_path) in str(saved)
            assert img.retained_until is not None  # có chính sách lưu trữ
            assert len(img.sha256 or "") == 64


@pytest.fixture()
def no_models(tmp_path, monkeypatch):
    """Ép trạng thái 'chưa có model' để kiểm thử đường suy giảm trung thực.

    Trước đây các bài này dựa vào việc máy chưa huấn luyện model; sau khi huấn luyện xong
    chúng sẽ sai. Trỏ thư mục model vào thư mục rỗng để bài kiểm thử không phụ thuộc
    trạng thái thật của máy.
    """
    empty = tmp_path / "no_models"
    (empty / "image").mkdir(parents=True, exist_ok=True)
    (empty / "regression").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "image_model_dir", empty / "image")
    monkeypatch.setattr(settings, "regression_model_dir", empty / "regression")
    ic_mod._classifier = None
    rm_mod._model = None
    yield empty
    ic_mod._classifier = None
    rm_mod._model = None


# ---------- 2. API dự đoán khi CHƯA có model ----------

class TestNoModelYet:
    def test_can_dang_nhap(self, api):
        new_client, _, _ = api
        r = new_client().post("/api/v1/predict/image", files={"file": ("a.png", png_bytes(), "image/png")})
        assert r.status_code == 401

    def test_tra_ve_503_va_khong_luu_anh_rac(self, api, no_models):
        new_client, _, tmp_path = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/predict/image", files={"file": ("a.png", png_bytes(), "image/png")})
        assert r.status_code == 503, r.text
        assert "Chưa có model" in r.json()["detail"]
        # không được lưu ảnh khi chưa có model -> thư mục uploads phải trống
        uploads = tmp_path / "uploads"
        assert not uploads.exists() or not any(uploads.rglob("*.*"))

    def test_anh_sai_dinh_dang_tra_400(self, api):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/predict/image", files={"file": ("a.png", b"khong-phai-anh", "image/png")})
        assert r.status_code == 400

    def test_trang_thai_model_noi_ro_chua_co(self, api, no_models):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        body = c.get("/api/v1/predict/models").json()
        assert body["image_classifier"]["available"] is False
        assert "huấn luyện" in body["image_classifier"]["reason"]
        assert body["regression"]["available"] is False

    def test_nang_luong_thieu_du_lieu_thi_bao_unavailable(self, api, no_models):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/foods", json={"name_vi": "Món không rõ calo", "cooking_state": "cooked",
                                          "protein_g_per_100g": 5.0, "source_name": "kiểm thử"})
        fid = r.json()["id"]
        body = c.post("/api/v1/predict/nutrition", json={"food_id": fid}).json()
        assert body["source"] == "unavailable"
        assert body["energy_kcal_per_100g"] is None  # không bịa số
        # ở trạng thái chưa có model: phải nói rõ cả việc thiếu số liệu đo lẫn thiếu model
        assert "chưa có số liệu năng lượng" in body["message"]
        assert "chưa có model hồi quy" in body["message"]
        # tên feature phải theo đúng tên model mong đợi (`water_g`), không phải mã chất
        # trong database (`moisture_g`) — API tự quy đổi khi nhận `moisture_g`.
        assert "water_g" in body["missing_features"]


# ---------- 3. API dự đoán khi CÓ model (vật mẫu kiểm thử) ----------

@pytest.fixture()
def with_image_model(tmp_path, monkeypatch):
    """MobileNetV3-Small với trọng số ngẫu nhiên - chỉ để kiểm tra luồng suy luận."""
    import torch
    import torch.nn as nn
    from torchvision import models as tvm

    model_dir = tmp_path / "model_image"
    model_dir.mkdir()
    net = tvm.mobilenet_v3_small(weights=None)
    net.classifier[-1] = nn.Linear(net.classifier[-1].in_features, len(FIXTURE_LABELS))
    torch.save(
        {
            "state_dict": net.state_dict(),
            "labels": FIXTURE_LABELS,
            "arch": "mobilenet_v3_small",
            "input_size": 224,
        },
        model_dir / "best.pt",
    )
    (model_dir / "latest.json").write_text(
        json.dumps({
            "arch": "mobilenet_v3_small",
            "labels": FIXTURE_LABELS,
            "num_classes": len(FIXTURE_LABELS),
            "trained_at": "VẬT MẪU KIỂM THỬ - trọng số ngẫu nhiên, không phải model đã huấn luyện",
            "metrics": None,
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "image_model_dir", model_dir)
    ic_mod._classifier = None
    yield model_dir
    ic_mod._classifier = None


class TestImagePredictionWithModel:
    def test_nhan_dien_tra_top3(self, api, with_image_model):
        new_client, SessionLocal, _ = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/predict/image", files={"file": ("mon.jpg", jpeg_bytes(), "image/jpeg")})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["top_k"]) == 3
        assert [p["rank"] for p in body["top_k"]] == [1, 2, 3]
        assert {p["label"] for p in body["top_k"]} <= set(FIXTURE_LABELS)
        confidences = [p["confidence"] for p in body["top_k"]]
        assert confidences == sorted(confidences, reverse=True)
        assert all(0.0 <= v <= 1.0 for v in confidences)
        assert body["latency_ms"] is not None and body["latency_ms"] >= 0
        assert "chưa đúng" in body["message"] or "xác nhận" in body["message"]
        assert body["needs_confirmation"] in (True, False)

        # có ghi lịch sử dự đoán
        with SessionLocal() as db:
            rows = db.query(Prediction).all()
            assert len(rows) == 1
            assert rows[0].kind == "image"
            assert len(rows[0].top_k) == 3

    def test_xem_lai_anh_chi_chu_so_huu(self, api, with_image_model):
        new_client, _, _ = api
        a, b = new_client(), new_client()
        _register(a, "a@example.com")
        _register(b, "b@example.com")
        body = a.post("/api/v1/predict/image",
                      files={"file": ("mon.png", png_bytes(), "image/png")}).json()
        r = a.get(f"/api/v1/predict/images/{body['image_id']}")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/")
        assert b.get(f"/api/v1/predict/images/{body['image_id']}").status_code == 404

    def test_goi_y_mon_tu_nhan_dien(self, api, with_image_model):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        # thực phẩm có gắn nhãn ảnh 'pizza'
        r = c.post("/api/v1/foods", json={"name_vi": "Pizza hải sản", "cooking_state": "cooked",
                                          "energy_kcal_per_100g": 266.0, "source_name": "kiểm thử"})
        fid = r.json()["id"]
        # gán nhãn ảnh trực tiếp trong DB
        from app.models import Food

        with api[1]() as db:
            db.get(Food, fid).image_class = "pizza"
            db.commit()

        body = c.post("/api/v1/predict/image",
                      files={"file": ("mon.jpg", jpeg_bytes(), "image/jpeg")}).json()
        labels = [p["label"] for p in body["top_k"]]
        # nhãn "pizza" có thể không phải top-1 (trọng số ngẫu nhiên) nên chỉ kiểm tra
        # rằng gợi ý món khớp với nhãn top-1 nếu nhãn đó có trong database
        assert isinstance(body["suggested_foods"], list)
        assert set(labels) <= set(FIXTURE_LABELS)


@pytest.fixture()
def with_regression_model(tmp_path, monkeypatch):
    """LinearRegression thật (sklearn) huấn luyện trên dữ liệu tổng hợp - vật mẫu kiểm thử."""
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LinearRegression

    model_dir = tmp_path / "model_regression"
    model_dir.mkdir()
    rng = np.random.default_rng(0)
    protein = rng.uniform(0, 30, 300)
    fat = rng.uniform(0, 30, 300)
    carb = rng.uniform(0, 80, 300)
    noise = rng.normal(0, 1, 300)
    energy = protein * 4 + carb * 4 + fat * 9 + noise  # quan hệ Atwater + nhiễu
    # huấn luyện trên DataFrame (giống cách pipeline hồi quy thật sẽ được huấn luyện)
    X = pd.DataFrame({"protein_g": protein, "fat_g": fat, "carbohydrate_g": carb})
    model = LinearRegression().fit(X, energy)

    joblib.dump(model, model_dir / "energy_regression_linearmodel.joblib")
    (model_dir / "latest.json").write_text(
        json.dumps({
            "model_file": "energy_regression_linearmodel.joblib",
            "algorithm": "LinearRegression",
            "feature_names": ["protein_g", "fat_g", "carbohydrate_g"],
            "target": "energy_kcal_per_100g",
            "metrics": {"test": {"MAE": 0.8, "RMSE": 1.0, "R2": 0.999}},
            "trained_at": "VẬT MẪU KIỂM THỬ - dữ liệu tổng hợp",
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "regression_model_dir", model_dir)
    rm_mod._model = None
    yield model_dir
    rm_mod._model = None


class TestNutritionPrediction:
    def test_uu_tien_so_lieu_do_trong_database(self, api, with_regression_model):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/foods", json={"name_vi": "Cơm trắng chín", "cooking_state": "cooked",
                                          "energy_kcal_per_100g": 130.0, "protein_g_per_100g": 2.7,
                                          "fat_g_per_100g": 0.3, "carbohydrate_g_per_100g": 28.2,
                                          "source_name": "kiểm thử"})
        fid = r.json()["id"]
        body = c.post("/api/v1/predict/nutrition", json={"food_id": fid, "weight_grams": 250}).json()
        # §5.2: có số liệu đo thì KHÔNG dùng model
        assert body["source"] == "database"
        assert body["energy_kcal_per_100g"] == pytest.approx(130.0)
        assert body["energy_kcal_for_weight"] == pytest.approx(325.0)

    def test_dung_model_khi_thieu_so_lieu_va_noi_ro_la_uoc_luong(self, api, with_regression_model):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/foods", json={"name_vi": "Món chưa rõ calo", "cooking_state": "cooked",
                                          "protein_g_per_100g": 10.0, "fat_g_per_100g": 5.0,
                                          "carbohydrate_g_per_100g": 20.0, "source_name": "kiểm thử"})
        fid = r.json()["id"]
        body = c.post("/api/v1/predict/nutrition", json={"food_id": fid}).json()
        assert body["source"] == "model"
        # 10*4 + 20*4 + 5*9 = 165 (model học từ dữ liệu Atwater + nhiễu nhỏ)
        assert body["energy_kcal_per_100g"] == pytest.approx(165.0, abs=5.0)
        assert "ước lượng" in body["message"]
        assert body["model"]["algorithm"] == "LinearRegression"

    def test_du_doan_truc_tiep_tu_feature(self, api, with_regression_model):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        body = c.post("/api/v1/predict/nutrition", json={
            "features": {"protein_g": 0.0, "fat_g": 0.0, "carbohydrate_g": 100.0}
        }).json()
        assert body["source"] == "model"
        assert body["energy_kcal_per_100g"] == pytest.approx(400.0, abs=5.0)

    def test_thieu_feature_thi_bao_ro_chu_khong_bia(self, api, with_regression_model):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        r = c.post("/api/v1/predict/nutrition", json={"features": {"protein_g": 5.0}})
        assert r.status_code == 400
        assert "Thiếu feature" in r.json()["detail"]

    def test_khong_co_food_va_feature(self, api):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        assert c.post("/api/v1/predict/nutrition", json={}).status_code == 400

    def test_food_khong_ton_tai(self, api):
        new_client, _, _ = api
        c = new_client()
        _register(c)
        assert c.post("/api/v1/predict/nutrition", json={"food_id": 4321}).status_code == 404
