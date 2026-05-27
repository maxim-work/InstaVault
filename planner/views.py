from django.shortcuts import render


def day_view(request):
    if request.headers.get('HX-Request'):
        return render(request, 'planner/htmx/day.html')
    return render(request, 'planner/day.html', {'page': 'day'})

def habits_view(request):
    if request.headers.get('HX-Request'):
        return render(request, 'planner/htmx/habits.html')
    return render(request, 'planner/habits.html', {'page': 'habits'})

def calendar_view(request):
    if request.headers.get('HX-Request'):
        return render(request, 'planner/htmx/calendar.html')
    return render(request, 'planner/calendar.html', {'page': 'calendar'})