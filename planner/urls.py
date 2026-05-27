from django.urls import path
from . import views

app_name = 'planner'

urlpatterns = [
    path('day/', views.day_view, name='day'),
    path('habits/', views.habits_view, name='habits'),
    path('calendar/', views.calendar_view, name='calendar'),
]