"""Kiểm thử luồng huấn luyện nhận diện ảnh (dữ liệu TỔNG HỢP).

Mục đích: chứng minh script huấn luyện chạy thật, sinh đúng file model + metadata +
báo cáo, và model lưu ra nạp lại được bằng `app.ml.ImageClassifier`.

Đây KHÔNG phải thực nghiệm của đề tài: ảnh là hình khối tổng hợp do bài kiểm thử vẽ ra.
Kết quả thực nghiệm thật nằm ở data/reports/image_experiment.md sau khi huấn luyện
trên dataset ảnh thật.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = PROJECT_ROOT / "training" / "image" / "train.py"
CLASSES = ["com_tam", "pizza", "salad"]


def _draw(cls: str, index: int, size: int = 96) -> Image.Image:
    """Vẽ ảnh tổng hợp khác nhau cho từng lớp (có nhiễu nhỏ để các ảnh không trùng nhau)."""
    img = Image.new("RGB", (size, size), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    jitter = (index * 7) % 12
    if cls == "com_tam":
        draw.rectangle([10 + jitter, 10, size - 10, size - 10 - jitter], fill=(196, 142, 60))
    elif cls == "pizza":
        draw.ellipse([8, 8 + jitter, size - 8, size - 8], fill=(200, 60, 40))
    else:
        draw.polygon([(size // 2, 10 + jitter), (size - 12, size - 12), (12, size - 12)],
                     fill=(70, 150, 70))
    return img


def _make_dataset(raw_dir: Path, per_class: int = 12) -> None:
    for cls in CLASSES:
        folder = raw_dir / cls
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(per_class):
            _draw(cls, i).save(folder / f"{cls}_{i:03d}.jpg", quality=88)


def _run_train(raw_dir: Path, manifest: Path, out_dir: Path, report_dir: Path,
               extra: list[str] | None = None) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, str(TRAIN_SCRIPT),
        "--raw-dir", str(raw_dir),
        "--manifest", str(manifest),
        "--out-dir", str(out_dir),
        "--report-dir", str(report_dir),
        "--epochs", "1",
        "--batch-size", "4",
        "--no-pretrained",
        "--seed", "7",
    ] + (extra or [])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=str(PROJECT_ROOT))


class TestTrainingPipeline:
    def test_quet_thu_muc_va_sinh_model(self, tmp_path):
        raw = tmp_path / "raw"
        _make_dataset(raw)
        out = tmp_path / "models"
        report = tmp_path / "reports"

        result = _run_train(raw, tmp_path / "khong_ton_tai.csv", out, report)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "KHÔNG LUYỆN" not in result.stdout
        assert "quét thư mục" in result.stdout

        # 1. file model đúng hợp đồng mà app/ml/image_classifier.py mong đợi
        assert (out / "best.pt").exists()
        metadata = json.loads((out / "latest.json").read_text(encoding="utf-8"))
        assert metadata["arch"] == "mobilenet_v3_small"
        assert metadata["labels"] == CLASSES
        assert metadata["num_classes"] == 3

        # 2. metrics phải là số THẬT trong khoảng hợp lệ
        metrics = metadata["metrics"]
        assert 0.0 <= metrics["test_accuracy"] <= 1.0
        assert 0.0 <= metrics["best_val_accuracy"] <= 1.0
        assert len(metrics["test_per_class"]) == 3
        assert len(metrics["confusion_matrix"]) == 3
        # ma trận nhầm lẫn phải chứa đúng số ảnh test: 3 lớp × round(12 × 0,15) = 6
        assert sum(sum(row) for row in metrics["confusion_matrix"]) == 6
        assert metrics["test_per_class"][0]["label"] in CLASSES

        # 3. có ghi lại thời gian chạy thật (đo được, > 0)
        assert metadata["timing"]["total_seconds"] > 0
        assert len(metadata["timing"]["seconds_per_epoch"]) == len(metadata["history"])
        assert metadata["hyperparameters"]["epochs_run"] == 1
        assert metadata["hyperparameters"]["pretrained"] is False

        # 4. báo cáo tiếng Việt có số liệu thật
        report_file = report / "image_experiment.md"
        assert report_file.exists()
        text = report_file.read_text(encoding="utf-8")
        assert "BÁO CÁO THỰC NGHIỆM" in text
        assert f"{metrics['test_accuracy']:.4f}" in text
        assert "MobileNetV3-Small" in text

        # 5. có biểu đồ
        assert (report / "figures" / "image_training_curves.png").exists()
        assert (report / "figures" / "image_confusion_matrix.png").exists()

    def test_model_nap_lai_duoc_bang_lop_suy_luan(self, tmp_path):
        """Đây là điểm quan trọng nhất: model lưu ra phải dùng được ngay trong app."""
        from app.ml.image_classifier import ImageClassifier

        raw = tmp_path / "raw"
        _make_dataset(raw)
        out = tmp_path / "models"
        report = tmp_path / "reports"
        result = _run_train(raw, tmp_path / "none.csv", out, report)
        assert result.returncode == 0, result.stdout + result.stderr

        classifier = ImageClassifier(model_dir=out)
        assert classifier.is_available is True
        assert classifier.load() is True

        sample = next((raw / "pizza").glob("*.jpg"))
        predictions = classifier.predict_topk(sample, top_k=3)
        assert len(predictions) == 3
        assert {p.label for p in predictions} <= set(CLASSES)
        confidences = [p.confidence for p in predictions]
        assert confidences == sorted(confidences, reverse=True)
        assert all(0.0 <= c <= 1.0 for c in confidences)
        assert [p.rank for p in predictions] == [1, 2, 3]
        # mô tả model phải đọc được metadata
        described = classifier.describe()
        assert described["available"] is True
        assert described["num_classes"] == 3
        assert described["reason"] is None

    def test_dung_manifest_neu_co(self, tmp_path):
        """Khi có manifest (do prepare_dataset.py sinh ra) thì phải tôn trọng cột split."""
        raw = tmp_path / "raw"
        _make_dataset(raw, per_class=6)
        manifest = tmp_path / "manifest.csv"
        rows = []
        for cls in CLASSES:
            files = sorted((raw / cls).glob("*.jpg"))
            for i, path in enumerate(files):
                split = "train" if i < 4 else ("val" if i == 4 else "test")
                rows.append({
                    "our_class": cls,
                    "source_class": cls,
                    "source": "kiem_thu",
                    "split": split,
                    "relative_path": str(path),
                    "width": 96,
                    "height": 96,
                    "bytes": path.stat().st_size,
                    "licence": "dữ liệu tổng hợp của bài kiểm thử",
                })
        with manifest.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        result = _run_train(raw, manifest, tmp_path / "models", tmp_path / "reports")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "manifest" in result.stdout
        metadata = json.loads((tmp_path / "models" / "latest.json").read_text(encoding="utf-8"))
        assert metadata["dataset"]["counts"] == {"train": 12, "val": 3, "test": 3}

    def test_khong_co_du_lieu_thi_bao_ro_khong_doan_bua(self, tmp_path):
        empty = tmp_path / "raw_empty"
        empty.mkdir()
        result = _run_train(empty, tmp_path / "none.csv", tmp_path / "m", tmp_path / "r")
        assert result.returncode == 2
        assert "Không tìm thấy ảnh huấn luyện" in result.stdout
        assert not (tmp_path / "m" / "best.pt").exists()
        assert not (tmp_path / "m" / "latest.json").exists()

    def test_mot_lop_thi_tu_choi_phan_loai(self, tmp_path):
        raw = tmp_path / "raw_one"
        for i in range(8):
            (raw / "chi_mot_lop").mkdir(parents=True, exist_ok=True)
            _draw("pizza", i).save(raw / "chi_mot_lop" / f"x{i}.jpg")
        result = _run_train(raw, tmp_path / "none.csv", tmp_path / "m", tmp_path / "r")
        assert result.returncode == 2
        assert "tối thiểu 2 lớp" in result.stdout
