"""Nhận diện thực phẩm bằng ảnh: MobileNetV3-Small (transfer learning).

Hợp đồng file model (do training/image/train.py sinh ra):
    models/image/best.pt   -> torch.save({"state_dict": ..., "labels": [...],
                                          "arch": "mobilenet_v3_small",
                                          "input_size": 224})
    models/image/latest.json -> metadata: metrics thực tế, thời điểm huấn luyện,
                                số lớp, ghi chú dataset, thư viện.

Nếu thiếu file: `is_available` = False và `predict_topk` ném ModelUnavailableError.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.ml.exceptions import ModelUnavailableError, PredictionError

logger = logging.getLogger(__name__)

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


@dataclass
class Prediction:
    label: str
    confidence: float
    rank: int


class ImageClassifier:
    """Bọc model phân loại ảnh, nạp model một lần và tái sử dụng."""

    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = Path(model_dir or settings.image_model_dir)
        self._model = None
        self._labels: list[str] = []
        self._metadata: dict = {}
        self._transform = None
        self._lock = threading.Lock()

    # ---------- trạng thái ----------

    @property
    def weights_path(self) -> Path:
        return self.model_dir / "best.pt"

    @property
    def metadata_path(self) -> Path:
        return self.model_dir / "latest.json"

    @property
    def is_available(self) -> bool:
        return self.weights_path.exists()

    def metadata(self) -> dict:
        if not self._metadata and self.metadata_path.exists():
            try:
                self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Không đọc được metadata model ảnh: %s", type(exc).__name__)
                self._metadata = {}
        return self._metadata

    def describe(self) -> dict:
        meta = self.metadata()
        return {
            "available": self.is_available,
            "weights": str(self.weights_path) if self.is_available else None,
            "labels": meta.get("labels") or self._labels or None,
            "num_classes": meta.get("num_classes"),
            "trained_at": meta.get("trained_at"),
            "metrics": meta.get("metrics"),
            "dataset_note": meta.get("dataset_note"),
            "reason": None
            if self.is_available
            else "Chưa có file model (models/image/best.pt). Hãy huấn luyện bằng "
            "training/image/train.py sau khi chuẩn bị dataset.",
        }

    # ---------- nạp model ----------

    def load(self) -> bool:
        if not self.is_available:
            return False
        with self._lock:
            if self._model is not None:
                return True
            try:
                import torch
                import torch.nn as nn
                from torchvision import models as tvm
                from torchvision import transforms
            except ImportError as exc:  # pragma: no cover - phụ thuộc môi trường
                raise ModelUnavailableError(
                    "Thiếu PyTorch/torchvision trong môi trường ảo.", str(exc)
                ) from exc

            checkpoint = torch.load(self.weights_path, map_location="cpu", weights_only=False)
            labels = list(checkpoint.get("labels") or [])
            arch = checkpoint.get("arch", "mobilenet_v3_small")
            input_size = int(checkpoint.get("input_size", settings.image_input_size))
            if not labels:
                raise ModelUnavailableError("File model thiếu danh sách nhãn.")

            net = tvm.mobilenet_v3_small(weights=None)
            in_features = net.classifier[-1].in_features
            net.classifier[-1] = nn.Linear(in_features, len(labels))
            net.load_state_dict(checkpoint["state_dict"])
            net.eval()

            self._model = net
            self._labels = labels
            self._transform = transforms.Compose(
                [
                    transforms.Resize(int(input_size * 256 / 224)),
                    transforms.CenterCrop(input_size),
                    transforms.ToTensor(),
                    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
                ]
            )
            self._metadata = dict(self.metadata())
            self._metadata.setdefault("arch", arch)
            logger.info("Đã nạp model ảnh: %d lớp (%s)", len(labels), arch)
            return True

    # ---------- suy luận ----------

    def predict_topk(self, image_path: str | Path, top_k: int | None = None) -> list[Prediction]:
        if not self.load():
            raise ModelUnavailableError(
                "Chưa huấn luyện model nhận diện ảnh.",
                f"Không tìm thấy {self.weights_path}",
            )
        try:
            import torch
            from PIL import Image, UnidentifiedImageError
        except ImportError as exc:  # pragma: no cover
            raise ModelUnavailableError("Thiếu Pillow/PyTorch.", str(exc)) from exc

        try:
            with Image.open(image_path) as img:
                rgb = img.convert("RGB")
                tensor = self._transform(rgb).unsqueeze(0)
        except (UnidentifiedImageError, OSError) as exc:
            raise PredictionError("File ảnh không hợp lệ hoặc đã hỏng.") from exc

        k = max(1, min(int(top_k or settings.image_top_k), len(self._labels)))
        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0)
        top = torch.topk(probs, k)

        return [
            Prediction(label=self._labels[int(idx)], confidence=round(float(score), 4), rank=rank + 1)
            for rank, (score, idx) in enumerate(zip(top.values.tolist(), top.indices.tolist()))
        ]


_classifier: ImageClassifier | None = None


def get_classifier() -> ImageClassifier:
    """Singleton - tránh nạp lại model cho mỗi request."""
    global _classifier
    if _classifier is None:
        _classifier = ImageClassifier()
    return _classifier
