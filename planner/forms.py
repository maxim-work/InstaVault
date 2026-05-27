from django import forms


class NoteForm(forms.Form):
    description = forms.CharField(
        label='Заметка дня',
        widget=forms.Textarea(attrs={
            'id': 'dailyNote',
            'placeholder': 'Напишите заметку на день...',
            'rows': 2,
        })
    )


class TaskForm(forms.Form):
    title = forms.CharField(
        label='Название',
        widget=forms.TextInput(attrs={
            'id': 'taskTitle',
            'class': 'modal-input',
            'placeholder': 'Название задачи',
            'autofocus': True,
        })
    )

    description = forms.CharField(
        label='Описание',
        required=False,
        widget=forms.Textarea(attrs={
            'id': 'taskDescription',
            'class': 'modal-input modal-textarea',
            'placeholder': 'Описание (необязательно)',
            'rows': 3,
        })
    )

    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={
            'id': 'taskDate',
            'class': 'modal-input',
            'type': 'date',
        })
    )

    time_start = forms.TimeField(
        label='Начало',
        required=False,
        widget=forms.TimeInput(attrs={
            'id': 'taskTimeStart',
            'class': 'modal-input',
            'placeholder': 'Начало',
            'type': 'time',
            'value': '09:00',
        })
    )

    time_end = forms.TimeField(
        label='Конец',
        required=False,
        widget=forms.TimeInput(attrs={
            'id': 'taskTimeEnd',
            'class': 'modal-input',
            'placeholder': 'Конец',
            'type': 'time',
        })
    )

    notification_time = forms.TimeField(
        label='Время уведомления',
        required=False,
        widget=forms.TimeInput(attrs={
            'id': 'taskNotificationTime',
            'class': 'modal-input',
            'placeholder': 'Время уведомления',
            'type': 'time',
            'value': '09:00',
        })
    )

    priority = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'priorityValue'}),
        initial='none',
    )

    repeat = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'repeatValue'}),
        initial='none',
    )

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError('Название обязательно')
        if len(title) > 100:
            raise forms.ValidationError('Название не должно превышать 100 символов')
        return title

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if not date:
            raise forms.ValidationError('Дата обязательна')
        return date

    def clean_priority(self):
        priority = self.cleaned_data.get('priority')
        valid = ['none', 'urgent', 'important']
        if priority not in valid:
            raise forms.ValidationError('Некорректный приоритет')
        return priority

    def clean_repeat(self):
        repeat = self.cleaned_data.get('repeat')
        valid = ['none', 'daily', 'weekly', 'weekdays']
        if repeat not in valid:
            raise forms.ValidationError('Некорректный повтор')
        return repeat

    def clean(self):
        cleaned_data = super().clean()
        time_start = cleaned_data.get('time_start')
        time_end = cleaned_data.get('time_end')

        if time_end and not time_start:
            self.add_error('time_start', 'Укажите время начала')
        
        if time_start and time_end and time_start >= time_end:
            self.add_error('time_end', 'Конец должен быть позже начала')

        return cleaned_data


class RescheduleTaskForm(forms.Form):
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={
            'id': 'rescheduleDate',
            'class': 'modal-input',
            'type': 'date',
        })
    )

    time_start = forms.TimeField(
        label='Начало',
        required=False,
        widget=forms.TimeInput(attrs={
            'id': 'rescheduleTimeStart',
            'class': 'modal-input',
            'placeholder': 'Начало',
            'type': 'time',
        })
    )

    time_end = forms.TimeField(
        label='Конец',
        required=False,
        widget=forms.TimeInput(attrs={
            'id': 'rescheduleTimeEnd',
            'class': 'modal-input',
            'placeholder': 'Конец',
            'type': 'time',
        })
    )

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if not date:
            raise forms.ValidationError('Дата обязательна')
        return date