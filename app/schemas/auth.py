"""Pydantic schemas cho xác thực và tài khoản."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MIN_PASSWORD_LENGTH, validate_password_strength


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError(" ".join(errors))
        return v

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return v.strip() or None if v is not None else None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError(" ".join(errors))
        return v


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    confirm: str = Field(description="Gõ chính xác DELETE để xác nhận xóa tài khoản")


class ProfileIn(BaseModel):
    gender: str | None = Field(default=None, pattern="^(male|female|other)$")
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    height_cm: float | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=10, le=400)
    activity_level: str | None = Field(
        default=None, pattern="^(sedentary|light|moderate|active|very_active)$"
    )
    goal: str | None = Field(default=None, pattern="^(lose|maintain|gain)$")
    daily_kcal_target: float | None = Field(default=None, ge=500, le=8000)
    note: str | None = Field(default=None, max_length=500)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gender: str | None = None
    birth_year: int | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    activity_level: str | None = None
    goal: str | None = None
    daily_kcal_target: float | None = None
    note: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserDetailOut(UserOut):
    profile: ProfileOut | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    profile: ProfileIn | None = None


class MessageOut(BaseModel):
    detail: str
