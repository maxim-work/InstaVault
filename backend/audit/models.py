from django.db import models
from django.conf import settings
from users.models import CustomUser


class AuditLog(models.Model):
    CATEGORY_CHOICES = [
        ('user', 'Действия пользователя'),
        ('admin', 'Действия администратора'),
        ('system', 'Системное действие')]

    ACTION_CHOICES = [
        ('ban', 'Блокировка'),
        ('unban', 'Разблокировка'),
        ('ownership_transfer', 'Передача прав владельца'),
        ('send_telegram', 'Рассылка в Telegram'),
        ('send_email', 'Рассылка Email'),
        ('appeal_approved', 'Апелляция одобрена'),
        ('appeal_rejected', 'Апелляция отклонена'),
        
        ('login', 'Вход'),
        ('login_failed', 'Неудачный вход'),
        ('logout', 'Выход'),
        ('register', 'Регистрация'),
        ('password_change', 'Смена пароля'),
        ('email_change', 'Смена email'),
        ('name_change', 'Смена имени'),
        ('username_change', 'Смена username'),
        ('telegram_connect', 'Подключение Telegram'),
        ('telegram_disconnect', 'Отключение Telegram'),
        ('avatar_upload', 'Загрузка аватара'),
        ('delete_account', 'Удаление аккаунта'),
        
        ('auto_unban', 'Авторазблокировка'),]


    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='audit_actions')
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='audit_performed')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Лог'
        verbose_name_plural = 'Логи'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['performed_by', '-created_at']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] ({self.category}) -> {self.action} -> {self.details}"