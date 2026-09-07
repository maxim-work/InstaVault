from django import forms
from users.models import CustomUser

class LoginForm(forms.Form):
    identifier = forms.CharField(
        label='Email или имя пользователя',
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'input-field',
            'placeholder': 'your@email.com или username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'input-field',
            'placeholder': 'введите пароль',
            'id': 'password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get('identifier')
        password = cleaned_data.get('password')
        
        if identifier and password:
            
            user = None
            if '@' in identifier:
                try:
                    user = CustomUser.objects.get(email=identifier)
                except CustomUser.DoesNotExist:
                    user = None
            else:
                try:
                    user = CustomUser.objects.get(username=identifier)
                except CustomUser.DoesNotExist:
                    user = None
            
            if user is None or not user.check_password(password):
                raise forms.ValidationError('Неверный email/имя пользователя или пароль')
            
            cleaned_data['user'] = user
        
        return cleaned_data


class RegisterForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя',
        max_length=150,
    )

    email = forms.EmailField(
        label='Электронная почта',
        max_length=250,
    )

    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'input-field',
            'placeholder': 'минимум 8 символов',
            'minlength': '8',
            'id': 'password',
            'style': 'padding-right: 40px;'
        })
    )

    password_confirm = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'input-field',
            'placeholder': 'минимум 8 символов',
            'minlength': '8',
            'id': 'password_confirm',
            'style': 'padding-right: 40px;'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if all([username, email, password, password_confirm]):
            if password != password_confirm:
                self.add_error('password_confirm', 'Пароли не совпадают')
            
            from users.models import CustomUser
            if CustomUser.objects.filter(username=username).exists():
                self.add_error('username', 'Имя уже занято')
            if CustomUser.objects.filter(email=email).exists():
                self.add_error('email', 'Email уже зарегистрирован')
        
        return cleaned_data