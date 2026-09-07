from django.contrib import admin
from audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'category', 'action', 'user', 'performed_by')
    list_filter = ('category', 'action', 'created_at')
    search_fields = ('user__username', 'performed_by__username', 'details')
    readonly_fields = ('category', 'user', 'performed_by', 'action', 'details', 'ip_address', 'created_at')
    ordering = ('-created_at',)