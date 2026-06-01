from django.urls import path
from . import views

app_name = 'planner'

urlpatterns = [
    path('day/', views.day_view, name='day'),
    path('day/nav/', views.day_nav, name='day_nav'),
    path('day/note/save/', views.save_note, name='note_save'),
    path('day/task/create/', views.create_task, name='task_create'),
    path('day/task/<int:task_id>/update/', views.update_task, name='task_update'),
    path('day/task/delete/', views.delete_task, name='task_delete'),
    path('day/task/reschedule/', views.reschedule_task, name='task_reschedule'),
    path('day/task/<int:task_id>/toggle/', views.toggle_task, name='task_toggle'),
    path('habits/', views.habits_view, name='habits'),
    path('calendar/', views.calendar_view, name='calendar'),
]