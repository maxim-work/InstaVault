from django.shortcuts import render, redirect, get_object_or_404
from .forms import NoteForm, TaskForm, RescheduleTaskForm, HabitForm
from .models import Note, Task, TaskTemplate, Habit, HabitCompletion
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.template.loader import render_to_string


def day_get_context(request, date):
    note = Note.objects.filter(user=request.user, date=date).first()
    tasks = Task.objects.filter(user=request.user, date=date).order_by('time_start', 'created_at')
    
    total = tasks.count()
    completed_count = tasks.filter(completed=True).count()
    productivity = round(completed_count / total * 100) if total > 0 else 0

    return {
        'page': 'day',
        'note_content': note.description if note else '',
        'tasks': tasks,
        'current_date': f"{date.day} {['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][date.month-1]}, {['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье'][date.weekday()]}",
        'today_iso': date.isoformat(),
        'prev_date': (date - timedelta(days=1)).isoformat(),
        'next_date': (date + timedelta(days=1)).isoformat(),
        'completed': completed_count,
        'total': total,
        'productivity': productivity,
        'urgent': tasks.filter(priority='urgent').count(),
        'important': tasks.filter(priority='important').count(),
        'none': tasks.filter(priority='none').count(),
        'name': request.user.username,
    }

@login_required
def day_view(request):
    date_str = request.GET.get('date')
    if date_str:
        today = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        today = timezone.now().date()

    generate_tasks_from_templates(request.user, today)
    
    context = day_get_context(request, today)
    if request.headers.get('HX-Request'):
        return render(request, 'planner/htmx/day.html', context)
    return render(request, 'planner/day.html', context)

