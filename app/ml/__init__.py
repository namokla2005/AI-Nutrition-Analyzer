"""Lớp Machine Learning: nạp model đã huấn luyện và suy luận.

Nguyên tắc: nếu model chưa có, lớp này phải BÁO RÕ là chưa có - tuyệt đối không
trả kết quả giả để giao diện trông như hệ thống đã hoạt động.
"""
from __future__ import annotations

from app.ml.exceptions import ModelUnavailableError, PredictionError
from app.ml.image_classifier import ImageClassifier, Prediction, get_classifier
from app.ml.regression_model import RegressionModel, get_regression_model

__all__ = [
    "ModelUnavailableError",
    "PredictionError",
    "ImageClassifier",
    "Prediction",
    "get_classifier",
    "RegressionModel",
    "get_regression_model",
]
