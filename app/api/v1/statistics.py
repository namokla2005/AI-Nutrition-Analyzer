"""API thống kê dinh dưỡng theo ngày / tuần / tháng."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_user
from app.models import User
from app.schemas.meal import DailyStatsOut, PeriodStatsOut
from app.services import statistics_service

router = APIRouter(prefix="/statistics", tags=["statistics"])


def _target(user: User) -> float | None:
    profile = user.profile
    return profile.daily_kcal_target if profile else None


@router.get("/daily", response_model=DailyStatsOut, summary="Thống kê một ngày")
def daily(
    day: date | None = Query(default=None, description="Bỏ trống = hôm nay (giờ địa phương)"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    db.refresh(user)
    return statistics_service.daily(db, user.id, day, _target(user))


@router.get("/weekly", response_model=PeriodStatsOut, summary="Thống kê theo tuần")
def weekly(
    any_day: date | None = Query(default=None, description="Một ngày bất kỳ trong tuần cần xem"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    db.refresh(user)
    return statistics_service.weekly(db, user.id, any_day, _target(user))


@router.get("/monthly", response_model=PeriodStatsOut, summary="Thống kê theo tháng")
def monthly(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    db.refresh(user)
    return statistics_service.monthly(db, user.id, year, month, _target(user))
