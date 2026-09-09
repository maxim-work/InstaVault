from typing import Any

from django.contrib.auth.backends import ModelBackend


class AllowInactiveBackend(ModelBackend):
    def user_can_authenticate(self, user: Any) -> bool:  # noqa: ARG002
        return True
