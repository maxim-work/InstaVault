from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from .models import CustomUser, UserSettings

@receiver(post_save, sender=CustomUser)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)