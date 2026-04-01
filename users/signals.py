from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import CustomUser, UserSettings
from django.db import transaction


@receiver(post_save, sender=CustomUser)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: UserSettings.objects.create(user=instance)
        )