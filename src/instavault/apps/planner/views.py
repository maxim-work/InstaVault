from __future__ import annotations

import calendar
import json
from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone

from instavault.shared.utils import get_user

from .forms import HabitForm, RescheduleTaskForm, TaskForm
from .models import Habit, HabitCompletion, Note, Task, TaskTemplate

if TYPE_CHECKING:
    from instavault.apps.users.models import CustomUser


MONTHS_RU = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
WEEKDAYS_RU = (
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
)
MONTHS_RU_TITLE = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)


def _format_date_ru(target_date: date_type) -> str:
    return (
        f"{target_date.day} "
        f"{MONTHS_RU[target_date.month - 1]}, "
        f"{WEEKDAYS_RU[target_date.weekday()]}"
    )


def _parse_date(date_str: str | None) -> date_type:
    if not date_str:
        return timezone.now().date()
    try:
        return date_type.fromisoformat(date_str)
    except ValueError:
        return timezone.now().date()


def day_get_context(request: HttpRequest, target_date: date_type) -> dict[str, Any]:
    user = get_user(request)
    note = Note.objects.filter(user=user, date=target_date).first()
    tasks = Task.objects.filter(user=user, date=target_date).order_by(
        "time_start", "created_at"
    )

    total = tasks.count()
    completed_count = tasks.filter(completed=True).count()
    productivity = round(completed_count / total * 100) if total > 0 else 0

    return {
        "page": "day",
        "note_content": note.description if note else "",
        "tasks": tasks,
        "current_date": _format_date_ru(target_date),
        "today_iso": target_date.isoformat(),
        "prev_date": (target_date - timedelta(days=1)).isoformat(),
        "next_date": (target_date + timedelta(days=1)).isoformat(),
        "completed": completed_count,
        "total": total,
        "productivity": productivity,
        "urgent": tasks.filter(priority="urgent").count(),
        "important": tasks.filter(priority="important").count(),
        "none": tasks.filter(priority="none").count(),
        "name": user.username,
    }


@login_required
def day_view(request: HttpRequest) -> HttpResponse:
    user = get_user(request)
    today = _parse_date(request.GET.get("date"))

    generate_tasks_from_templates(user, today)

    context = day_get_context(request, today)
    if request.headers.get("HX-Request"):
        return render(request, "planner/htmx/day.html", context)
    return render(request, "planner/day.html", context)


