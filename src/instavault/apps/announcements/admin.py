from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from .models import AnnouncementShown, AnnouncementText


@admin.register(AnnouncementText)
class AnnouncementTextAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "code",
        "group",
        "short_text",
        "category",
        "window",
        "frequency",
        "priority",
        "active",
    )
    list_filter = ("group", "category", "window", "frequency", "active")
    search_fields = ("code", "group", "text")
    ordering = ("priority",)

    @admin.display(description="Текст")
    def short_text(self, obj: AnnouncementText) -> str:
        return obj.text[:60]


@admin.register(AnnouncementShown)
class AnnouncementShownAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "group", "period_key", "shown_at")
    list_filter = ("group", "period_key")
    search_fields = ("user__username", "group")
    readonly_fields = ("user", "group", "period_key", "shown_at")
    date_hierarchy = "shown_at"

    def has_add_permission(self, request: HttpRequest) -> bool:  # noqa: ARG002
        return False
