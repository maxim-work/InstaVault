from django.shortcuts import render


def register_view(request):
    if request.headers.get('HX-Request'):
        return render(request, 'users/htmx_page/register.html')
    return render(request, 'users/register.html')


def login_view(request):
    if request.headers.get('HX-Request'):
        return render(request, 'users/htmx_page/login.html')
    return render(request, 'users/login.html')

def change_password_view(request):
    if request.headers.get('HX-Request'):
        return render(request, 'users/htmx_page/change_password.html')
    return render(request, 'users/change_password.html')

def profile_view(request):
    return render(request, 'users/profile.html')