# ruff: noqa: ARG001
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.utils import timezone

if TYPE_CHECKING:
    from instavault.apps.users.models import CustomUser


def always(user: CustomUser, **params: Any) -> bool:
    return True


def on_date(user: CustomUser, *, day: int, month: int, **params: Any) -> bool:
    now = timezone.localtime()
    return now.day == day and now.month == month


def in_time_range(
    user: CustomUser,
    *,
    from_hour: int,
    to_hour: int,
    **params: Any,
) -> bool:
    hour = timezone.localtime().hour
    if from_hour <= to_hour:
        return from_hour <= hour < to_hour
    return hour >= from_hour or hour < to_hour


def first_day_after_signup(
    user: CustomUser,
    *,
    days: int = 1,
    **params: Any,
) -> bool:
    signup_date = timezone.localtime(user.date_joined).date()
    today = timezone.localdate()
    return (today - signup_date).days == days


def has_streak_at_least(
    user: CustomUser,
    *,
    min_days: int = 7,
    **params: Any,
) -> bool:
    from instavault.apps.planner.models import Habit  # noqa: PLC0415

    for habit in Habit.objects.filter(user=user, is_active=True):
        if habit.current_streak >= min_days:
            return True
    return False


def is_birthday(user: CustomUser, **params: Any) -> bool:
    return False


CONDITIONS: dict[str, Callable[..., bool]] = {
    "always": always,
    "on_date": on_date,
    "in_time_range": in_time_range,
    "first_day_after_signup": first_day_after_signup,
    "has_streak_at_least": has_streak_at_least,
    "is_birthday": is_birthday,
}


def evaluate(
    condition_key: str,
    user: CustomUser,
    params: dict[str, Any] | None = None,
) -> bool:
    if not condition_key:
        return True
    func = CONDITIONS.get(condition_key)
    if func is None:
        return False
    try:
        return bool(func(user, **(params or {})))
    except TypeError:
        return False
