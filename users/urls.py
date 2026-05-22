from django.urls import path
from . import views
from .admin import confirm_ownership_transfer, send_telegram_message_view, send_email_message_view, ban_operation_view
from django.contrib.admin.views.decorators import staff_member_required

app_name = 'users'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/upload_avatar/', views.upload_avatar, name='upload_avatar'),
    path('profile/update_name/', views.update_name, name='update_name'),
    path('profile/update_username/', views.update_username, name='update_username'),
    path('profile/send_old_email_code/', views.send_old_email_code, name='send_old_email_code'),
    path('profile/verify_old_email_code/', views.verify_old_email_code, name='verify_old_email_code'),
    path('profile/send_new_email_code/', views.send_new_email_code, name='send_new_email_code'),
    path('profile/verify_new_email_code/', views.verify_new_email_code, name='verify_new_email_code'),
    path('profile/update_email/', views.update_email, name='update_email'),
    path('profile/get-telegram-code/', views.get_telegram_code, name='get_telegram_code'),
    path('profile/check_telegram/', views.check_telegram, name='check_telegram'),
    path('profile/disconnect_telegram/', views.disconnect_telegram, name='disconnect_telegram'),
    path('profile/export_data/', views.export_data, name='export_data'),
    path('profile/delete_account/', views.delete_account, name='delete_account'),
    path('register/', views.register_view, name='register'),
    path('register/check_username/', views.check_username, name='check_username'),
    path('register/check_email/', views.check_email, name='check_email'),
    path('register/send-code/', views.send_verification_code, name='send_code'),
    path('register/verify-code/', views.verify_code, name='verify_code'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change_password/', views.change_password_view, name='change_password'),
    path('change_password/send_reset_code/', views.send_reset_code, name='send_reset_code'),
    path('change_password/verify_reset_code/', views.verify_reset_code, name='verify_reset_code'),
    path('change_password/reset_password/', views.reset_password, name='reset_password'),
    path('admin/confirm-ownership-transfer/', staff_member_required(confirm_ownership_transfer), name='confirm_ownership_transfer'),
    path('admin/send-telegram-message/', staff_member_required(send_telegram_message_view), name='send_telegram_message'),
    path('admin/send-email-message/', staff_member_required(send_email_message_view), name='send_email_message'),
    path('admin/ban-operation/', staff_member_required(ban_operation_view), name='ban_operation'),
]