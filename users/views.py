import hashlib
import random
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from users.forms import LoginForm, RegisterForm
from users.models import CustomUser, Appeal
from audit.utils import log_action


def register_view(request):
    if request.user.is_authenticated:
        return redirect('users:profile')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            login(request, user)
            log_action(
                user=user,
                performed_by=user,
                action='register',
                category='user',
                request=request
            )
            return redirect('users:profile')
        else:
            return render(request, 'users/register.html', {'form': form})
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})

@require_POST
def check_username(request):
    username = request.POST.get('username', '')
    if CustomUser.objects.filter(username=username).exists():
        return HttpResponse('<span style="color: #ff4d4d;">Имя занято</span>')
    return HttpResponse('')

@require_POST
def check_email(request):
    email = request.POST.get('email', '')
    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<span style="color: #ff4d4d;">Почта уже зарегистрирована</span>')
    return HttpResponse('')

@require_POST
def send_verification_code(request):
    email = request.POST.get('email', '')
    
    if not email:
        return HttpResponse('<span style="color: #ffb3b3;">Email обязателен</span>')
    
    code = str(random.randint(100000, 999999))
    
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    cache.set(f'verification_code_{email}', code_hash, timeout=180)
    
    print(f'[EMAIL] Код для {email}: {code}')
    
    return HttpResponse('')

@require_POST
def verify_code(request):
    email = request.POST.get('email', '')
    code = request.POST.get('code', '')
    
    if not email or not code:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')
    
    stored_hash = cache.get(f'verification_code_{email}')
    
    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк, запросите новый</span>')
    
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    if code_hash != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')
    
    cache.delete(f'verification_code_{email}')
    
    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('users:profile')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            log_action(
                user=user,
                performed_by=user,
                action='login',
                category='user',
                request=request
            )
            return redirect('users:profile')
        else:
            if request.headers.get('HX-Request'):
                errors_html = ''
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == '__all__' or field is None:
                            errors_html += f'<div class="error-message">{error}</div>'
                        else:
                            errors_html += f'<div class="error-message" id="{field}-error">{error}</div>'
                return render(request, 'users/partials/login_errors.html', {'errors_html': errors_html})
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})

def change_password_view(request):
    return render(request, 'users/change_password.html')

@require_POST
def send_reset_code(request):
    email = request.POST.get('email', '')
    
    if not email:
        return HttpResponse('<span style="color: #ffb3b3;">Email обязателен</span>')

    if not CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<span style="color: #ffb3b3;">Вы не зарегистрированы</span>')
    
    code = str(random.randint(100000, 999999))
    
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    cache.set(f'reset_code_{email}', code_hash, timeout=180)
    
    print(f'[EMAIL] Код для {email}: {code}')
    
    return HttpResponse('')

@require_POST
def verify_reset_code(request):
    email = request.POST.get('email', '')
    code = request.POST.get('code', '')
    
    if not email or not code:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')

    if not CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<span style="color: #ffb3b3;">Вы не зарегистрированы</span>')
    
    stored_hash = cache.get(f'reset_code_{email}')
    
    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк, запросите новый</span>')
    
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    if code_hash != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')
    
    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')

def reset_password(request):
    email = request.POST.get('email', '')
    password = request.POST.get('password', '')
    password_confirm = request.POST.get('password_confirm', '')

    if not all([email, password, password_confirm]):
        return JsonResponse({'error': 'Некорректные данные'})
        
    if password != password_confirm:
        return JsonResponse({'error': 'Пароли не совпадают'})

    user = CustomUser.objects.get(email=email)
    user.set_password(password)
    user.save()

    cache.delete(f'reset_code_{email}')
    
    log_action(
        user=user,
        performed_by=user,
        action='password_change',
        category='user',
        request=request
    )

    return JsonResponse({'success': True, 'redirect': reverse('users:login')})

def profile_view(request):
    if request.user.is_authenticated:
        return render(request, 'users/profile.html')

    return redirect('users:login')

