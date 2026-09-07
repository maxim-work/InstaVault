from django.shortcuts import render, redirect, get_object_or_404
from .forms import NoteForm, TaskForm, RescheduleTaskForm, HabitForm
from .models import Note, Task, TaskTemplate, Habit, HabitCompletion
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, date
from django.utils import timezone
import calendar
from django.template.loader import render_to_string
import json
from collections import defaultdict


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

def get_day_stats(habits, task_templates, date, tasks_by_day, completions_by_day):
    day = date.day
    
    applicable_habits = [h for h in habits if h.is_applicable_on_date(date)]
    completed_habit_ids = completions_by_day.get(day, set())
    
    total_habits = len(applicable_habits)
    completed_habits = sum(1 for h in applicable_habits if h.id in completed_habit_ids)
    
    applicable_templates = [t for t in task_templates if t.is_applicable_on_date(date)]
    day_tasks = tasks_by_day.get(day, [])
    custom_tasks = len([t for t in day_tasks if not t.template_id])
    
    total_tasks = len(applicable_templates) + custom_tasks
    completed_tasks = sum(1 for t in day_tasks if t.completed)
    
    return total_habits, completed_habits, total_tasks, completed_tasks


def load_month_data(user, year, month):
    tasks = Task.objects.filter(user=user, date__year=year, date__month=month)
    completions = HabitCompletion.objects.filter(
        habit__user=user, habit__is_active=True,
        date__year=year, date__month=month, completed=True
    ).values_list('habit_id', 'date')
    
    tasks_by_day = defaultdict(list)
    for task in tasks:
        tasks_by_day[task.date.day].append(task)
    
    completions_by_day = defaultdict(set)
    for habit_id, comp_date in completions:
        completions_by_day[comp_date.day].add(habit_id)
    
    return tasks_by_day, completions_by_day


def calculate_productivity(total, completed):
    return round((completed / total) * 100) if total > 0 else 0


def calendar_get_context(request, date=None):
    if not date:
        date = timezone.now().date()
    
    today = timezone.now().date()
    is_current_month = date.strftime("%Y-%m") == today.strftime("%Y-%m")
    days = today.day if is_current_month else calendar.monthrange(date.year, date.month)[1]
    full_month_days = calendar.monthrange(date.year, date.month)[1]

    habits = list(Habit.objects.filter(user=request.user, is_active=True))
    task_templates = list(TaskTemplate.objects.filter(user=request.user, is_active=True))
    
    tasks_by_day, completions_by_day = load_month_data(request.user, date.year, date.month)

    chart_data = []
    calendar_data = []
    best_day = None
    best_day_productivity = -1
    
    for day in range(1, full_month_days + 1):
        current_date = date.replace(day=day)
        total_habits, completed_habits, total_tasks, completed_tasks = get_day_stats(
            habits, task_templates, current_date, tasks_by_day, completions_by_day
        )
        
        total_items = total_habits + total_tasks
        completed_items = completed_habits + completed_tasks
        
        is_future = date.year == today.year and date.month == today.month and day > today.day
        
        if total_items > 0 and not is_future:
            day_productivity = calculate_productivity(total_items, completed_items)
            if day_productivity > best_day_productivity:
                best_day_productivity = day_productivity
                best_day = {'day': day, 'productivity': day_productivity}
        
        if not is_future:
            chart_data.append({
                'day': day,
                'tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'habits': total_habits,
                'completed_habits': completed_habits,
            })
        
        calendar_data.append({
            'day': day,
            'tasks': total_tasks,
            'habits': total_habits,
        })

    best_month = None
    best_month_productivity = -1
    months_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    
    last_month = today.month if date.year == today.year else 12
    
    for month in range(1, last_month + 1):
        month_tasks, month_completions = load_month_data(request.user, date.year, month)
        max_day = today.day if (date.year == today.year and month == today.month) else calendar.monthrange(date.year, month)[1]
        
        month_total = month_completed = 0
        
        for day in range(1, max_day + 1):
            current_date = date.replace(year=date.year, month=month, day=day)
            h_total, h_done, t_total, t_done = get_day_stats(
                habits, task_templates, current_date, month_tasks, month_completions
            )
            month_total += h_total + t_total
            month_completed += h_done + t_done
        
        if month_total > 0:
            month_productivity = calculate_productivity(month_total, month_completed)
            if month_productivity > best_month_productivity:
                best_month_productivity = month_productivity
                best_month = {
                    'month': months_names[month - 1],
                    'productivity': month_productivity
                }

    return {
        'page': 'calendar',
        'chart_data': json.dumps(chart_data),
        'calendar_data': json.dumps(calendar_data),
        'best_day': best_day or {'day': '—', 'productivity': 0},
        'best_month': best_month or {'month': '—', 'productivity': 0},
    }


def calendar_view(request):
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            date = timezone.now().date().replace(year=int(year), month=int(month), day=1)
        except (ValueError, TypeError):
            date = timezone.now().date()
    else:
        date = timezone.now().date()
    
    context = calendar_get_context(request, date)
    
    prev_date = date.replace(year=date.year - 1, month=12, day=1) if date.month == 1 else date.replace(month=date.month - 1, day=1)
    next_date = date.replace(year=date.year + 1, month=1, day=1) if date.month == 12 else date.replace(month=date.month + 1, day=1)
    
    months = ['января','февраля','марта','апреля','мая','июня',
              'июля','августа','сентября','октября','ноября','декабря']
    
    context.update({
        'date': date,
        'prev_year': prev_date.year,
        'prev_month': prev_date.month,
        'next_year': next_date.year,
        'next_month': next_date.month,
        'current_date': f"{months[date.month-1].capitalize()} {date.year}",
    })
    
    template = 'planner/htmx/calendar.html' if request.headers.get('HX-Request') else 'planner/calendar.html'
    return render(request, template, context)