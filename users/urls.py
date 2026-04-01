from django.urls import path
from . import views
from .admin import confirm_ownership_transfer

app_name = 'users'

urlpatterns = [
    path('profile', views.profile_view, name='profile'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('change_password/', views.change_password_view, name='change_password'),
    path('admin/confirm-ownership-transfer/', confirm_ownership_transfer, name='confirm_ownership_transfer'),
]