@login_required
@require_POST
def upload_avatar(request):
    if 'avatar' not in request.FILES:
        return JsonResponse({'error': 'Файл не получен'}, status=400)
    
    user = request.user
    
    if user.avatar:
        user.avatar.delete(save=False)
    
    user.avatar = request.FILES['avatar']
    user.save()
    
    log_action(
        user=user,
        performed_by=user,
        action='avatar_upload',
        category='user',
        request=request
    )
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def update_name(request):
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    
    if not first_name:
        return JsonResponse({'error': 'Имя обязательно'})
    
    old_full_name = request.user.get_full_name()
    request.user.first_name = first_name
    request.user.last_name = last_name
    request.user.save()
    
    log_action(
        user=request.user,
        performed_by=request.user,
        action='name_change',
        category='user',
        details=f'Name changed from "{old_full_name}" to "{first_name} {last_name}"',
        request=request
    )
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def update_username(request):
    username = request.POST.get('username', '').strip()
    
    if CustomUser.objects.filter(username=username).exclude(id=request.user.id).exists():
        return JsonResponse({'error': 'Имя занято'})
    
    old_username = request.user.username
    request.user.username = username
    request.user.save()
    
    log_action(
        user=request.user,
        performed_by=request.user,
        action='username_change',
        category='user',
        details=f'Changed from {old_username} to {username}',
        request=request
    )
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def send_old_email_code(request):
    user = request.user
    
    code = str(random.randint(100000, 999999))
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    cache.set(f'old_email_code_{user.id}', code_hash, timeout=180)
    
    if user.telegram_id:
        print(f'[TELEGRAM] Код для {user.telegram_id}: {code}')
    else:
        print(f'[EMAIL] Код для {user.email}: {code}')
    
    return HttpResponse('')

@login_required
@require_POST
def verify_old_email_code(request):
    email = request.POST.get('email', '')
    code = request.POST.get('code', '')
    
    stored_hash = cache.get(f'old_email_code_{request.user.id}')
    
    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк</span>')
    
    if hashlib.sha256(code.encode()).hexdigest() != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')
    
    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')

@login_required
@require_POST
def send_new_email_code(request):
    email = request.POST.get('email', '')
    
    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<span style="color: #ffb3b3;">Email занят</span>')
    
    code = str(random.randint(100000, 999999))
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    cache.set(f'new_email_code_{request.user.id}', code_hash, timeout=180)
    
    print(f'[EMAIL] Код для нового email {email}: {code}')
    return HttpResponse('')

@login_required
@require_POST
def verify_new_email_code(request):
    code = request.POST.get('code', '')
    
    stored_hash = cache.get(f'new_email_code_{request.user.id}')
    
    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк</span>')
    
    if hashlib.sha256(code.encode()).hexdigest() != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')
    
    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')

@login_required
@require_POST
def update_email(request):
    email = request.POST.get('email', '').strip()
    
    if not cache.get(f'old_email_code_{request.user.id}'):
        return JsonResponse({'error': 'Сначала подтвердите старый email'})
    
    if not cache.get(f'new_email_code_{request.user.id}'):
        return JsonResponse({'error': 'Сначала подтвердите новый email'})
    
    old_email = request.user.email
    request.user.email = email
    request.user.save()
    
    cache.delete(f'old_email_code_{request.user.id}')
    cache.delete(f'new_email_code_{request.user.id}')
    
    log_action(
        user=request.user,
        performed_by=request.user,
        action='email_change',
        category='user',
        details=f'Changed from {old_email} to {email}',
        request=request
    )
    
    return JsonResponse({'success': True})

@login_required
def get_telegram_code(request):
    code = str(random.randint(100000, 999999))
    cache.set(f'telegram_link_{code}', request.user.id, timeout=600)
    return JsonResponse({'code': code, 'bot_link': f'https://t.me/your_bot?start={code}'})

@login_required
def check_telegram(request):
    return JsonResponse({'connected': bool(request.user.telegram_id)})

@login_required
@require_POST
def disconnect_telegram(request):
    request.user.telegram_id = None
    request.user.save()
    
    log_action(
        user=request.user,
        performed_by=request.user,
        action='telegram_disconnect',
        category='user',
        request=request
    )
    
    return JsonResponse({'success': True})

@login_required
def export_data(request):
    # заглушка позже архив
    data = f"Пользователь: {request.user.username}\nEmail: {request.user.email}\n"
    response = HttpResponse(data, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="my_data.txt"'
    return response

@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    log_action(
        user=user,
        performed_by=user,
        action='delete_account',
        category='user',
        request=request
    )
    return JsonResponse({'success': True})

def logout_view(request):
    if request.user.is_authenticated:
        log_action(
            user=request.user,
            performed_by=request.user,
            action='logout',
            category='user',
            request=request
        )
    logout(request)
    return redirect('users:login')

def appeal(request):
    return render(request, 'users/ban_appeal.html')

@require_POST
def check_appeal_username(request):
    username = request.POST.get('username', '')
    exists = CustomUser.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})

@require_POST
def submit_appeal(request):
    username = request.POST.get('username', '')
    contact = request.POST.get('contact', '')
    message = request.POST.get('message', '')

    if all([username, message]):
        Appeal.objects.create(
            username=username,
            contact=contact,
            message=message)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Данные введены не корректно!'})




