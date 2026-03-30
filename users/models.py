from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    telegram_id = models.BigIntegerField(unique=True, blank=True, null=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        if self.email:
            return f"{self.username} ({self.email})"
        return self.username
    

def default_settings():
    return {}
    

class UserSettings(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='settings')
    settings = models.JSONField(default=default_settings)

    class Meta:
        verbose_name = 'Настройки'
        verbose_name_plural = 'Настройки'

    def __str__(self):
        return f'Настройки {self.user.username}'
    
    def get(self, key, default=None):
        if self.settings is None:
            self.settings = {}
            self.save(update_fields=['settings'])
        return self.settings.get(key, default)

    def set(self, key, value):
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value
        self.save(update_fields=['settings'])