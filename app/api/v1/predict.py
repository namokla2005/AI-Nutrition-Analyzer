"""API dự đoán: nhận diện thực phẩm từ ảnh và ước lượng năng lượng.

Quy tắc:
- Nếu model chưa được huấn luyện: trả 503 kèm lý do rõ ràng, KHÔNG trả nhãn giả.
- Ảnh được kiểm tra định dạng thật trước khi lưu; không lưu file rác.
- Kết quả nhận diện luôn trả Top-3 kèm confidence; dưới ngưỡng thì yêu cầu xác nhận (§5.1).
- Năng lượng: số liệu đo trong database luôn được ưu tiên hơn model hồi quy (§5.2).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_user
from app.core.utils import normalize_name, utcnow
from app.ml import get_classifier, get_regression_model, labels_vi
from app.ml.exceptions import ModelUnavailableError, PredictionError
from app.ml.regression_model import FEATURE_TO_NUTRIENT_CODE
from app.models import Food, FoodImage, Prediction, User
from app.repositories.food_repository import FoodRepository
from app.schemas.predict import (
    ImagePredictionOut,
    ModelStatusOut,
    NutritionPredictIn,
    NutritionPredictOut,
    SuggestedFood,
    TopKItem,
)
from app.services import upload_service
from app.services.upload_service import UploadError

router = APIRouter(prefix="/predict", tags=["prediction"])

# Feature tối thiểu của bài toán hồi quy năng lượng (dùng để báo rõ còn thiếu gì
# khi chưa có metadata model). Tên phải TRÙNG với tên model mong đợi — model dùng
# `water_g`, còn database lưu mã chất là `moisture_g`; FEATURE_TO_NUTRIENT_CODE lo phần quy đổi.
FALLBACK_REGRESSION_FEATURES = [
    "protein_g",
    "fat_g",
    "carbohydrate_g",
    "fiber_g",
    "water_g",
    "ash_g",
    "food_category",
    "cooking_state",
]

# Tên khác mà người gọi API có thể dùng -> tên model thật sự mong đợi.
# Cần thiết vì database đặt mã chất là `moisture_g` còn model huấn luyện với `water_g`.
FEATURE_ALIASES = {
    "moisture_g": "water_g",
    "water": "water_g",
    "carb_g": "carbohydrate_g",
    "carbs_g": "carbohydrate_g",
    "carbohydrates_g": "carbohydrate_g",
    "protein": "protein_g",
    "fat": "fat_g",
    "fiber": "fiber_g",
    "ash": "ash_g",
    "category": "food_category",
}


def _normalize_features(raw: dict | None) -> dict:
    """Quy đổi tên feature người gọi gửi sang tên model mong đợi (không tự bịa giá trị)."""
    normalized: dict = {}
    for key, value in (raw or {}).items():
        name = FEATURE_ALIASES.get(key, key)
        if name not in normalized or normalized[name] is None:
            normalized[name] = value
    return normalized


@router.get("/models", response_model=ModelStatusOut, summary="Trạng thái các model")
def model_status(user: User = Depends(require_user)) -> dict:
    return {
        "image_classifier": get_classifier().describe(),
        "regression": get_regression_model().describe(),
        "checked_at": utcnow(),
    }


def _suggest_foods(db: Session, label: str, limit: int = 5) -> list[dict]:
    """Gợi ý thực phẩm khớp với nhãn vừa nhận diện.

    Ưu tiên thực phẩm đã được gắn `image_class` (khớp chính xác). Nếu chưa có bản ghi nào
    được gắn nhãn, tìm theo tên (nhãn 'pho_bo' -> 'pho bo') để trang nhận diện vẫn có gợi ý
    thật thay vì danh sách rỗng.
    """
    stmt = (
        select(Food)
        .where(Food.image_class == label)
        .order_by(Food.is_verified.desc(), Food.name_normalized.asc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt))
    if not rows:
        # Nhãn là mã lớp (vd 'nem_ran'); thử lần lượt các từ khoá tiếng Việt/tiếng Anh
        # của món đó để tìm ra thực phẩm thật, thay vì chỉ đổi '_' thành khoảng trắng.
        # Bỏ qua từ khoá trùng sau khi bỏ dấu ('chả giò' và 'cha gio' là một) và từ khoá
        # chắc chắn không có kết quả: mỗi truy vấn xếp hạng trên 102.847 thực phẩm tốn
        # khoảng 300 ms, còn phép kiểm nhanh chỉ vài chục ms (số đo trong BAO_CAO_KIEM_THU.md).
        repo = FoodRepository(db)
        tried: set[str] = set()
        for term in labels_vi.search_terms(label):
            query = normalize_name(term)
            if not query or query in tried:
                continue
            tried.add(query)
            if not repo.has_match(query):
                continue
            rows, _ = repo.search(query=query, limit=limit, with_total=False)
            if rows:
                break
    return [
        {
            "food_id": f.id,
            "name": f.display_name,
            "energy_kcal_per_100g": f.energy_kcal_per_100g,
            "category": f.category,
            "cooking_state": f.cooking_state,
        }
        for f in rows
    ]


@router.post("/image", response_model=ImagePredictionOut, summary="Nhận diện thực phẩm từ ảnh")
async def predict_image(
    file: UploadFile = File(..., description="Ảnh JPEG/PNG/WEBP"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    started = time.perf_counter()
    raw = await file.read(settings.max_upload_bytes + 1)

    # 1) Kiểm tra ảnh thật trước khi tốn công lưu
    try:
        upload_service.validate_image_bytes(raw, file.filename)
    except UploadError as exc:
        code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if exc.code == "too_large" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=exc.message) from exc

    # 2) Model phải sẵn sàng - nếu chưa thì báo rõ, không lưu ảnh, không bịa kết quả
    classifier = get_classifier()
    if not classifier.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Chưa có model nhận diện ảnh. Hãy huấn luyện MobileNetV3-Small "
                "(training/image/train.py) rồi thử lại."
            ),
        )

    image = upload_service.save_user_image(db, user.id, file.filename, raw)

    try:
        predictions = classifier.predict_topk(upload_service.absolute_path(image))
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except PredictionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    top1 = predictions[0] if predictions else None
    needs_confirmation = bool(top1 and top1.confidence < settings.image_confidence_threshold)

    record = Prediction(
        user_id=user.id,
        kind="image",
        image_id=image.id,
        top_k=[{
            "rank": p.rank,
            "label": p.label,
            "display_label": labels_vi.display_label(p.label),
            "confidence": p.confidence,
        } for p in predictions],
        confidence=top1.confidence if top1 else None,
        latency_ms=latency_ms,
    )
    db.add(record)
    db.commit()

    suggestions = _suggest_foods(db, top1.label) if top1 else []
    message = (
        "Độ tin cậy thấp - hãy xác nhận hoặc chọn lại món."
        if needs_confirmation
        else "Kết quả nhận diện có thể chưa đúng - hãy kiểm tra lại trước khi ghi vào nhật ký."
    )

    return {
        "image_id": image.id,
        "model": {
            "arch": classifier.metadata().get("arch", "mobilenet_v3_small"),
            "trained_at": classifier.metadata().get("trained_at"),
            "num_classes": len(classifier.metadata().get("labels") or []),
            "test_metrics": (classifier.metadata().get("metrics") or {}),
        },
        "top_k": [
            TopKItem(rank=p.rank, label=p.label,
                     display_label=labels_vi.display_label(p.label), confidence=p.confidence)
            for p in predictions
        ],
        "confidence": top1.confidence if top1 else None,
        "needs_confirmation": needs_confirmation,
        "message": message,
        "suggested_foods": [SuggestedFood(**s) for s in suggestions],
        "latency_ms": latency_ms,
    }


@router.get("/images/{image_id}", summary="Xem lại ảnh đã tải lên (chỉ chủ sở hữu)")
def get_image(
    image_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    image = db.get(FoodImage, image_id)
    # Không tiết lộ sự tồn tại của ảnh người khác -> trả 404
    if image is None or image.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ảnh.")
    try:
        path = upload_service.absolute_path(image)
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tệp ảnh không còn trên đĩa.")
    return FileResponse(path, media_type=image.mime_type, filename=path.name)


@router.post("/nutrition", response_model=NutritionPredictOut, summary="Tra/ước lượng năng lượng")
def predict_nutrition(
    payload: NutritionPredictIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    # --- Trường hợp 1: dự đoán trực tiếp từ feature thô ---
    if payload.food_id is None:
        if not payload.features:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cần cung cấp food_id hoặc features.",
            )
        model = get_regression_model()
        try:
            result = model.predict(_normalize_features(payload.features))
        except ModelUnavailableError as exc:
            return {
                "source": "unavailable",
                "model": model.describe(),
                "message": exc.message,
                "missing_features": [],
            }
        except PredictionError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {
            "source": "model",
            "energy_kcal_per_100g": result["predicted_energy_kcal_per_100g"],
            "model": result["model"],
            "message": result["disclaimer"],
            "missing_features": [],
        }

    # --- Trường hợp 2: theo food_id -> ưu tiên số liệu đo trong database ---
    repo = FoodRepository(db)
    food = repo.get(payload.food_id)
    if food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thực phẩm.")

    per_100g = repo.nutrient_values_per_100g(food.id)
    measured = per_100g.get("energy_kcal")
    weight = payload.weight_grams

    if measured is not None:
        return {
            "food_id": food.id,
            "food_name": food.display_name,
            "source": "database",
            "energy_kcal_per_100g": measured,
            "weight_grams": weight,
            "energy_kcal_for_weight": round(measured * weight / 100.0, 1) if weight else None,
            "model": {},
            "message": "Dùng số liệu năng lượng có sẵn trong database (nguồn dữ liệu đã ghi nhận).",
            "missing_features": [],
        }

    # Thiếu số liệu đo -> xem có thể ước lượng bằng model hồi quy hay không
    model = get_regression_model()
    if model.is_available and model.feature_names:
        features = model.build_features(per_100g, food)
        if payload.features:
            for key, value in _normalize_features(payload.features).items():
                # chấp nhận cả tên feature của model và mã chất dinh dưỡng trong database
                if key in features:
                    features[key] = value
                else:
                    for name in model.feature_names:
                        if FEATURE_TO_NUTRIENT_CODE.get(name, name) == key:
                            features[name] = value
    else:
        features = {name: per_100g.get(FEATURE_TO_NUTRIENT_CODE.get(name, name)) for name in FALLBACK_REGRESSION_FEATURES}
        if payload.features:
            features.update(_normalize_features(payload.features))
    missing = model.missing_features(features)

    if not model.is_available:
        return {
            "food_id": food.id,
            "food_name": food.display_name,
            "source": "unavailable",
            "weight_grams": weight,
            "model": model.describe(),
            "message": "Thực phẩm này chưa có số liệu năng lượng đo được, và hiện chưa có model "
            "hồi quy nào được huấn luyện. Hãy bổ sung dữ liệu nguồn (nguồn rõ ràng) hoặc huấn "
            "luyện model tại training/regression.",
            "missing_features": missing,
        }

    if missing:
        return {
            "food_id": food.id,
            "food_name": food.display_name,
            "source": "unavailable",
            "weight_grams": weight,
            "model": model.describe(),
            "message": "Thực phẩm này thiếu số liệu năng lượng và cũng thiếu feature để ước lượng. "
            "Hãy bổ sung dữ liệu nguồn thay vì suy đoán.",
            "missing_features": missing,
        }

    try:
        result = model.predict(features)
    except ModelUnavailableError as exc:
        return {
            "food_id": food.id,
            "food_name": food.display_name,
            "source": "unavailable",
            "weight_grams": weight,
            "model": model.describe(),
            "message": exc.message,
            "missing_features": [],
        }

    value = result["predicted_energy_kcal_per_100g"]
    return {
        "food_id": food.id,
        "food_name": food.display_name,
        "source": "model",
        "energy_kcal_per_100g": value,
        "weight_grams": weight,
        "energy_kcal_for_weight": round(value * weight / 100.0, 1) if weight else None,
        "model": result["model"],
        "message": result["disclaimer"],
        "missing_features": [],
    }
