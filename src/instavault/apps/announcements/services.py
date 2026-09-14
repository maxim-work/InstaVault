from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone

from .conditions import evaluate
from .models import AnnouncementShown, AnnouncementText

if TYPE_CHECKING:
    from instavault.apps.users.models import CustomUser


def _period_key(frequency: str, now: datetime) -> str:  # noqa: PLR0911
    match frequency:
        case AnnouncementText.Frequency.ONCE:
            return "once"
        case AnnouncementText.Frequency.DAILY:
            return now.date().isoformat()
        case AnnouncementText.Frequency.WEEKLY:
            iso = now.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        case AnnouncementText.Frequency.MONTHLY:
            return now.strftime("%Y-%m")
        case AnnouncementText.Frequency.YEARLY:
            return str(now.year)
        case AnnouncementText.Frequency.ON_CONDITION:
            return "cond"
        case _:
            return "once"


def pick_announcements(
    user: CustomUser, *, window: str | None = None, limit: int = 1
) -> list[AnnouncementText]:
    now = timezone.localtime()
    qs = AnnouncementText.objects.filter(active=True).order_by("priority", "code")
    if window:
        qs = qs.filter(window=window)

    picked: list[AnnouncementText] = []
    seen_groups: set[str] = set()

    for ann in qs:
        if len(picked) >= limit:
            break

        if ann.group in seen_groups:
            continue

        if not evaluate(ann.condition_key, user, ann.condition_params):
            continue

        key = _period_key(ann.frequency, now)
        try:
            with transaction.atomic():
                AnnouncementShown.objects.create(
                    user=user,
                    group=ann.group,
                    period_key=key,
                )
        except IntegrityError:
            seen_groups.add(ann.group)
            continue

        picked.append(ann)
        seen_groups.add(ann.group)

    return picked


def render_text(ann: AnnouncementText, user: CustomUser) -> str:
    now = timezone.localtime()
    return ann.text.format(
        name=user.first_name or user.username,
        date=now.strftime("%d.%m.%Y"),
        time=now.strftime("%H:%M"),
    )
