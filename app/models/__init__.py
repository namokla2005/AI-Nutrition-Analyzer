"""Export toàn bộ model để Alembic autogenerate nhìn thấy đủ metadata."""
from app.models.base import Base, TimestampMixin
from app.models.chat import ChatMessage, ChatSession
from app.models.food import (
    COOKING_STATES,
    Food,
    FoodAlias,
    FoodImage,
    FoodNutrient,
    FoodSource,
    Nutrient,
)
from app.models.meal import MEAL_TYPES, Meal, MealItem
from app.models.ml import ModelVersion, Prediction
from app.models.user import User, UserProfile

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserProfile",
    "FoodSource",
    "Food",
    "Nutrient",
    "FoodNutrient",
    "FoodAlias",
    "FoodImage",
    "Meal",
    "MealItem",
    "ModelVersion",
    "Prediction",
    "ChatSession",
    "ChatMessage",
    "MEAL_TYPES",
    "COOKING_STATES",
]
