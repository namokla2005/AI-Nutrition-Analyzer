"""Các endpoint /api/v1."""
from fastapi import APIRouter

from app.api.v1 import assistant, auth, foods, meals, plan, predict, statistics, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(foods.router)
api_router.include_router(meals.router)
api_router.include_router(statistics.router)
api_router.include_router(predict.router)
api_router.include_router(assistant.router)
api_router.include_router(plan.router)

__all__ = ["api_router"]
