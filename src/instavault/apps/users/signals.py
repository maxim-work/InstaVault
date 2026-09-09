from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from instavault.apps.users.models import CustomUser, UserSettings


@receiver(post_save, sender=CustomUser)
def create_user_settings(
    sender: type[CustomUser],  # noqa: ARG001
    instance: CustomUser,
    created: bool,
    **_kwargs: Any,
) -> None:
    if created:
        transaction.on_commit(
            lambda: UserSettings.objects.create(user=instance)
        )
