from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from instavault.apps.audit.utils import log_action
from instavault.apps.users.models import CustomUser
from instavault.shared.utils import get_user


class BanCheckMiddleware:
    EXEMPT_URLS = ("/ban-appeal/", "/static/")

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._is_exempt(request.path):
            return self.get_response(request)

        user = get_user(request)

        if user.is_authenticated:
            if user.should_auto_unban():
                user.perform_auto_unban()

                log_action(
                    user=user,
                    performed_by=None,
                    action="auto_unban",
                    category="system",
                    request=request,
                )

            if user.is_banned():
                return self._render_ban_page(request, user)

        return self.get_response(request)

    def _is_exempt(self, path: str) -> bool:
        return path.startswith(tuple(self.EXEMPT_URLS))

    def _render_ban_page(
        self,
        request: HttpRequest,
        user: CustomUser,
    ) -> HttpResponse:
        request.session["banned_user_id"] = user.pk

        logout(request)

        context = {
            "reason": user.reason_ban,
            "started": user.started_ban,
            "ended": user.ended_ban,
            "now": timezone.now(),
        }
        return render(request, "users/banned.html", context, status=403)
