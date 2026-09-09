from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Category(models.TextChoices):
        USER = "user", "Действия пользователя"
        ADMIN = "admin", "Действия администратора"
        SYSTEM = "system", "Системное действие"

    class Action(models.TextChoices):
        BAN = "ban", "Блокировка"
        UNBAN = "unban", "Разблокировка"
        OWNERSHIP_TRANSFER = "ownership_transfer", "Передача прав владельца"
        SEND_TELEGRAM = "send_telegram", "Рассылка в Telegram"
        SEND_EMAIL = "send_email", "Рассылка Email"
        APPEAL_APPROVED = "appeal_approved", "Апелляция одобрена"
        APPEAL_REJECTED = "appeal_rejected", "Апелляция отклонена"
        LOGIN = "login", "Вход"
        LOGIN_FAILED = "login_failed", "Неудачный вход"
        LOGOUT = "logout", "Выход"
        REGISTER = "register", "Регистрация"
        PASSWORD_CHANGE = "password_change", "Смена пароля"
        EMAIL_CHANGE = "email_change", "Смена email"
        NAME_CHANGE = "name_change", "Смена имени"
        USERNAME_CHANGE = "username_change", "Смена username"
        TELEGRAM_CONNECT = "telegram_connect", "Подключение Telegram"
        TELEGRAM_DISCONNECT = "telegram_disconnect", "Отключение Telegram"
        AVATAR_UPLOAD = "avatar_upload", "Загрузка аватара"
        DELETE_ACCOUNT = "delete_account", "Удаление аккаунта"
        AUTO_UNBAN = "auto_unban", "Авторазблокировка"

    category = models.CharField(max_length=10, choices=Category.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_actions",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_performed",
    )
    action = models.CharField(max_length=50, choices=Action.choices)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Лог"
        verbose_name_plural = "Логи"
        indexes = (
            models.Index(fields=["user", "-created_at"], name="audit_user_created_idx"),
            models.Index(
                fields=["performed_by", "-created_at"],
                name="audit_performed_created_idx",
            ),
            models.Index(fields=["action"], name="audit_action_idx"),
        )

    def __str__(self) -> str:
        return (
            f"[{self.created_at:%Y-%m-%d %H:%M}] "
            f"({self.category}) -> {self.action} -> {self.details}"
        )
