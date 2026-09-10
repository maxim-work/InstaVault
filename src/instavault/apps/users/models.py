from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from encrypted_model_fields.fields import EncryptedCharField


def avatar_upload_to(instance: CustomUser, filename: str) -> str:
    user_id = instance.pk or "unknown"
    return f"avatars/{user_id}_{filename}"

class CustomUser(AbstractUser):
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, null=True)
    telegram_id = EncryptedCharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Telegram ID",
    )
    is_owner = models.BooleanField(
        default=False,
        verbose_name="Главный суперадмин",
    )
    started_ban = models.DateTimeField(
        blank=True, null=True, verbose_name="Начало блокировки"
    )
    ended_ban = models.DateTimeField(
        blank=True, null=True, verbose_name="Конец блокировки"
    )
    # Permanent ban: ended_ban is None, started_ban is set
    reason_ban = models.CharField(
        max_length=500, blank=True, verbose_name="Причина блокировки"
    )

    class Meta:  # type: ignore[assignment]
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        indexes = (
            models.Index(fields=["telegram_id"], name="user_telegram_id_idx"),
            models.Index(fields=["is_owner"], name="user_is_owner_idx"),
            models.Index(fields=["is_active"], name="user_is_active_idx"),
            models.Index(fields=["ended_ban"], name="user_ended_ban_idx"),
        )
        ordering = ("-date_joined",)

    def clean(self) -> None:
        super().clean()

        if self.is_owner:
            existing_owner = (
                CustomUser.objects.filter(is_owner=True)
                .exclude(pk=self.pk)
                .first()
            )
            if existing_owner:
                raise ValidationError(
                    {"is_owner": "The main superadmin already exists!"}
                )

            if not self.is_superuser:
                raise ValidationError(
                    {
                        "is_owner": (
                            "The main superadmin must have the status "
                            "of superadmin"
                        )
                    }
                )

            if not self.is_staff:
                raise ValidationError(
                    {
                        "is_owner": (
                            "The chief superadmin must have staff status"
                        )
                    }
                )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_owner:
            self.is_superuser = True
            self.is_staff = True

        if not self.is_owner and self.pk:
            old = CustomUser.objects.filter(pk=self.pk).first()
            if old and old.is_owner:
                raise ValueError(
                    "It is not possible to remove the main superadmin's "
                    "rights. Use the command: "
                    "python manage.py transfer_owner <username>"
                )

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.email:
            return f"{self.username} ({self.email})"
        return self.username

    def should_auto_unban(self) -> bool:
        if self.ended_ban is None:
            return False
        return timezone.now() > self.ended_ban

    def perform_auto_unban(self) -> None:
        self.is_active = True
        self.started_ban = None
        self.ended_ban = None
        self.reason_ban = ""
        self.save()

    def is_banned(self) -> bool:
        return not self.is_active

    def ban(
        self,
        reason: str,
        days: int = 0,
        hours: int = 0,
        is_perm_ban: bool = False,
    ) -> None:
        if not reason and not is_perm_ban:
            raise ValueError("The reason for the ban is not specified")
        if not reason:
            reason = "Permanent ban"

        if not is_perm_ban and days == 0 and hours == 0:
            raise ValueError("Specify the ban duration(days or hours)")

        now = timezone.now()
        if is_perm_ban:
            self.started_ban = now
            self.ended_ban = None
        elif self.is_active:
            self.started_ban = now
            self.ended_ban = now + timedelta(days=days, hours=hours)
        elif self.ended_ban is not None: # Extension of an existing ban
                self.ended_ban = self.ended_ban + timedelta(
                    days=days, hours=hours
                )

        self.is_active = False
        self.reason_ban = reason
        self.save()

    def unban(self, _reason: str = "") -> bool:
        was_banned = not self.is_active
        self.is_active = True
        self.started_ban = None
        self.ended_ban = None
        self.reason_ban = ""
        self.save()
        return was_banned


def default_settings() -> dict[str, Any]:
    return {}


class UserSettings(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name="пользователь",
    )
    settings = models.JSONField(
        default=default_settings,
        blank=True,
        verbose_name="настройки",
    )

    class Meta:
        verbose_name = "Настройки"
        verbose_name_plural = "Настройки"

    def __str__(self) -> str:
        return f"Настройки {self.user.username}"

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default) if self.settings else default

    def set(self, key: str, value: Any) -> None:
        with transaction.atomic():
            settings = UserSettings.objects.select_for_update().get(pk=self.pk)
            if settings.settings is None:
                settings.settings = {}
            settings.settings[key] = value
            settings.save(update_fields=["settings"])
            self.settings = settings.settings


class Appeal(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новое"
        APPROVED = "approved", "Одобрено"
        REJECTED = "rejected", "Отклонено"

    username = models.CharField(max_length=150)
    contact = models.CharField(max_length=255, blank=True)
    message = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=20,
        default=Status.NEW,
        choices=Status.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Апелляция"
        verbose_name_plural = "Апелляции"

    def __str__(self) -> str:
        return f"{self.username} — {self.get_status_display()}"  # type: ignore[attr-defined]
