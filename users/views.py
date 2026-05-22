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
from users.forms import LoginForm, RegisterForm
from users.models import CustomUser


def register_view(request):
    if request.user.is_authenticated:
        return redirect('users:profile')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            print('valid')
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            login(request, user)
            return redirect('users:profile')
        else:
            print(form.errors)
            print('not')
            return render(request, 'users/register.html', {'form': form})
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})

def check_username(request):
    username = request.POST.get('username', '')
    if CustomUser.objects.filter(username=username).exists():
        return HttpResponse('<span style="color: #ff4d4d;">Имя занято</span>')
    return HttpResponse('')

def check_email(request):
    email = request.POST.get('email', '')
    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<span style="color: #ff4d4d;">Почта уже зарегистрирована</span>')
    return HttpResponse('')

def send_verification_code(request):
    email = request.POST.get('email', '')
    
    if not email:
        return HttpResponse('<span style="color: #ffb3b3;">Email обязателен</span>')
    
    code = str(random.randint(100000, 999999))
    
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    cache.set(f'verification_code_{email}', code_hash, timeout=180)
    
    print(f'[EMAIL] Код для {email}: {code}')
    
    return HttpResponse('')

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

    if not all([email,password, password_confirm]):
        return JsonResponse({'error': 'Некорректные данные'})
        
    if password != password_confirm:
        return JsonResponse({'error': 'Пароли не совпадают'})

    user = CustomUser.objects.get(email=email)
    user.set_password(password)
    user.save()

    cache.delete(f'reset_code_{email}')

    return JsonResponse({'success': True, 'redirect': reverse('users:login')})

def profile_view(request):
    if request.user.is_authenticated:
        return render(request, 'users/profile.html')

    return redirect('users:login')

@require_POST
def upload_avatar(request):
    if 'avatar' not in request.FILES:
        return JsonResponse({'error': 'Файл не получен'}, status=400)
    
    user = request.user
    
    if user.avatar:
        user.avatar.delete(save=False)
    
    user.avatar = request.FILES['avatar']
    user.save()
    
    return JsonResponse({'success': True})

def update_name(request):
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    
    if not first_name:
        return JsonResponse({'error': 'Имя обязательно'})
    
    request.user.first_name = first_name
    request.user.last_name = last_name
    request.user.save()
    return JsonResponse({'success': True})

def update_username(request):
    username = request.POST.get('username', '').strip()
    
    if CustomUser.objects.filter(username=username).exclude(id=request.user.id).exists():
        return JsonResponse({'error': 'Имя занято'})
    
    request.user.username = username
    request.user.save()
    return JsonResponse({'success': True})

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

def verify_old_email_code(request):
    email = request.POST.get('email', '')
    code = request.POST.get('code', '')
    
    stored_hash = cache.get(f'old_email_code_{request.user.id}')
    
    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк</span>')
    
    if hashlib.sha256(code.encode()).hexdigest() != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')
    
    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')

def send_new_email_code(request):
    email = request.POST.get('email', '')
    
    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<span style="color: #ffb3b3;">Email занят</span>')
    
    code = str(random.randint(100000, 999999))
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    cache.set(f'new_email_code_{request.user.id}', code_hash, timeout=180)
    
    print(f'[EMAIL] Код для нового email {email}: {code}')
    return HttpResponse('')

def verify_new_email_code(request):
    code = request.POST.get('code', '')
    
    stored_hash = cache.get(f'new_email_code_{request.user.id}')
    
    if not stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Код истёк</span>')
    
    if hashlib.sha256(code.encode()).hexdigest() != stored_hash:
        return HttpResponse('<span style="color: #ffb3b3;">Неверный код</span>')
    
    return HttpResponse('<span style="color: #28a745;">Код подтверждён</span>')

def update_email(request):
    email = request.POST.get('email', '').strip()
    
    if not cache.get(f'old_email_code_{request.user.id}'):
        return JsonResponse({'error': 'Сначала подтвердите старый email'})
    
    if not cache.get(f'new_email_code_{request.user.id}'):
        return JsonResponse({'error': 'Сначала подтвердите новый email'})
    
    request.user.email = email
    request.user.save()
    
    cache.delete(f'old_email_code_{request.user.id}')
    cache.delete(f'new_email_code_{request.user.id}')
    
    return JsonResponse({'success': True})

def get_telegram_code(request):
    code = str(random.randint(100000, 999999))
    cache.set(f'telegram_link_{code}', request.user.id, timeout=600)
    return JsonResponse({'code': code, 'bot_link': f'https://t.me/your_bot?start={code}'})

def check_telegram(request):
    return JsonResponse({'connected': bool(request.user.telegram_id)})

def disconnect_telegram(request):
    request.user.telegram_id = None
    request.user.save()
    return JsonResponse({'success': True})

def export_data(request):
    # заглушка позже архив
    data = f"Пользователь: {request.user.username}\nEmail: {request.user.email}\n"
    response = HttpResponse(data, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="my_data.txt"'
    return response

def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    return JsonResponse({'success': True})

def logout_view(request):
    logout(request)
    return redirect('users:login')