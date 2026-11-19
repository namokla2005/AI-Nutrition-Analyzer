"""Ước lượng năng lượng bằng model hồi quy đã huấn luyện (joblib).

Vai trò theo §5.2: giá trị năng lượng CÓ SẴN trong database luôn được ưu tiên.
Model hồi quy chỉ là phương pháp ước lượng BỔ SUNG khi thiếu số liệu - và khi dùng
thì phải ghi rõ là giá trị ước lượng từ model, kèm cảnh báo sai số (MAE).

Lớp này đọc được HAI định dạng metadata:
1. Hợp đồng của ứng dụng: `latest.json` với {model_file, feature_names,
   metrics.test.MAE/RMSE/R2}.
2. Định dạng do training/regression sinh ra: `experiment_metadata.json` +
   `<model>_metadata.json` với {model_file (đường dẫn tính từ gốc dự án), feature_list,
   metrics.{train,validation,test}.{mae,rmse,r2}, selected_best_model}.
Cả hai được chuẩn hóa về cùng một dạng nội bộ để tầng API không phải biết chi tiết.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from app.core.config import BASE_DIR, settings
from app.ml.exceptions import ModelUnavailableError, PredictionError

logger = logging.getLogger(__name__)

# Tên feature của model (đặt theo cột CSV của USDA) -> mã chất dinh dưỡng trong database
FEATURE_TO_NUTRIENT_CODE = {
    "water_g": "moisture_g",
    "moisture_g": "moisture_g",
}

# Feature phân loại lấy từ bảng foods, không phải từ food_nutrients
CATEGORICAL_TO_FOOD_ATTR = {
    "food_category": "category",
    "category": "category",
    "cooking_state": "cooking_state",
}

CANDIDATE_MODELS = ("random_forest", "gradient_boosting", "linear_regression", "baseline_mean")


class RegressionModel:
    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = Path(model_dir or settings.regression_model_dir)
        self._pipeline = None
        self._metadata: dict = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ metadata

    @property
    def app_contract_path(self) -> Path:
        return self.model_dir / "latest.json"

    @property
    def experiment_path(self) -> Path:
        return self.model_dir / "experiment_metadata.json"

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Không đọc được %s: %s", path.name, type(exc).__name__)
            return {}

    def _normalize_metrics(self, raw: dict) -> dict:
        """Chuẩn hóa mae/rmse/r2 (chữ thường) và MAE/RMSE/R2 (chữ hoa) về cùng dạng."""
        out: dict = {}
        for split, values in (raw or {}).items():
            if not isinstance(values, dict):
                continue
            out[str(split)] = {
                "MAE": values.get("MAE", values.get("mae")),
                "RMSE": values.get("RMSE", values.get("rmse")),
                "R2": values.get("R2", values.get("r2")),
            }
        return out

    def _resolve_model_file(self, raw_path: str) -> Path:
        """Đường dẫn trong metadata có thể tính từ gốc dự án hoặc từ thư mục model."""
        candidate = Path(raw_path)
        for path in (candidate, self.model_dir / candidate.name,
                     BASE_DIR / candidate, self.model_dir / candidate):
            if path.is_file():
                return path
        return self.model_dir / candidate.name

    def metadata(self) -> dict:
        """Metadata đã chuẩn hóa; đọc được cả hai định dạng trên đĩa."""
        if self._metadata:
            return self._metadata

        if self.app_contract_path.exists():
            raw = self._read_json(self.app_contract_path)
            self._metadata = {
                "source_format": "app_contract",
                "model_file": raw.get("model_file"),
                "algorithm": raw.get("algorithm"),
                "feature_names": list(raw.get("feature_names") or []),
                "target": raw.get("target", "energy_kcal_per_100g"),
                "metrics": self._normalize_metrics(raw.get("metrics") or {}),
                "trained_at": raw.get("trained_at"),
                "dataset_note": raw.get("dataset_note"),
            }
            return self._metadata

        if self.experiment_path.exists():
            per_model: list[tuple[str, dict]] = []
            for name in CANDIDATE_MODELS:
                path = self.model_dir / f"{name}_metadata.json"
                if path.exists():
                    per_model.append((name, self._read_json(path)))

            chosen_name, chosen = None, None
            for name, meta in per_model:
                flag = meta.get("selected_best_model")
                if flag is True or flag == name:
                    chosen_name, chosen = name, meta
                    break
            if chosen is None and per_model:
                real = [(n, m) for n, m in per_model if n != "baseline_mean"] or per_model

                def val_rmse(item: tuple[str, dict]) -> float:
                    metrics = self._normalize_metrics(item[1].get("metrics") or {})
                    value = (metrics.get("validation") or {}).get("RMSE")
                    return float(value) if value is not None else float("inf")

                chosen_name, chosen = min(real, key=val_rmse)

            if chosen is not None:
                provenance = chosen.get("provenance")
                self._metadata = {
                    "source_format": "training_pipeline",
                    "model_file": chosen.get("model_file"),
                    "algorithm": chosen.get("algorithm"),
                    "feature_names": list(chosen.get("feature_list") or []),
                    "target": chosen.get("target", "energy_kcal_per_100g"),
                    "metrics": self._normalize_metrics(chosen.get("metrics") or {}),
                    "trained_at": chosen.get("created_at_utc"),
                    "dataset_note": provenance.get("licence_note")
                    if isinstance(provenance, dict) else None,
                    "selected_model": chosen_name,
                    "all_models": {n: self._normalize_metrics(m.get("metrics") or {})
                                   for n, m in per_model},
                    "split": chosen.get("split"),
                    "leakage_controls": chosen.get("leakage_controls"),
                    "missing_value_rules": chosen.get("missing_value_rules"),
                    "hyperparameters": chosen.get("hyperparameters"),
                    "feature_units": chosen.get("feature_units"),
                }
                return self._metadata

        self._metadata = {}
        return self._metadata

    @property
    def feature_names(self) -> list[str]:
        return list(self.metadata().get("feature_names") or [])

    @property
    def nutrient_codes(self) -> list[str]:
        """Các feature là chất dinh dưỡng, quy về mã trong database."""
        return [FEATURE_TO_NUTRIENT_CODE.get(f, f) for f in self.feature_names
                if f not in CATEGORICAL_TO_FOOD_ATTR]

    @property
    def food_attributes(self) -> list[str]:
        return [CATEGORICAL_TO_FOOD_ATTR[f] for f in self.feature_names
                if f in CATEGORICAL_TO_FOOD_ATTR]

    def _model_path(self) -> Path | None:
        raw = self.metadata().get("model_file")
        if not raw:
            return None
        path = self._resolve_model_file(str(raw))
        return path if path.is_file() else None

    @property
    def is_available(self) -> bool:
        return self._model_path() is not None

    def describe(self) -> dict:
        meta = self.metadata()
        test = (meta.get("metrics") or {}).get("test") or {}
        return {
            "available": self.is_available,
            "algorithm": meta.get("algorithm"),
            "selected_model": meta.get("selected_model"),
            "feature_names": meta.get("feature_names"),
            "target": meta.get("target"),
            "metrics": {"test": test, "all_splits": meta.get("metrics")},
            # So sánh 3 thuật toán + baseline (§5.2 yêu cầu thực nghiệm và so sánh)
            "model_comparison": meta.get("all_models"),
            "trained_at": meta.get("trained_at"),
            "model_file": str(self._model_path()) if self.is_available else meta.get("model_file"),
            "source_format": meta.get("source_format"),
            "dataset_note": meta.get("dataset_note"),
            "leakage_controls": meta.get("leakage_controls"),
            "reason": None if self.is_available
            else "Chưa có model hồi quy (cần models/regression/latest.json hoặc "
            "experiment_metadata.json kèm file .joblib). Hãy huấn luyện bằng training/regression.",
        }

    # ------------------------------------------------------------ suy luận

    def load(self) -> bool:
        path = self._model_path()
        if path is None:
            return False
        with self._lock:
            if self._pipeline is not None:
                return True
            try:
                import joblib
            except ImportError as exc:  # pragma: no cover
                raise ModelUnavailableError("Thiếu thư viện joblib.", str(exc)) from exc
            self._pipeline = joblib.load(path)
            logger.info("Đã nạp model hồi quy: %s (%s)",
                        self.metadata().get("algorithm"), path.name)
            return True

    def build_features(self, per_100g: dict, food=None) -> dict:
        """Ghép feature theo ĐÚNG tên mà model mong đợi, từ dữ liệu trong database."""
        features: dict = {}
        for name in self.feature_names:
            if name in CATEGORICAL_TO_FOOD_ATTR:
                attr = CATEGORICAL_TO_FOOD_ATTR[name]
                features[name] = getattr(food, attr, None) if food is not None else None
            else:
                features[name] = per_100g.get(FEATURE_TO_NUTRIENT_CODE.get(name, name))
        return features

    @staticmethod
    def missing_features(features: dict) -> list[str]:
        """Feature số bị thiếu. Feature phân loại không tính (pipeline tự xử lý 'Unknown')."""
        return [name for name, value in features.items()
                if value is None and name not in CATEGORICAL_TO_FOOD_ATTR]

    def predict(self, features: dict) -> dict:
        if not self.load():
            raise ModelUnavailableError(
                "Chưa huấn luyện model hồi quy năng lượng.",
                str(self.experiment_path if not self.app_contract_path.exists()
                    else self.app_contract_path),
            )
        names = self.feature_names
        if not names:
            raise ModelUnavailableError("Metadata model hồi quy thiếu danh sách feature.")

        missing = self.missing_features({n: features.get(n) for n in names})
        if missing:
            raise PredictionError(
                "Thiếu feature đầu vào: " + ", ".join(missing)
                + ". Hãy bổ sung hoặc để trống (model này không tự bịa giá trị thiếu)."
            )

        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover
            raise ModelUnavailableError("Thiếu pandas.", str(exc)) from exc

        row = pd.DataFrame([{name: features.get(name) for name in names}])
        try:
            value = float(self._pipeline.predict(row)[0])
        except Exception as exc:
            raise PredictionError(
                f"Model không dự đoán được với dữ liệu này: {type(exc).__name__}."
            ) from exc

        meta = self.metadata()
        test = (meta.get("metrics") or {}).get("test") or {}
        return {
            "predicted_energy_kcal_per_100g": round(value, 1),
            "model": {
                "algorithm": meta.get("algorithm"),
                "selected_model": meta.get("selected_model"),
                "trained_at": meta.get("trained_at"),
                "test_MAE": test.get("MAE"),
                "test_RMSE": test.get("RMSE"),
                "test_R2": test.get("R2"),
            },
            "disclaimer": "Giá trị do model hồi quy ước lượng, KHÔNG phải số liệu đo từ nguồn "
            "dinh dưỡng. Chỉ dùng khi dữ liệu chuẩn bị thiếu.",
        }


_model: RegressionModel | None = None


def get_regression_model() -> RegressionModel:
    global _model
    if _model is None:
        _model = RegressionModel()
    return _model
