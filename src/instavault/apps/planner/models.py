from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils import timezone


class Note(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes")
    date = models.DateField(db_index=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ("-date",)

    def __str__(self) -> str:
        return f"Заметка на {self.date}"


class Task(models.Model):
    class Priority(models.TextChoices):
        URGENT = "urgent", "Срочный"
        IMPORTANT = "important", "Важный"
        NONE = "none", "Без уровня"

    template = models.ForeignKey(
        "TaskTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_tasks",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    date = models.DateField(db_index=True)
    time_start = models.TimeField(blank=True, null=True)
    time_end = models.TimeField(blank=True, null=True)
    priority = models.CharField(max_length=15, choices=Priority.choices, default=Priority.NONE)
    notification_enabled = models.BooleanField(default=False)
    notification_time = models.TimeField(blank=True, null=True)
    completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("date", "time_start", "created_at")
        indexes = (
            models.Index(fields=["user", "date"], name="task_user_date_idx"),
            models.Index(fields=["user", "date", "completed"], name="task_user_date_completed_idx"),
        )

    def __str__(self) -> str:
        return f"Задача на {self.date}"


class TaskTemplate(models.Model):
    class Repeat(models.TextChoices):
        DAILY = "daily", "Ежедневно"
        WEEKLY = "weekly", "Еженедельно"
        WEEKDAYS = "weekdays", "По будням"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_templates")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    time_start = models.TimeField(blank=True, null=True)
    time_end = models.TimeField(blank=True, null=True)
    priority = models.CharField(
        max_length=15, choices=Task.Priority.choices, default=Task.Priority.NONE
    )
    repeat = models.CharField(max_length=15, choices=Repeat.choices)
    notification_enabled = models.BooleanField(default=False)
    notification_time = models.TimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = (
                models.Index(fields=["user", "is_active"], name="task_template_user_active_idx"),
            )

    def __str__(self) -> str:
        return f"Шаблон: {self.title}"

    def is_applicable_on_date(self, target_date: date_type) -> bool:
        if self.repeat == self.Repeat.DAILY:
            return True
        if self.repeat == self.Repeat.WEEKLY:
            return target_date.weekday() == self.created_at.date().weekday()
        if self.repeat == self.Repeat.WEEKDAYS:
            return target_date.weekday() < 5
        return False





class Habit(models.Model):
    class Repeat(models.TextChoices):
        DAILY = "daily", "Ежедневно"
        WEEKLY = "weekly", "Еженедельно"
        WEEKDAYS = "weekdays", "По будням"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
    )
    avatar = models.CharField(max_length=5, default="🏃")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    motivation = models.TextField(blank=True, default="")
    time = models.TimeField(blank=True, null=True)
    repeat = models.CharField(max_length=20, choices=Repeat.choices, default=Repeat.DAILY)
    notification_enabled = models.BooleanField(default=False)
    notification_time = models.TimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    if TYPE_CHECKING:
        from typing import Any # noqa: I001, PLC0415
        completions: Any

    class Meta:
        ordering = ("created_at",)
        indexes = (
            models.Index(fields=["user", "is_active"], name="habit_user_active_idx"),
        )

    def __str__(self) -> str:
        return f"{self.avatar} {self.title}"

    @property
    def current_streak(self) -> int:
        today = timezone.now().date()
        if self.repeat == self.Repeat.DAILY:
            return self._daily_streak(today)
        if self.repeat == self.Repeat.WEEKLY:
            return self._weekly_streak(today)
        if self.repeat == self.Repeat.WEEKDAYS:
            return self._weekdays_streak(today)
        return 0

    @property
    def longest_streak(self) -> int:
        completions = list(
            self.completions.filter(completed=True).order_by("date").values_list("date", flat=True)
        )
        if not completions:
            return 0

        longest = 1
        current = 1
        for i in range(1, len(completions)):
            if self._is_streak_continued(completions[i - 1], completions[i]):
                current += 1
            else:
                current = 1
            longest = max(longest, current)
        return longest

    @property
    def completion_rate(self) -> int:
        today = timezone.now().date()
        days = 30
        start = today - timedelta(days=days - 1)
        done = self.completions.filter(date__gte=start, date__lte=today, completed=True).count()
        return round((done / days) * 100)

    @property
    def is_completed_today(self) -> bool:
        return self.completions.filter(date=timezone.now().date(), completed=True).exists()

    def is_completed_on_date(self, target_date: date_type) -> bool:
        return self.completions.filter(date=target_date, completed=True).exists()

    def is_applicable_on_date(self, target_date: date_type) -> bool:
        if self.repeat == self.Repeat.DAILY:
            return True
        if self.repeat == self.Repeat.WEEKLY:
            return target_date.weekday() == self.created_at.date().weekday()
        if self.repeat == self.Repeat.WEEKDAYS:
            return target_date.weekday() < 5
        return False

    def _daily_streak(self, today: date_type) -> int:
        streak = 0
        check_date = today
        while self.completions.filter(date=check_date, completed=True).exists():
            streak += 1
            check_date -= timedelta(days=1)
        if streak == 0:
            check_date = today - timedelta(days=1)
            while self.completions.filter(date=check_date, completed=True).exists():
                streak += 1
                check_date -= timedelta(days=1)
        return streak

    def _weekly_streak(self, today: date_type) -> int:
        streak = 0
        check_date = today
        while self.completions.filter(date=check_date, completed=True).exists():
            streak += 1
            check_date -= timedelta(days=7)
        if streak == 0:
            check_date = today - timedelta(days=7)
            while self.completions.filter(date=check_date, completed=True).exists():
                streak += 1
                check_date -= timedelta(days=7)
        return streak

    def _weekdays_streak(self, today: date_type) -> int:
        streak = 0
        check_date = today
        while self.completions.filter(date=check_date, completed=True).exists():
            streak += 1
            check_date -= timedelta(days=1)
            while check_date.weekday() >= 5:
                check_date -= timedelta(days=1)
        if streak == 0:
            check_date = today - timedelta(days=1)
            while check_date.weekday() >= 5:
                check_date -= timedelta(days=1)
            while self.completions.filter(date=check_date, completed=True).exists():
                streak += 1
                check_date -= timedelta(days=1)
                while check_date.weekday() >= 5:
                    check_date -= timedelta(days=1)
        return streak

    def _is_streak_continued(self, prev_date: date_type, curr_date: date_type) -> bool:
        delta = (curr_date - prev_date).days

        if self.repeat == self.Repeat.DAILY:
            return delta == 1
        if self.repeat == self.Repeat.WEEKLY:
            return delta == 7
        if self.repeat == self.Repeat.WEEKDAYS:
            return self._is_weekdays_continued(prev_date, curr_date)
        return False

    def _is_weekdays_continued(self, prev_date: date_type, curr_date: date_type) -> bool:
        if (curr_date - prev_date).days > 3:
            return False
        middle = prev_date + timedelta(days=1)
        while middle < curr_date:
            if middle.weekday() < 5:
                return False
            middle += timedelta(days=1)
        return True


class HabitCompletion(models.Model):
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    date = models.DateField(db_index=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-date",)
        constraints = (
            models.UniqueConstraint(
                fields=["habit", "date"],
                name="unique_habit_completion_per_date",
            ),
        )
        indexes = (
            models.Index(
                fields=["habit", "date"],
                name="habit_comp_habit_date_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.habit} — {self.date}"
