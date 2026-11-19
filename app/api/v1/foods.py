"""API tra cứu thực phẩm và tính khẩu phần dinh dưỡng."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_user
from app.models import User
from app.schemas.food import (
    FoodCreateRequest,
    FoodDetailOut,
    FoodListOut,
    FoodOut,
    PortionOut,
)
from app.services import food_service
from app.services.food_service import FoodServiceError

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("", response_model=FoodListOut, summary="Tra cứu thực phẩm")
def list_foods(
    q: str | None = Query(default=None, max_length=120, description="Từ khóa (có dấu hoặc không dấu)"),
    category: str | None = Query(default=None, max_length=80),
    food_group: str | None = Query(default=None, max_length=80),
    cooking_state: str | None = Query(default=None, pattern="^(raw|cooked|processed|unknown)$"),
    min_kcal: float | None = Query(default=None, ge=0, le=2000),
    max_kcal: float | None = Query(default=None, ge=0, le=2000),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> FoodListOut:
    items, total = food_service.list_foods(
        db,
        query=q,
        category=category,
        food_group=food_group,
        cooking_state=cooking_state,
        min_kcal=min_kcal,
        max_kcal=max_kcal,
        limit=limit,
        offset=offset,
    )
    return FoodListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/filters", summary="Danh mục dùng cho bộ lọc")
def filters(db: Session = Depends(get_db)) -> dict:
    return food_service.filter_options(db)


@router.get("/{food_id}", response_model=FoodDetailOut, summary="Chi tiết thực phẩm")
def get_food(food_id: int, db: Session = Depends(get_db)) -> dict:
    data = food_service.get_food_detail(db, food_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thực phẩm.")
    return data


@router.get("/{food_id}/portion", response_model=PortionOut, summary="Tính dinh dưỡng theo khối lượng")
def portion(
    food_id: int,
    weight_g: float = Query(gt=0, le=20000, description="Khối lượng mỗi phần (gam)"),
    quantity: float = Query(default=1.0, gt=0, le=100, description="Số phần"),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return food_service.portion_for_food(db, food_id, weight_g, quantity)
    except FoodServiceError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=exc.message) from exc


@router.post(
    "",
    response_model=FoodOut,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm thực phẩm mới (nhập tay)",
)
def create_food(
    payload: FoodCreateRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        food = food_service.create_food(db, payload.model_dump(), user.id)
    except FoodServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    # trả về kèm thông tin nguồn dữ liệu (truy vết - §6)
    return food_service.get_food_detail(db, food.id)
