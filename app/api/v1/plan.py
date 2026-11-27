"""API đề xuất thực đơn: nhu cầu năng lượng từ chỉ số cơ thể và thực đơn các bữa còn lại.

Cấu trúc dữ liệu trả về do `app.services.plan_service` dựng (không khai báo response_model để giữ
nguyên các trường chẩn đoán như `warnings`, `constraints`, `fit_note`).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_user
from app.models import User
from app.services import plan_service
from app.services.nutrition_needs import compute_needs, exercise_suggestion

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/needs", summary="Nhu cầu năng lượng tính từ chỉ số cơ thể")
def needs(user: User = Depends(require_user)) -> dict:
    """Tính BMR/TDEE/đề xuất kcal và gợi ý vận động từ hồ sơ người dùng.

    Thiếu chỉ số nào thì trả về `missing_fields` (không suy diễn, không bịa số).
    """
    result = compute_needs(user.profile, date.today())
    data = result.as_dict()
    data["formula"] = {
        "bmr": "Mifflin–St Jeor: 10×cân nặng + 6,25×chiều cao − 5×tuổi + 5 (nam) / − 161 (nữ)",
        "tdee": "BMR × hệ số vận động (ít 1,2 · nhẹ 1,375 · vừa 1,55 · nhiều 1,725 · rất nhiều 1,9)",
        "goal": "giảm cân −500 kcal · giữ cân 0 · tăng cân +300 kcal (có ngưỡng an toàn)",
    }
    data["exercise"] = exercise_suggestion(result, None)
    data["current_target_kcal"] = getattr(user.profile, "daily_kcal_target", None)
    return data


@router.get("/today", summary="Thực đơn đề xuất cho các bữa còn lại hôm nay")
def today(
    user: User = Depends(require_user),
    day: date | None = Query(default=None, description="Bỏ trống để lấy hôm nay (giờ Việt Nam)"),
    db: Session = Depends(get_db),
) -> dict:
    """Đề xuất thực đơn dựa trên: chỉ số cơ thể · mục tiêu kcal · các bữa ĐÃ ghi · kcal còn lại ·
    ghi chú trong hồ sơ (dị ứng/kiêng/chay...). Mọi con số lấy từ CSDL thật.
    """
    return plan_service.build_plan(db, user, day)
