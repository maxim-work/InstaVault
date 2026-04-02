from django.urls import path
from . import views
from .admin import confirm_ownership_transfer, send_telegram_message_view, send_email_message_view
from django.contrib.admin.views.decorators import staff_member_required

app_name = 'users'

urlpatterns = [
    path('profile', views.profile_view, name='profile'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('change_password/', views.change_password_view, name='change_password'),
    path('admin/confirm-ownership-transfer/', confirm_ownership_transfer, name='confirm_ownership_transfer'),
    path('admin/send-telegram-message/', staff_member_required(send_telegram_message_view), name='send_telegram_message'),
    path('admin/send-email-message/', staff_member_required(send_email_message_view), name='send_email_message'),
]