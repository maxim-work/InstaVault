from __future__ import annotations

import hashlib
import secrets

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from instavault.apps.audit.utils import log_action
from instavault.apps.users.forms import LoginForm, RegisterForm
from instavault.apps.users.models import Appeal, CustomUser
from instavault.shared.utils import get_user


def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method != "POST":
        form = RegisterForm()
        return render(request, "users/register.html", {"form": form})

    form = RegisterForm(request.POST)
    if not form.is_valid():
        return render(request, "users/register.html", {"form": form})

    username = form.cleaned_data["username"]
    email = form.cleaned_data["email"]
    password = form.cleaned_data["password"]

    user = CustomUser.objects.create_user(
        username=username, email=email, password=password
    )
    login(request, user)
    log_action(
        user=user,
        performed_by=user,
        action="register",
        category="user",
        request=request,
    )
    return redirect("users:profile")


@require_POST
def check_username(request: HttpRequest) -> HttpResponse:
    username = request.POST.get("username", "")
    if CustomUser.objects.filter(username=username).exists():
        return HttpResponse('<span style="color: #ff4d4d;">Имя занято</span>')
    return HttpResponse("")


@require_POST
def check_email(request: HttpRequest) -> HttpResponse:
    email = request.POST.get("email", "")
    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse(
            '<span style="color: #ff4d4d;">Почта уже зарегистрирована</span>'
        )
    return HttpResponse("")


@require_POST
def send_verification_code(request: HttpRequest) -> HttpResponse:
    email = request.POST.get("email", "")

    if not email:
        return HttpResponse('<span style="color: #ffb3b3;">Email обязателен</span>')

    code = str(secrets.randbelow(900000) + 100000)
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    cache.set(f"verification_code_{email}", code_hash, timeout=180)

    print(f"[EMAIL] Код для {email}: {code}")

    return HttpResponse("")


@require_POST
def verify_code(request: HttpRequest) -> HttpResponse:
    email = request.POST.get("email", "")
    code = request.POST.get("code", "")

    if not email or not code:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')

    stored_hash = cache.get(f"verification_code_{email}")

    if not stored_hash:
        return HttpResponse(
            '<span style="color: #ffb3b3;">Код истёк, запросите новый</span>'
        )

    code_hash = hashlib.sha256(code.encode()).hexdigest()

    if code_hash != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')

    cache.delete(f"verification_code_{email}")
    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method != "POST":
        form = LoginForm()
        return render(request, "users/login.html", {"form": form})

    form = LoginForm(request.POST)

    if form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user)
        log_action(
            user=user,
            performed_by=user,
            action="login",
            category="user",
            request=request,
        )
        return redirect("users:profile")

    if request.headers.get("HX-Request"):
        errors_html = ""
        for field, errors in form.errors.items():
            for error in errors:
                if field in ("__all__", None):
                    errors_html += f'<div class="error-message">{error}</div>'
                else:
                    errors_html += (
                        f'<div class="error-message" '
                        f'id="{field}-error">{error}</div>'
                    )
        return render(
            request,
            "users/partials/login_errors.html",
            {"errors_html": errors_html},
        )

    return render(request, "users/login.html", {"form": form})


def change_password_view(request: HttpRequest) -> HttpResponse:
    return render(request, "users/change_password.html")


@require_POST
def send_reset_code(request: HttpRequest) -> HttpResponse:
    email = request.POST.get("email", "")

    if not email:
        return HttpResponse('<span style="color: #ffb3b3;">Email обязателен</span>')

    if not CustomUser.objects.filter(email=email).exists():
        return HttpResponse(
            '<span style="color: #ffb3b3;">Вы не зарегистрированы</span>'
        )

    code = str(secrets.randbelow(900000) + 100000)
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    cache.set(f"reset_code_{email}", code_hash, timeout=180)

    print(f"[EMAIL] Код для {email}: {code}")

    return HttpResponse("")


