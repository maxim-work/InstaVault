from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest

from instavault.apps.audit.models import AuditLog

if TYPE_CHECKING:
    from instavault.apps.users.models import CustomUser


def log_action(
    user: CustomUser | None,
    performed_by: CustomUser | None,
    action: str,
    category: str,
    details: str = "",
    request: HttpRequest | None = None,
) -> None:
    ip = request.META.get("REMOTE_ADDR") if request else None
    AuditLog.objects.create(
        category=category,
        user=user,
        performed_by=performed_by,
        action=action,
        details=details,
        ip_address=ip,
    )
