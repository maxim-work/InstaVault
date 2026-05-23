from audit.models import AuditLog


def log_action(user, performed_by, action, category, details='', request=None):
    ip = request.META.get('REMOTE_ADDR') if request else None
    AuditLog.objects.create(
        category=category,
        user=user,
        performed_by=performed_by,
        action=action,
        details=details,
        ip_address=ip
    )