@require_POST
def verify_reset_code(request: HttpRequest) -> HttpResponse:
    email = request.POST.get("email", "")
    code = request.POST.get("code", "")

    if not email or not code:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')

    if not CustomUser.objects.filter(email=email).exists():
        return HttpResponse(
            '<span style="color: #ffb3b3;">Вы не зарегистрированы</span>'
        )

    stored_hash = cache.get(f"reset_code_{email}")

    if not stored_hash:
        return HttpResponse(
            '<span style="color: #ffb3b3;">Код истёк, запросите новый</span>'
        )

    code_hash = hashlib.sha256(code.encode()).hexdigest()

    if code_hash != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')

    cache.set(f"reset_code_verified_{email}", value=True, timeout=600)

    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')


@require_POST
def reset_password(request: HttpRequest) -> JsonResponse:
    email = request.POST.get("email", "")
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")

    if not all([email, password, password_confirm]):
        return JsonResponse({"error": "Некорректные данные"})

    if password != password_confirm:
        return JsonResponse({"error": "Пароли не совпадают"})

    if not cache.get(f"reset_code_verified_{email}"):
        return JsonResponse(
            {"error": "Сначала подтвердите код из письма"}
        )

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return JsonResponse({"error": "Пользователь не найден"})

    user.set_password(password)
    user.save()

    cache.delete(f"reset_code_{email}")
    cache.delete(f"reset_code_verified_{email}")

    log_action(
        user=user,
        performed_by=user,
        action="password_change",
        category="user",
        request=request,
    )

    return JsonResponse({"success": True, "redirect": reverse("users:login")})


def profile_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return render(request, "users/profile.html")
    return redirect("users:login")


@login_required
@require_POST
def upload_avatar(request: HttpRequest) -> JsonResponse:
    if "avatar" not in request.FILES:
        return JsonResponse({"error": "Файл не получен"}, status=400)

    user = get_user(request)

    if user.avatar:
        user.avatar.delete(save=False)

    user.avatar = request.FILES["avatar"]
    user.save()

    log_action(
        user=user,
        performed_by=user,
        action="avatar_upload",
        category="user",
        request=request,
    )

    return JsonResponse({"success": True})


@login_required
@require_POST
def update_name(request: HttpRequest) -> JsonResponse:
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()

    if not first_name:
        return JsonResponse({"error": "Имя обязательно"})

    user = get_user(request)
    old_full_name = user.get_full_name()
    user.first_name = first_name
    user.last_name = last_name
    user.save()

    log_action(
        user=user,
        performed_by=user,
        action="name_change",
        category="user",
        details=f'Name changed from "{old_full_name}" to "{first_name} {last_name}"',
        request=request,
    )

    return JsonResponse({"success": True})


@login_required
@require_POST
def update_username(request: HttpRequest) -> JsonResponse:
    username = request.POST.get("username", "").strip()
    user = get_user(request)

    if CustomUser.objects.filter(username=username).exclude(pk=user.pk).exists():
        return JsonResponse({"error": "Имя занято"})

    old_username = user.username
    user.username = username
    user.save()

    log_action(
        user=user,
        performed_by=user,
        action="username_change",
        category="user",
        details=f"Changed from {old_username} to {username}",
        request=request,
    )

    return JsonResponse({"success": True})


@login_required
@require_POST
def send_old_email_code(request: HttpRequest) -> HttpResponse:
    user = get_user(request)

    code = str(secrets.randbelow(900000) + 100000)
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    cache.set(f"old_email_code_{user.pk}", code_hash, timeout=180)

    if user.telegram_id:
        print(f"[TELEGRAM] Код для {user.telegram_id}: {code}")
    else:
        print(f"[EMAIL] Код для {user.email}: {code}")

    return HttpResponse("")


@login_required
@require_POST
def verify_old_email_code(request: HttpRequest) -> HttpResponse:
    user = get_user(request)
    code = request.POST.get("code", "")

    stored_hash = cache.get(f"old_email_code_{user.pk}")

    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк</span>')

    if hashlib.sha256(code.encode()).hexdigest() != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')

    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')