@login_required
def save_note(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        if not date_str:
            date_str = timezone.now().date().isoformat()
        
        note, created = Note.objects.update_or_create(
            user=request.user,
            date=date_str,
            defaults={'description': request.POST.get('description', '')}
        )
        return HttpResponse('')
    return HttpResponse('')

@login_required
def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            editing_id = request.POST.get('editing_task_id')
            date = form.cleaned_data['date']
            repeat = form.cleaned_data.get('repeat', 'none')
            
            if editing_id and editing_id.isdigit():
                update_task(request, editing_id, form, date)
            else:
                template = None
                if repeat != 'none':
                    template = TaskTemplate.objects.create(
                        user=request.user,
                        title=form.cleaned_data['title'],
                        description=form.cleaned_data['description'],
                        time_start=form.cleaned_data['time_start'],
                        time_end=form.cleaned_data['time_end'],
                        priority=form.cleaned_data['priority'],
                        repeat=repeat,
                        notification_enabled=bool(form.cleaned_data['notification_time']),
                        notification_time=form.cleaned_data['notification_time'],
                    )
                
                Task.objects.create(
                    template=template,
                    user=request.user,
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data['description'],
                    date=date,
                    time_start=form.cleaned_data['time_start'],
                    time_end=form.cleaned_data['time_end'],
                    priority=form.cleaned_data['priority'],
                    notification_enabled=bool(form.cleaned_data['notification_time']),
                    notification_time=form.cleaned_data['notification_time'],
                )
            
            context = day_get_context(request, date)
            html = render_to_string('planner/htmx/task_list.html', context, request)
            return HttpResponse(html)
        return JsonResponse({'errors': form.errors}, status=400)

@login_required
def update_task(request, editing_id, form, date):
    task = get_object_or_404(Task, id=int(editing_id), user=request.user)
    fields = ['title', 'description', 'time_start', 'time_end', 'priority', 'notification_time']
    for field in fields:
        setattr(task, field, form.cleaned_data[field])
    task.date = date
    task.notification_enabled = bool(form.cleaned_data['notification_time'])
    task.save()

    if task.template:
        for field in fields:
            setattr(task.template, field, form.cleaned_data[field])
        task.template.notification_enabled = bool(form.cleaned_data['notification_time'])
        task.template.save()
    elif form.cleaned_data.get('repeat'):
        task.template = TaskTemplate.objects.create(
            user=request.user,
            repeat=form.cleaned_data['repeat'],
            **{f: form.cleaned_data[f] for f in fields},
            notification_enabled=bool(form.cleaned_data['notification_time']),
        )
        task.save()

@login_required
def delete_task(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        delete_mode = request.POST.get('delete_mode', 'single')
        task = get_object_or_404(Task, id=task_id, user=request.user)
        date = task.date
        
        if delete_mode == 'all' and task.template:
            Task.objects.filter(template=task.template).delete()
            task.template.delete()
        else:
            task.delete()
        
        context = day_get_context(request, date)
        html = render_to_string('planner/htmx/task_list.html', context, request)
        return HttpResponse(html)

@login_required
def reschedule_task(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        task = get_object_or_404(Task, id=task_id, user=request.user)
        form = RescheduleTaskForm(request.POST)
        if form.is_valid():
            old_date = task.date
            task.date = form.cleaned_data['date']
            task.time_start = form.cleaned_data['time_start']
            task.time_end = form.cleaned_data['time_end']
            task.save()
            
            context = day_get_context(request, old_date)
            html = render_to_string('planner/htmx/task_list.html', context, request)
            return HttpResponse(html)
        return JsonResponse({'errors': form.errors}, status=400)

@login_required
def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.completed = not task.completed
    task.save()
    return JsonResponse({'status': 'ok', 'completed': task.completed})

@login_required
def day_nav(request):
    date_str = request.GET.get('date')
    if date_str:
        today = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        today = timezone.now().date()

    generate_tasks_from_templates(request.user, today)
    
    context = day_get_context(request, today)
    return render(request, 'planner/htmx/day.html', {**{'page': 'day'}, **context})

def generate_tasks_from_templates(user, date):
    templates = TaskTemplate.objects.filter(user=user, is_active=True)
    for template in templates:
        if not Task.objects.filter(template=template, date=date).exists():
            Task.objects.create(
                template=template,
                user=user,
                title=template.title,
                description=template.description,
                date=date,
                time_start=template.time_start,
                time_end=template.time_end,
                priority=template.priority,
                notification_enabled=template.notification_enabled,
                notification_time=template.notification_time,
            )

def habit_get_context(request, date=None):
    if date == None:
        date = timezone.now().date()
    habits = Habit.objects.filter(user=request.user)
    list_habits = []
    for habit in habits:
        if habit.repeat == 'weekly':
            if habit.created_at.weekday() == date.weekday():
                list_habits.append(habit)

        elif habit.repeat == 'weekdays':
            if date.weekday() < 5:
                list_habits.append(habit)
        else:
            list_habits.append(habit)

    for habit in list_habits:
        habit.completed_on_date = habit.is_completed_on_date(date)

    return {
        'page': 'habits',
        'current_date': f"{date.day} {['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][date.month-1]}, {['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье'][date.weekday()]}",
        'today_iso': date.isoformat(),
        'prev_date': (date - timedelta(days=1)).isoformat(),
        'next_date': (date + timedelta(days=1)).isoformat(),
        'name': request.user.username,
        'habits': list_habits,
        'total': len(list_habits),
        'completed': sum(1 for h in list_habits if h.is_completed_today),
        'max_streak': max((h.longest_streak for h in habits), default=0),
    }

@login_required
def habits_view(request):
    date_str = request.GET.get('date')
    if date_str:
        today = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        today = timezone.now().date()
    context = habit_get_context(request, today)
    if request.headers.get('HX-Request'):
        return render(request, 'planner/htmx/habits.html', context)
    return render(request, 'planner/habits.html', context)

@login_required
def create_habit(request):
    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            editing_id = request.POST.get('habit_id')
            if editing_id and editing_id.isdigit():
                update_habit(request, int(editing_id), form)
            else:
                Habit.objects.create(
                    user=request.user,
                    avatar=form.cleaned_data['avatar'],
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data['description'],
                    motivation=form.cleaned_data['motivation'],
                    time=form.cleaned_data['time'],
                    repeat=form.cleaned_data['repeat'],
                    notification_enabled=bool(form.cleaned_data['notification_time']),
                    notification_time=form.cleaned_data['notification_time'],
                    )
            context = habit_get_context(request)
            html = render_to_string('planner/htmx/habits_list.html', context, request)
            return HttpResponse(html)
        return JsonResponse({'errors': form.errors}, status=400)

@login_required
def update_habit(request, editing_id, form):
    habit = get_object_or_404(Habit, id=int(editing_id), user=request.user)
    fields = ['avatar', 'title', 'description', 'motivation', 'time', 'repeat', 'notification_time']
    for field in fields:
        setattr(habit, field, form.cleaned_data[field])
    habit.notification_enabled = bool(form.cleaned_data['notification_time'])
    habit.save()

@login_required
def delete_habit(request):
    if request.method == 'POST':
        habit_id = request.POST.get('habit_id')
        habit = get_object_or_404(Habit, id=habit_id, user=request.user)
        habit.delete()
        
        context = habit_get_context(request)
        html = render_to_string('planner/htmx/habits_list.html', context, request)
        return HttpResponse(html)

@login_required
def toggle_habit(request, habit_id):
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    today = timezone.now().date()
    date_str = request.GET.get('date', today.isoformat())
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    if date > today:
        return JsonResponse({'status': 'error', 'message': 'Нельзя выполнить наперёд'}, status=400)
    
    completion, created = HabitCompletion.objects.get_or_create(
        habit=habit,
        date=date,
        defaults={'completed': True, 'completed_at': timezone.now()}
    )
    
    if not created:
        completion.completed = not completion.completed
        completion.completed_at = timezone.now() if completion.completed else None
        completion.save()
    
    return JsonResponse({'status': 'ok', 'completed': completion.completed})

@login_required
def calendar_view(request):
    if request.headers.get('HX-Request'):
        return render(request, 'planner/htmx/calendar.html', {'page': 'calendar'})
    return render(request, 'planner/calendar.html', {'page': 'calendar'})