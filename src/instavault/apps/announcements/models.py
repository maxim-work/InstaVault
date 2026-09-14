# instavault/apps/announcements/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models


class AnnouncementText(models.Model):
    class Category(models.TextChoices):
        GREETING = "greeting", "Приветствие"
        HOLIDAY = "holiday", "Праздник"
        ONBOARDING = "onboarding", "Онбординг"
        MILESTONE = "milestone", "Достижение"

    class Window(models.TextChoices):
        POPUP = "popup", "Всплывающее окно"
        STRING = "string", "Строка на странице"
        MODAL = "modal", "Модалка"

    class Frequency(models.TextChoices):
        ONCE = "once", "Один раз за всё время"
        DAILY = "daily", "Раз в день"
        WEEKLY = "weekly", "Раз в неделю"
        MONTHLY = "monthly", "Раз в месяц"
        YEARLY = "yearly", "Раз в год"
        ON_CONDITION = "condition", "По условию (без периода)"

    code = models.SlugField(max_length=50, unique=True)
    group = models.CharField(max_length=40, db_index=True)
    text = models.TextField(help_text="Поддерживает {name}, {date}, {streak}")
    category = models.CharField(max_length=20, choices=Category.choices)
    window = models.CharField(max_length=20, choices=Window.choices, default=Window.STRING)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.DAILY)
    priority = models.PositiveSmallIntegerField(default=100, help_text="Меньше — важнее")
    condition_key = models.CharField(
        max_length=50,
        blank=True,
        help_text="Имя функции из announcements/conditions.py",
    )
    condition_params = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "code")
        indexes = (models.Index(fields=["active", "priority"]),)

    def __str__(self) -> str:
        return f"[{self.code}] {self.text[:60]}"


class AnnouncementShown(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    group = models.CharField(max_length=40)
    period_key = models.CharField(max_length=20)
    shown_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=["user", "group", "period_key"],
                name="unique_group_per_user_period",
            ),
        )

    def __str__(self) -> str:
        return f"{self.user} ← {self.group} @ {self.period_key}"
