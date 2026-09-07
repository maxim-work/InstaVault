from django.db import models
from django.utils import timezone
from datetime import timedelta
from users.models import CustomUser


class Note(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notes')
    date = models.DateField(db_index=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']


class Task(models.Model):
    class Priority(models.TextChoices):
        URGENT = 'urgent', 'Срочный'
        IMPORTANT = 'important', 'Важный'
        NONE = 'none', 'Без уровня'

    template = models.ForeignKey('TaskTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_tasks')
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    date = models.DateField(db_index=True)
    time_start = models.TimeField(blank=True, null=True)
    time_end = models.TimeField(blank=True, null=True)
    priority = models.CharField(max_length=15, choices=Priority.choices, default=Priority.NONE)
    notification_enabled = models.BooleanField(default=False)
    notification_time = models.TimeField(blank=True, null=True)
    completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time_start', 'created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'date', 'completed']),
        ]


class TaskTemplate(models.Model):
    class Repeat(models.TextChoices):
        DAILY = 'daily', 'Ежедневно'
        WEEKLY = 'weekly', 'Еженедельно'
        WEEKDAYS = 'weekdays', 'По будням'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='task_templates')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    time_start = models.TimeField(blank=True, null=True)
    time_end = models.TimeField(blank=True, null=True)
    priority = models.CharField(max_length=15, choices=Task.Priority.choices, default=Task.Priority.NONE)
    repeat = models.CharField(max_length=15, choices=Repeat.choices)
    notification_enabled = models.BooleanField(default=False)
    notification_time = models.TimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def is_applicable_on_date(self, date):
        if self.repeat == self.Repeat.DAILY:
            return True
        elif self.repeat == self.Repeat.WEEKLY:
            return date.weekday() == self.created_at.date().weekday()
        elif self.repeat == self.Repeat.WEEKDAYS:
            return date.weekday() < 5
        return False


class Habit(models.Model):
    class Repeat(models.TextChoices):
        DAILY = 'daily', 'Ежедневно'
        WEEKLY = 'weekly', 'Еженедельно'
        WEEKDAYS = 'weekdays', 'По будням'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='habits')
    avatar = models.CharField(max_length=5, default='🏃')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    motivation = models.TextField(blank=True, default='')
    time = models.TimeField(blank=True, null=True)
    repeat = models.CharField(max_length=20, choices=Repeat.choices, default=Repeat.DAILY)
    notification_enabled = models.BooleanField(default=False)
    notification_time = models.TimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    @property
    def current_streak(self):
        today = timezone.now().date()
        streak = 0
        
        if self.repeat == 'daily':
            check_date = today
            while self.completions.filter(date=check_date, completed=True).exists():
                streak += 1
                check_date -= timedelta(days=1)
            if streak == 0:
                check_date = today - timedelta(days=1)
                while self.completions.filter(date=check_date, completed=True).exists():
                    streak += 1
                    check_date -= timedelta(days=1)
                    
        elif self.repeat == 'weekly':
            check_date = today
            while self.completions.filter(date=check_date, completed=True).exists():
                streak += 1
                check_date -= timedelta(days=7)
            if streak == 0:
                check_date = today - timedelta(days=7)
                while self.completions.filter(date=check_date, completed=True).exists():
                    streak += 1
                    check_date -= timedelta(days=7)
                    
        elif self.repeat == 'weekdays':
            check_date = today
            while self.completions.filter(date=check_date, completed=True).exists():
                streak += 1
                check_date -= timedelta(days=1)
                while check_date.weekday() >= 5:
                    check_date -= timedelta(days=1)
            if streak == 0:
                check_date = today - timedelta(days=1)
                while check_date.weekday() >= 5:
                    check_date -= timedelta(days=1)
                while self.completions.filter(date=check_date, completed=True).exists():
                    streak += 1
                    check_date -= timedelta(days=1)
                    while check_date.weekday() >= 5:
                        check_date -= timedelta(days=1)
        
        return streak


    @property
    def longest_streak(self):
        completions = list(
            self.completions.filter(completed=True)
            .order_by('date')
            .values_list('date', flat=True)
        )
        if not completions:
            return 0
        
        if self.repeat == 'daily':
            step = timedelta(days=1)
        elif self.repeat == 'weekly':
            step = timedelta(days=7)
        elif self.repeat == 'weekdays':
            step = None
        
        longest = 1
        current = 1
        
        for i in range(1, len(completions)):
            delta = (completions[i] - completions[i-1]).days
            
            if self.repeat == 'daily' and delta == 1:
                current += 1
            elif self.repeat == 'weekly' and delta == 7:
                current += 1
            elif self.repeat == 'weekdays' and delta <= 3:
                middle = completions[i-1] + timedelta(days=1)
                only_weekends = True
                while middle < completions[i]:
                    if middle.weekday() < 5:
                        only_weekends = False
                        break
                    middle += timedelta(days=1)
                if only_weekends:
                    current += 1
                else:
                    current = 1
            else:
                current = 1
            
            longest = max(longest, current)
        
        return longest

    @property
    def completion_rate(self):
        today = timezone.now().date()
        days = 30
        start = today - timedelta(days=days - 1)
        done = self.completions.filter(date__gte=start, date__lte=today, completed=True).count()
        return round((done / days) * 100)

    def is_completed_on_date(self, date):
        return self.completions.filter(date=date, completed=True).exists()

    @property
    def is_completed_today(self):
        return self.completions.filter(date=timezone.now().date(), completed=True).exists()

    def is_applicable_on_date(self, date):
        if self.repeat == self.Repeat.DAILY:
            return True
        elif self.repeat == self.Repeat.WEEKLY:
            return date.weekday() == self.created_at.date().weekday()
        elif self.repeat == self.Repeat.WEEKDAYS:
            return date.weekday() < 5
        return False


class HabitCompletion(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='completions')
    date = models.DateField(db_index=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ['habit', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['habit', 'date']),
        ]