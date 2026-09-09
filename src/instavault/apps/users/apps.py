from importlib import import_module

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "instavault.apps.users"
    verbose_name = "Пользователи"

    def ready(self) -> None:
        import_module("instavault.apps.users.signals")