@login_required
@require_POST
def send_new_email_code(request: HttpRequest) -> HttpResponse:
    user = get_user(request)
    email = request.POST.get("email", "")

    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<span style="color: #ffb3b3;">Email занят</span>')

    code = str(secrets.randbelow(900000) + 100000)
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    cache.set(f"new_email_code_{user.pk}", code_hash, timeout=180)

    print(f"[EMAIL] Код для нового email {email}: {code}")
    return HttpResponse("")


@login_required
@require_POST
def verify_new_email_code(request: HttpRequest) -> HttpResponse:
    user = get_user(request)
    code = request.POST.get("code", "")

    stored_hash = cache.get(f"new_email_code_{user.pk}")

    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк</span>')

    if hashlib.sha256(code.encode()).hexdigest() != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')

    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')


@login_required
@require_POST
def update_email(request: HttpRequest) -> JsonResponse:
    user = get_user(request)
    email = request.POST.get("email", "").strip()

    if not cache.get(f"old_email_code_{user.pk}"):
        return JsonResponse({"error": "Сначала подтвердите старый email"})

    if not cache.get(f"new_email_code_{user.pk}"):
        return JsonResponse({"error": "Сначала подтвердите новый email"})

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "Некорректный email"})

    if CustomUser.objects.filter(email=email).exclude(pk=user.pk).exists():
        return JsonResponse({"error": "Этот email уже занят"})

    old_email = user.email
    user.email = email
    user.save()

    cache.delete(f"old_email_code_{user.pk}")
    cache.delete(f"new_email_code_{user.pk}")

    log_action(
        user=user,
        performed_by=user,
        action="email_change",
        category="user",
        details=f"Changed from {old_email} to {email}",
        request=request,
    )

    return JsonResponse({"success": True})


@login_required
def get_telegram_code(request: HttpRequest) -> JsonResponse:
    user = get_user(request)
    code = str(secrets.randbelow(900000) + 100000)
    cache.set(f"telegram_link_{code}", user.pk, timeout=600)
    return JsonResponse(
        {"code": code, "bot_link": f"https://t.me/your_bot?start={code}"}
    )


@login_required
def check_telegram(request: HttpRequest) -> JsonResponse:
    user = get_user(request)
    return JsonResponse({"connected": bool(user.telegram_id)})


@login_required
@require_POST
def disconnect_telegram(request: HttpRequest) -> JsonResponse:
    user = get_user(request)
    user.telegram_id = None
    user.save()

    log_action(
        user=user,
        performed_by=user,
        action="telegram_disconnect",
        category="user",
        request=request,
    )

    return JsonResponse({"success": True})


@login_required
def export_data(request: HttpRequest) -> HttpResponse:
    user = get_user(request)
    data = f"Пользователь: {user.username}\nEmail: {user.email}\n"
    response = HttpResponse(data, content_type="text/plain")
    response["Content-Disposition"] = 'attachment; filename="my_data.txt"'
    return response


@login_required
@require_POST
def delete_account(request: HttpRequest) -> JsonResponse:
    user = get_user(request)
    logout(request)
    user.delete()
    log_action(
        user=user,
        performed_by=user,
        action="delete_account",
        category="user",
        request=request,
    )
    return JsonResponse({"success": True})


def logout_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        user = get_user(request)
        log_action(
            user=user,
            performed_by=user,
            action="logout",
            category="user",
            request=request,
        )
    logout(request)
    return redirect("users:login")


def appeal(request: HttpRequest) -> HttpResponse:
    return render(request, "users/ban_appeal.html")


@require_POST
def check_appeal_username(request: HttpRequest) -> JsonResponse:
    username = request.POST.get("username", "")
    exists = CustomUser.objects.filter(username=username).exists()
    return JsonResponse({"exists": exists})


@require_POST
def submit_appeal(request: HttpRequest) -> JsonResponse:
    username = request.POST.get("username", "")
    contact = request.POST.get("contact", "")
    message = request.POST.get("message", "")

    if all([username, message]):
        Appeal.objects.create(username=username, contact=contact, message=message)
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Данные введены не корректно!"})
