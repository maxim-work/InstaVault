from __future__ import annotations

import getpass
from argparse import ArgumentParser
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.db import IntegrityError

from instavault.apps.users.models import CustomUser


class Command(BaseCommand):
    help = "Create owner (main superadmin)"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--username", type=str, help="Username for the owner")
        parser.add_argument("--email", type=str, help="Email for the owner")
        parser.add_argument(
            "--password",
            type=str,
            help="Password for the owner (not secure, use with caution)",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Run in non-interactive mode (requires --username and --password)",
        )

    def handle(self, *_args: Any, **options: Any) -> None:
        if CustomUser.objects.filter(is_owner=True).exists():
            self.stdout.write(self.style.ERROR("Owner already exists!"))
            return

        if options["no_input"]:
            self._create_non_interactive(options)
            return

        self._create_interactive()

    def _create_non_interactive(self, options: dict[str, Any]) -> None:
        username = options.get("username")
        password = options.get("password")
        email = options.get("email") or ""

        if not username or not password:
            self.stdout.write(
                self.style.ERROR(
                    "Username and password are required in non-interactive mode"
                )
            )
            return

        try:
            self._create_owner(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f"Owner created successfully: {username}")
            )
        except (IntegrityError, ValidationError, ValueError) as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))

    def _create_interactive(self) -> None:
        self.stdout.write("\nCreate OWNER (main superadmin)\n")

        try:
            username = self._prompt_username()
            email = self._prompt_email()
            password = self._prompt_password()

            self._create_owner(username, email, password)

            self.stdout.write(self.style.SUCCESS(f"\nOwner created: {username}"))
            self.stdout.write(
                self.style.WARNING("\nSave your password in a safe place!")
            )

        except KeyboardInterrupt:
            self.stdout.write("\n\nCreation cancelled")
        except (IntegrityError, ValidationError, ValueError) as e:
            self.stdout.write(self.style.ERROR(f"\nError: {e}"))

    def _prompt_username(self) -> str:
        while True:
            username = input("Username: ").strip()
            if not username:
                self.stdout.write(self.style.ERROR("Username is required!"))
                continue
            if CustomUser.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.ERROR(f"User '{username}' already exists!")
                )
                continue
            return username

    def _prompt_email(self) -> str:
        email = input("Email (optional): ").strip()
        if not email:
            return ""
        try:
            validate_email(email)
        except ValidationError:
            self.stdout.write(
                self.style.WARNING("Invalid email format. Skipping...")
            )
            return ""
        return email

    def _prompt_password(self) -> str:
        while True:
            password = getpass.getpass("Password: ")
            password2 = getpass.getpass("Confirm password: ")

            if not password:
                self.stdout.write(self.style.ERROR("Password is required!"))
                continue
            if password != password2:
                self.stdout.write(self.style.ERROR("Passwords don't match!"))
                continue
            if len(password) < 4:
                self.stdout.write(
                    self.style.ERROR("Password must be at least 4 characters!")
                )
                continue
            return password

    def _create_owner(self, username: str, email: str, password: str) -> None:
        owner = CustomUser.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        owner.is_owner = True
        owner.save()
