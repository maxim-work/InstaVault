from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from instavault.apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Создает тестовых пользователей"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Количество обычных пользователей",
        )
        parser.add_argument(
            "--admins",
            type=int,
            default=3,
            help="Количество администраторов",
        )

    def handle(self, *_args: Any, **options: Any) -> None:
        count = options["count"]
        admins_count = options["admins"]

        group, group_created = Group.objects.get_or_create(
            name="Менеджеры пользователей"
        )

        if group_created:
            content_type = ContentType.objects.get_for_model(CustomUser)
            permissions = Permission.objects.filter(
                content_type=content_type,
                codename__in=[
                    "view_customuser",
                    "add_customuser",
                    "change_customuser",
                    "delete_customuser",
                ],
            )
            group.permissions.set(permissions)
            self.stdout.write(
                self.style.SUCCESS(
                    'Создана группа "Менеджеры пользователей" с правами'
                )
            )

        if not CustomUser.objects.filter(is_owner=True).exists():
            owner = CustomUser.objects.create_superuser(
                username="owner",
                password="owner123",  # noqa: S106
                email="owner@example.com",
            )
            owner.is_owner = True
            owner.save()
            self.stdout.write(
                self.style.SUCCESS("Создан владелец: owner / owner123")
            )

        for i in range(admins_count):
            username = f"admin{i + 1}"
            if not CustomUser.objects.filter(username=username).exists():
                admin = CustomUser.objects.create_user(
                    username=username,
                    password="admin123",  # noqa: S106
                    email=f"{username}@example.com",
                )
                admin.is_staff = True
                admin.save()
                admin.groups.add(group)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Создан администратор: {username} / admin123"
                    )
                )

        for i in range(count):
            username = f"user{i + 1}"
            if not CustomUser.objects.filter(username=username).exists():
                CustomUser.objects.create_user(
                    username=username,
                    password="user123",  # noqa: S106
                    email=f"{username}@example.com",
                    telegram_id=f"12345678{i + 1}",
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Создан пользователь: {username} / user123")
                )

        stats = {
            "owners": CustomUser.objects.filter(is_owner=True).count(),
            "admins": CustomUser.objects.filter(
                is_staff=True, is_superuser=False
            ).count(),
            "users": CustomUser.objects.filter(
                is_staff=False, is_superuser=False
            ).count(),
        }

        self.stdout.write(self.style.SUCCESS("\nСтатистика:"))
        self.stdout.write(f"   Владельцев: {stats['owners']}")
        self.stdout.write(f"   Администраторов: {stats['admins']}")
        self.stdout.write(f"   Пользователей: {stats['users']}")
        self.stdout.write(f"   Всего: {sum(stats.values())}")
