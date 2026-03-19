from django.urls import path
from . import views

app_name = 'landing'

urlpatterns = [
    path('profile', views.profile_view, name='profile'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('change_password/', views.change_password_view, name='change_password'),
]