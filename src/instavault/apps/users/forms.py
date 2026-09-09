from __future__ import annotations

from typing import Any

from django import forms

from instavault.apps.users.models import CustomUser


class LoginForm(forms.Form):
    identifier = forms.CharField(
        label="Email или имя пользователя",
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "your@email.com или username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-field",
                "placeholder": "введите пароль",
                "id": "password",
            }
        ),
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}

        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")

        if identifier and password:
            user = self._find_user(identifier)
            if user is None or not user.check_password(password):
                raise forms.ValidationError(
                    "Неверный email/имя пользователя или пароль"
                )
            cleaned_data["user"] = user

        return cleaned_data

    @staticmethod
    def _find_user(identifier: str) -> CustomUser | None:
        field = "email" if "@" in identifier else "username"
        try:
            return CustomUser.objects.get(**{field: identifier})
        except CustomUser.DoesNotExist:
            return None


class RegisterForm(forms.Form):
    username = forms.CharField(
        label="Имя пользователя",
        max_length=150,
    )

    email = forms.EmailField(
        label="Электронная почта",
        max_length=250,
    )

    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-field",
                "placeholder": "минимум 8 символов",
                "minlength": "8",
                "id": "password",
                "style": "padding-right: 40px;",
            }
        ),
    )

    password_confirm = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-field",
                "placeholder": "минимум 8 символов",
                "minlength": "8",
                "id": "password_confirm",
                "style": "padding-right: 40px;",
            }
        ),
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}

        username = cleaned_data.get("username")
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if not all([username, email, password, password_confirm]):
            return cleaned_data

        if password != password_confirm:
            self.add_error("password_confirm", "Пароли не совпадают")

        if CustomUser.objects.filter(username=username).exists():
            self.add_error("username", "Имя уже занято")

        if CustomUser.objects.filter(email=email).exists():
            self.add_error("email", "Email уже зарегистрирован")

        return cleaned_data
