from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser, UserSettings
from django.contrib.auth.models import Group
from django.contrib.admin import DateFieldListFilter
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages


class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False
    extra = 0
    max_num = 1
    min_num = 1
    verbose_name = "Настройки"
    verbose_name_plural = "Настройки"

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ('settings',)
        return ()
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    search_fields = ('username', 'email')

    actions = ['transfer_owner']

    def transfer_owner(self, request, queryset):
        if not request.user.is_owner:
            self.message_user(
                request,
                "Только владелец может передавать права владельца",
                level='ERROR'
            )
            return
        
        if queryset.count() != 1:
            self.message_user(
                request,
                "Выберите ровно одного пользователя для передачи прав владельца",
                level='ERROR'
            )
            return
        
        new_owner = queryset.first()
        current_owner = CustomUser.objects.filter(is_owner=True).first()
        
        if new_owner == current_owner:
            self.message_user(
                request,
                f"Пользователь {new_owner.username} уже является владельцем",
                level='ERROR'
            )
            return
        
        if not new_owner.is_superuser or not new_owner.is_staff:
            self.message_user(
                request,
                "Новый владелец должен иметь права суперадмина и staff",
                level='ERROR'
            )
            return
        
        request.session['pending_ownership_transfer'] = {
            'new_owner_id': new_owner.id,
            'new_owner_username': new_owner.username,
            'current_owner_username': current_owner.username if current_owner else None
        }
        
        return redirect(reverse('users:confirm_ownership_transfer'))
    
    transfer_owner.short_description = "Передать права владельца"
    
    
    def get_list_display(self, request):
        if request.user.is_owner:
            return (
                'username', 'get_email_link', 'telegram_status',
                'is_staff', 'is_superuser', 'is_active'
            )
        if request.user.is_superuser:
            return (
                'username', 'get_email_link', 'telegram_status',
                'is_staff', 'is_active'
            )
        return ('username', 'email_masked', 'telegram_status', 'is_active')
    
    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (None, {
                    'classes': ('wide',),
                    'fields': ('username', 'password1', 'password2'),
                }),
            )
        
        if request.user.is_owner:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Личная информация', {
                    'fields': ('first_name', 'last_name', 'email', 'avatar', 'telegram_id'),
                    'classes': ('wide',)
                }),
                ('Права доступа', {
                    'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
                }),
                ('Важные даты', {'fields': ('last_login', 'date_joined')}),
            )
        
        if request.user.is_superuser:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Личная информация', {
                    'fields': ('first_name', 'last_name', 'email', 'avatar', 'telegram_id'),
                    'classes': ('wide',)
                }),
                ('Права доступа', {
                    'fields': ('is_active', 'is_staff', 'groups', 'user_permissions')
                }),
                ('Важные даты', {'fields': ('last_login', 'date_joined')}),
            )
        
        return (
            (None, {'fields': ('username', 'password')}),
            ('Личная информация', {
                'fields': ('first_name', 'last_name', 'avatar'),
                'classes': ('wide',)
            }),
            ('Права доступа', {'fields': ('is_active',)}),
            ('Важные даты', {'fields': ('last_login', 'date_joined')}),
        )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = ('last_login', 'date_joined', 'telegram_id', 'email')
        
        if request.user.is_owner:
            if obj == request.user:
                readonly += (
                    'username', 'email', 'first_name', 'last_name',
                    'avatar', 'is_active', 'is_staff', 'is_superuser', 'is_owner'
                )
            return readonly
        
        if not request.user.is_superuser:
            readonly += (
                'username', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
            )
        
        if obj == request.user:
            readonly += (
                'username', 'email', 'first_name', 'last_name',
                'avatar', 'is_active', 'is_staff', 'is_superuser'
            )
        
        return readonly
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('settings')
        
        if request.user.is_owner:
            return qs
        
        if request.user.is_superuser and not request.user.is_owner:
            return qs.filter(is_owner=False, is_superuser=False)
        
        if request.user.is_staff and not request.user.is_superuser:
            return qs.filter(is_staff=False, is_superuser=False, is_owner=False)
        
        return qs.none()
    
    def get_list_filter(self, request):
        filters = ('is_active', ('date_joined', DateFieldListFilter))
        if request.user.is_owner:
            filters = ('is_owner', 'is_superuser', 'is_staff') + filters
        elif request.user.is_superuser:
            filters = ('is_staff',) + filters
        return filters
    
    def get_inlines(self, request, obj=None):
        if obj is not None and (request.user.is_owner or request.user.is_superuser):
            return [UserSettingsInline]
        return []
    
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def _can_access_user(self, request, obj):
        if obj is None:
            return True
        
        if request.user.is_owner:
            return True
        
        if request.user.is_superuser and not request.user.is_owner:
            return not (obj.is_owner or obj.is_superuser)
        
        if request.user.is_staff and not request.user.is_superuser:
            return not (obj.is_staff or obj.is_superuser or obj.is_owner)
        
        return False
    
    def has_view_permission(self, request, obj=None):
        return self._can_access_user(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return self._can_access_user(request, obj)
    
    def has_change_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return self._can_access_user(request, obj)
    
    
    def get_email_link(self, obj):
        url = reverse('admin:users_customuser_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.email)
    
    get_email_link.short_description = 'Email'
    get_email_link.admin_order_field = 'email'
    
    def email_masked(self, obj):
        if not obj.email:
            return '-'
        local, domain = obj.email.split('@')
        masked = local[0] + '***' + (local[-1] if len(local) > 2 else '')
        return f"{masked}@{domain}"
    
    email_masked.short_description = 'Email'
    
    def telegram_status(self, obj):
        return "✅" if obj.telegram_id else "❌"
    
    telegram_status.short_description = 'Telegram'


admin.site.unregister(Group)


@staff_member_required
def confirm_ownership_transfer(request):
    transfer_data = request.session.get('pending_ownership_transfer')
    if not transfer_data:
        messages.error(request, "Нет ожидаемой передачи прав")
        return redirect('admin:users_customuser_changelist')
    
    if not request.user.is_owner:
        messages.error(request, "Только владелец может передавать права")
        return redirect('admin:users_customuser_changelist')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm':
            new_owner_id = transfer_data['new_owner_id']
            
            try:
                new_owner = CustomUser.objects.get(id=new_owner_id)
                current_owner = CustomUser.objects.filter(is_owner=True).first()
                
                if current_owner:
                    CustomUser.objects.filter(pk=current_owner.pk).update(is_owner=False)
                
                CustomUser.objects.filter(pk=new_owner.pk).update(is_owner=True)
                
                del request.session['pending_ownership_transfer']
                
                messages.success(
                    request,
                    f"Права владельца успешно переданы пользователю {new_owner.username}"
                )
                return redirect('admin:users_customuser_changelist')
                
            except CustomUser.DoesNotExist:
                messages.error(request, "Пользователь не найден")
                return redirect('admin:users_customuser_changelist')
        
        else:
            del request.session['pending_ownership_transfer']
            messages.info(request, "Передача прав отменена")
            return redirect('admin:users_customuser_changelist')
    
    context = {
        'new_owner': transfer_data['new_owner_username'],
        'current_owner': transfer_data.get('current_owner_username', 'нет (будет создан)'),
        'title': 'Подтверждение передачи прав владельца',
    }
    return render(request, 'admin/confirm_ownership_transfer.html', context)