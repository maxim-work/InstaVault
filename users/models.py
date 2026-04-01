from django.db import models
from django.contrib.auth.models import AbstractUser
from encrypted_model_fields.fields import EncryptedCharField
from django.core.exceptions import ValidationError
from django.db import transaction


class CustomUser(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    telegram_id = EncryptedCharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Telegram ID"
    )
    is_owner = models.BooleanField(
        default=False,
        verbose_name="Главный суперадмин",
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['is_owner']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-date_joined']

    def clean(self):
        super().clean()
        
        if self.is_owner:
            existing_owner = CustomUser.objects.filter(is_owner=True).exclude(pk=self.pk).first()
            if existing_owner:
                raise ValidationError({
                    'is_owner': f'The main superadmin already exists!'
                })
        
        if self.is_owner and not self.is_superuser:
            raise ValidationError({
                'is_owner': 'The main superadmin must have the status of superadmin'
            })
        
        if self.is_owner and not self.is_staff:
            raise ValidationError({
                'is_owner': 'The chief superadmin must have staff status'
            })

    def save(self, *args, **kwargs):
        if self.is_owner:
            self.is_superuser = True
            self.is_staff = True
        
        self.full_clean()
        
        if not self.is_owner and self.pk:
            old = CustomUser.objects.filter(pk=self.pk).first()
            if old and old.is_owner:
                raise ValueError(
                    "It is not possible to remove the main superadmin's rights."
                    'Use the command: python manage.py transfer_owner <username>'
                )
        
        super().save(*args, **kwargs)

    def __str__(self):
        if self.email:
            return f"{self.username} ({self.email})"
        return self.username


def default_settings():
    return {}


class UserSettings(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='settings', verbose_name="пользователь")
    settings = models.JSONField(default=default_settings, blank=True, verbose_name="настройки")

    class Meta:
        verbose_name = 'Настройки'
        verbose_name_plural = 'Настройки'

    def __str__(self):
        return f'Настройки {self.user.username}'
    
    def get(self, key, default=None):
        with transaction.atomic():
            if self.settings is None:
                settings = UserSettings.objects.select_for_update().get(pk=self.pk)
                if settings.settings is None:
                    settings.settings = {}
                    settings.save(update_fields=['settings'])
                    self.settings = settings.settings
                else:
                    self.settings = settings.settings
        return self.settings.get(key, default)

    def set(self, key, value):
        with transaction.atomic():
            settings = UserSettings.objects.select_for_update().get(pk=self.pk)
            if settings.settings is None:
                settings.settings = {}
            settings.settings[key] = value
            settings.save(update_fields=['settings'])
            self.settings = settings.settings