@login_required
def save_note(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_user(request)
    date_str = request.POST.get("date") or timezone.now().date().isoformat()

    Note.objects.update_or_create(
        user=user,
        date=date_str,
        defaults={"description": request.POST.get("description", "")},
    )
    return HttpResponse("")


@login_required
def create_task(request: HttpRequest) -> HttpResponse | JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    form = TaskForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    user = get_user(request)
    editing_id = request.POST.get("editing_task_id")
    task_date = form.cleaned_data["date"]
    repeat = form.cleaned_data.get("repeat", "none")

    if editing_id and editing_id.isdigit():
        _update_task(user, editing_id, form, task_date)
    else:
        template = None
        if repeat != "none":
            template = TaskTemplate.objects.create(
                user=user,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                time_start=form.cleaned_data["time_start"],
                time_end=form.cleaned_data["time_end"],
                priority=form.cleaned_data["priority"],
                repeat=repeat,
                notification_enabled=bool(form.cleaned_data["notification_time"]),
                notification_time=form.cleaned_data["notification_time"],
            )

        Task.objects.create(
            template=template,
            user=user,
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            date=task_date,
            time_start=form.cleaned_data["time_start"],
            time_end=form.cleaned_data["time_end"],
            priority=form.cleaned_data["priority"],
            notification_enabled=bool(form.cleaned_data["notification_time"]),
            notification_time=form.cleaned_data["notification_time"],
        )

    context = day_get_context(request, task_date)
    html = render_to_string("planner/htmx/task_list.html", context, request)
    return HttpResponse(html)


def _update_task(
    user: CustomUser,
    editing_id: str,
    form: TaskForm,
    task_date: date_type,
) -> None:
    task = get_object_or_404(Task, id=int(editing_id), user=user)

    task.title = form.cleaned_data["title"]
    task.description = form.cleaned_data["description"]
    task.time_start = form.cleaned_data["time_start"]
    task.time_end = form.cleaned_data["time_end"]
    task.priority = form.cleaned_data["priority"]
    task.notification_time = form.cleaned_data["notification_time"]
    task.notification_enabled = bool(form.cleaned_data["notification_time"])
    task.date = task_date
    task.save()

    repeat = form.cleaned_data.get("repeat", "none")

    if task.template is not None:
        template = task.template
        template.title = form.cleaned_data["title"]
        template.description = form.cleaned_data["description"]
        template.time_start = form.cleaned_data["time_start"]
        template.time_end = form.cleaned_data["time_end"]
        template.priority = form.cleaned_data["priority"]
        template.notification_time = form.cleaned_data["notification_time"]
        template.notification_enabled = bool(form.cleaned_data["notification_time"])
        template.save()
    elif repeat and repeat != "none":
        task.template = TaskTemplate.objects.create(
            user=user,
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            time_start=form.cleaned_data["time_start"],
            time_end=form.cleaned_data["time_end"],
            priority=form.cleaned_data["priority"],
            repeat=repeat,
            notification_enabled=bool(form.cleaned_data["notification_time"]),
            notification_time=form.cleaned_data["notification_time"],
        )
        task.save()


@login_required
def delete_task(request: HttpRequest) -> HttpResponse | JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_user(request)
    task_id = request.POST.get("task_id")
    delete_mode = request.POST.get("delete_mode", "single")
    task = get_object_or_404(Task, id=task_id, user=user)
    task_date = task.date

    if delete_mode == "all" and task.template is not None:
        Task.objects.filter(template=task.template).delete()
        task.template.delete()
    else:
        task.delete()

    context = day_get_context(request, task_date)
    html = render_to_string("planner/htmx/task_list.html", context, request)
    return HttpResponse(html)


@login_required
def reschedule_task(request: HttpRequest) -> HttpResponse | JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_user(request)
    task_id = request.POST.get("task_id")
    task = get_object_or_404(Task, id=task_id, user=user)
    form = RescheduleTaskForm(request.POST)

    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    old_date = task.date
    task.date = form.cleaned_data["date"]
    task.time_start = form.cleaned_data["time_start"]
    task.time_end = form.cleaned_data["time_end"]
    task.save()

    context = day_get_context(request, old_date)
    html = render_to_string("planner/htmx/task_list.html", context, request)
    return HttpResponse(html)


@login_required
def toggle_task(request: HttpRequest, task_id: int) -> JsonResponse:
    user = get_user(request)
    task = get_object_or_404(Task, id=task_id, user=user)
    task.completed = not task.completed
    task.save()
    return JsonResponse({"status": "ok", "completed": task.completed})


@login_required
def day_nav(request: HttpRequest) -> HttpResponse:
    user = get_user(request)
    today = _parse_date(request.GET.get("date"))

    generate_tasks_from_templates(user, today)

    context = day_get_context(request, today)
    context["page"] = "day"
    return render(request, "planner/htmx/day.html", context)


def generate_tasks_from_templates(user: CustomUser, target_date: date_type) -> None:
    templates = TaskTemplate.objects.filter(user=user, is_active=True)
    for template in templates:
        if not Task.objects.filter(template=template, date=target_date).exists():
            Task.objects.create(
                template=template,
                user=user,
                title=template.title,
                description=template.description,
                date=target_date,
                time_start=template.time_start,
                time_end=template.time_end,
                priority=template.priority,
                notification_enabled=template.notification_enabled,
                notification_time=template.notification_time,
            )


def habit_get_context(
    request: HttpRequest,
    target_date: date_type | None = None,
) -> dict[str, Any]:
    if target_date is None:
        target_date = timezone.now().date()

    user = get_user(request)
    habits = Habit.objects.filter(user=user)
    list_habits: list[Habit] = []

    for habit in habits:
        if habit.repeat == Habit.Repeat.WEEKLY:
            if habit.created_at.weekday() == target_date.weekday():
                list_habits.append(habit)
        elif habit.repeat == Habit.Repeat.WEEKDAYS:
            if target_date.weekday() < 5:
                list_habits.append(habit)
        else:
            list_habits.append(habit)

    for habit in list_habits:
        habit.completed_on_date = habit.is_completed_on_date(target_date)  # type: ignore[attr-defined]

    return {
        "page": "habits",
        "current_date": _format_date_ru(target_date),
        "today_iso": target_date.isoformat(),
        "prev_date": (target_date - timedelta(days=1)).isoformat(),
        "next_date": (target_date + timedelta(days=1)).isoformat(),
        "name": user.username,
        "habits": list_habits,
        "total": len(list_habits),
        "completed": sum(1 for h in list_habits if h.is_completed_today),
        "max_streak": max((h.longest_streak for h in habits), default=0),
    }


@login_required
def habits_view(request: HttpRequest) -> HttpResponse:
    today = _parse_date(request.GET.get("date"))
    context = habit_get_context(request, today)
    if request.headers.get("HX-Request"):
        return render(request, "planner/htmx/habits.html", context)
    return render(request, "planner/habits.html", context)


@login_required
def create_habit(request: HttpRequest) -> HttpResponse | JsonResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    form = HabitForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    user = get_user(request)
    editing_id = request.POST.get("habit_id")

    if editing_id and editing_id.isdigit():
        update_habit(user, int(editing_id), form)
    else:
        Habit.objects.create(
            user=user,
            avatar=form.cleaned_data["avatar"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            motivation=form.cleaned_data["motivation"],
            time=form.cleaned_data["time"],
            repeat=form.cleaned_data["repeat"],
            notification_enabled=bool(form.cleaned_data["notification_time"]),
            notification_time=form.cleaned_data["notification_time"],
        )

    context = habit_get_context(request)
    html = render_to_string("planner/htmx/habits_list.html", context, request)
    return HttpResponse(html)


def update_habit(user: CustomUser, editing_id: int, form: HabitForm) -> None:
    habit = get_object_or_404(Habit, id=editing_id, user=user)

    habit.avatar = form.cleaned_data["avatar"]
    habit.title = form.cleaned_data["title"]
    habit.description = form.cleaned_data["description"]
    habit.motivation = form.cleaned_data["motivation"]
    habit.time = form.cleaned_data["time"]
    habit.repeat = form.cleaned_data["repeat"]
    habit.notification_time = form.cleaned_data["notification_time"]
    habit.notification_enabled = bool(form.cleaned_data["notification_time"])
    habit.save()


@login_required
def delete_habit(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_user(request)
    habit_id = request.POST.get("habit_id")
    habit = get_object_or_404(Habit, id=habit_id, user=user)
    habit.delete()

    context = habit_get_context(request)
    html = render_to_string("planner/htmx/habits_list.html", context, request)
    return HttpResponse(html)


@login_required
def toggle_habit(request: HttpRequest, habit_id: int) -> JsonResponse:
    user = get_user(request)
    habit = get_object_or_404(Habit, id=habit_id, user=user)
    today = timezone.now().date()

    date_str = request.GET.get("date", today.isoformat())
    target_date = _parse_date(date_str)

    if target_date > today:
        return JsonResponse(
            {"status": "error", "message": "Нельзя выполнить наперёд"},
            status=400,
        )

    completion, created = HabitCompletion.objects.get_or_create(
        habit=habit,
        date=target_date,
        defaults={"completed": True, "completed_at": timezone.now()},
    )

    if not created:
        completion.completed = not completion.completed
        completion.completed_at = timezone.now() if completion.completed else None
        completion.save()

    return JsonResponse({"status": "ok", "completed": completion.completed})


def get_day_stats(
    habits: list[Habit],
    task_templates: list[TaskTemplate],
    target_date: date_type,
    tasks_by_day: dict[int, list[Task]],
    completions_by_day: dict[int, set[int]],
) -> tuple[int, int, int, int]:
    day = target_date.day

    applicable_habits = [h for h in habits if h.is_applicable_on_date(target_date)]
    completed_habit_ids = completions_by_day.get(day, set())

    total_habits = len(applicable_habits)
    completed_habits = sum(1 for h in applicable_habits if h.pk in completed_habit_ids)

    applicable_templates = [
        t for t in task_templates if t.is_applicable_on_date(target_date)
    ]
    day_tasks = tasks_by_day.get(day, [])
    custom_tasks = len([t for t in day_tasks if t.template is None])

    total_tasks = len(applicable_templates) + custom_tasks
    completed_tasks = sum(1 for t in day_tasks if t.completed)

    return total_habits, completed_habits, total_tasks, completed_tasks


def load_month_data(
    user: CustomUser,
    year: int,
    month: int,
) -> tuple[dict[int, list[Task]], dict[int, set[int]]]:
    tasks = Task.objects.filter(user=user, date__year=year, date__month=month)
    completions = HabitCompletion.objects.filter(
        habit__user=user,
        habit__is_active=True,
        date__year=year,
        date__month=month,
        completed=True,
    ).values_list("habit_id", "date")

    tasks_by_day: dict[int, list[Task]] = defaultdict(list)
    for task in tasks:
        tasks_by_day[task.date.day].append(task)

    completions_by_day: dict[int, set[int]] = defaultdict(set)
    for habit_id, comp_date in completions:
        completions_by_day[comp_date.day].add(habit_id)

    return tasks_by_day, completions_by_day


def calculate_productivity(total: int, completed: int) -> int:
    return round((completed / total) * 100) if total > 0 else 0


def calendar_get_context(
    request: HttpRequest,
    target_date: date_type | None = None,
) -> dict[str, Any]:
    if target_date is None:
        target_date = timezone.now().date()

    user = get_user(request)
    today = timezone.now().date()

    full_month_days = calendar.monthrange(target_date.year, target_date.month)[1]

    habits = list(Habit.objects.filter(user=user, is_active=True))
    task_templates = list(TaskTemplate.objects.filter(user=user, is_active=True))

    tasks_by_day, completions_by_day = load_month_data(
        user, target_date.year, target_date.month
    )

    chart_data: list[dict[str, int]] = []
    calendar_data: list[dict[str, int]] = []
    best_day: dict[str, Any] | None = None
    best_day_productivity = -1

    for day in range(1, full_month_days + 1):
        current_date = target_date.replace(day=day)
        total_habits, completed_habits, total_tasks, completed_tasks = get_day_stats(
            habits, task_templates, current_date, tasks_by_day, completions_by_day
        )

        total_items = total_habits + total_tasks
        completed_items = completed_habits + completed_tasks

        is_future = (
            target_date.year == today.year
            and target_date.month == today.month
            and day > today.day
        )

        if total_items > 0 and not is_future:
            day_productivity = calculate_productivity(total_items, completed_items)
            if day_productivity > best_day_productivity:
                best_day_productivity = day_productivity
                best_day = {"day": day, "productivity": day_productivity}

        if not is_future:
            chart_data.append(
                {
                    "day": day,
                    "tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "habits": total_habits,
                    "completed_habits": completed_habits,
                }
            )

        calendar_data.append(
            {"day": day, "tasks": total_tasks, "habits": total_habits}
        )

    best_month: dict[str, Any] | None = None
    best_month_productivity = -1

    last_month = today.month if target_date.year == today.year else 12

    for month in range(1, last_month + 1):
        month_tasks, month_completions = load_month_data(user, target_date.year, month)
        max_day = (
            today.day
            if (target_date.year == today.year and month == today.month)
            else calendar.monthrange(target_date.year, month)[1]
        )

        month_total = 0
        month_completed = 0

        for day in range(1, max_day + 1):
            current_date = target_date.replace(
                year=target_date.year, month=month, day=day
            )
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
                    "month": MONTHS_RU_TITLE[month - 1],
                    "productivity": month_productivity,
                }

    return {
        "page": "calendar",
        "chart_data": json.dumps(chart_data),
        "calendar_data": json.dumps(calendar_data),
        "best_day": best_day or {"day": "—", "productivity": 0},
        "best_month": best_month or {"month": "—", "productivity": 0},
    }


@login_required
def calendar_view(request: HttpRequest) -> HttpResponse:
    year = request.GET.get("year")
    month = request.GET.get("month")

    if year and month:
        try:
            target_date = timezone.now().date().replace(
                year=int(year), month=int(month), day=1
            )
        except (ValueError, TypeError):
            target_date = timezone.now().date()
    else:
        target_date = timezone.now().date()

    context = calendar_get_context(request, target_date)

    prev_date = (
        target_date.replace(year=target_date.year - 1, month=12, day=1)
        if target_date.month == 1
        else target_date.replace(month=target_date.month - 1, day=1)
    )
    next_date = (
        target_date.replace(year=target_date.year + 1, month=1, day=1)
        if target_date.month == 12
        else target_date.replace(month=target_date.month + 1, day=1)
    )

    context.update(
        {
            "date": target_date,
            "prev_year": prev_date.year,
            "prev_month": prev_date.month,
            "next_year": next_date.year,
            "next_month": next_date.month,
            "current_date": f"{MONTHS_RU_TITLE[target_date.month - 1]} {target_date.year}",
        }
    )

    template = (
        "planner/htmx/calendar.html"
        if request.headers.get("HX-Request")
        else "planner/calendar.html"
    )
    return render(request, template, context)
