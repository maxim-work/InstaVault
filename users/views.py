from django.shortcuts import render


def register_view(request):
    return render(request, 'users/register.html')

def login_view(request):
    return render(request, 'users/login.html')

def change_password_view(request):
    return render(request, 'users/change_password.html')

def profile_view(request):
    return render(request, 'users/profile.html')