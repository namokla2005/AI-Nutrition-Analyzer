"""Quy đổi thời gian giữa UTC (cách lưu trong DB) và giờ địa phương (cách hiển thị).

TD-08: toàn bộ DB lưu UTC dạng naive. Mọi thống kê theo NGÀY phải đi qua module này,
không được tự cộng trừ giờ rải rác trong code nghiệp vụ.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.core.config import settings


def offset() -> timedelta:
    return timedelta(hours=settings.timezone_offset_hours)


def utc_to_local(dt: datetime) -> datetime:
    """UTC naive -> giờ địa phương naive."""
    return dt + offset()


def local_to_utc(dt: datetime) -> datetime:
    """Giờ địa phương naive -> UTC naive."""
    return dt - offset()


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    """Khoảng [đầu ngày, đầu ngày kế tiếp) theo giờ địa phương, quy về UTC.

    Dùng để truy vấn `eaten_at >= start AND eaten_at < end`.
    """
    start_local = datetime.combine(day, time.min)
    start_utc = local_to_utc(start_local)
    return start_utc, start_utc + timedelta(days=1)


def local_today() -> date:
    return utc_to_local(datetime.utcnow()).date()


def local_date_of(dt: datetime) -> date:
    """Ngày (giờ địa phương) của một mốc thời gian UTC."""
    return utc_to_local(dt).date()


def local_week_bounds(any_day: date) -> tuple[date, date]:
    """Tuần tính từ Thứ Hai đến Chủ Nhật."""
    start = any_day - timedelta(days=any_day.weekday())
    return start, start + timedelta(days=6)


def date_range(start: date, end: date) -> list[date]:
    if end < start:
        return []
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]
