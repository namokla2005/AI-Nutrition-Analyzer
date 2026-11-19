"""API nhật ký ăn uống. Mọi thao tác chỉ trên dữ liệu của người đang đăng nhập."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_user
from app.models import User
from app.schemas.meal import MealCreateIn, MealListOut, MealOut, MealUpdateIn
from app.services import meal_service
from app.services.meal_service import MealServiceError

router = APIRouter(prefix="/meals", tags=["meals"])


def _fail(exc: MealServiceError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if exc.code in ("not_found", "food_not_found")
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=exc.message)


@router.post("", response_model=MealOut, status_code=status.HTTP_201_CREATED, summary="Thêm bữa ăn")
def create_meal(
    payload: MealCreateIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        meal = meal_service.create_meal(db, user.id, payload.model_dump())
    except MealServiceError as exc:
        raise _fail(exc) from exc
    return meal_service.meal_to_dict(meal)


@router.get("", response_model=MealListOut, summary="Xem nhật ký ăn uống")
def list_meals(
    date_from: date | None = Query(default=None, description="Từ ngày (giờ địa phương)"),
    date_to: date | None = Query(default=None, description="Đến ngày (giờ địa phương)"),
    meal_type: str | None = Query(default=None, pattern="^(breakfast|lunch|dinner|snack)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> MealListOut:
    meals, total = meal_service.list_meals(
        db, user.id, date_from=date_from, date_to=date_to, meal_type=meal_type,
        limit=limit, offset=offset,
    )
    return MealListOut(
        items=[meal_service.meal_to_dict(m) for m in meals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{meal_id}", response_model=MealOut, summary="Chi tiết một bữa ăn")
def get_meal(meal_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    meal = meal_service.get_meal(db, user.id, meal_id)
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bữa ăn.")
    return meal_service.meal_to_dict(meal)


@router.put("/{meal_id}", response_model=MealOut, summary="Sửa bữa ăn")
def update_meal(
    meal_id: int,
    payload: MealUpdateIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        meal = meal_service.update_meal(db, user.id, meal_id, payload.model_dump())
    except MealServiceError as exc:
        raise _fail(exc) from exc
    return meal_service.meal_to_dict(meal)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa bữa ăn")
def delete_meal(
    meal_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        meal_service.delete_meal(db, user.id, meal_id)
    except MealServiceError as exc:
        raise _fail(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
