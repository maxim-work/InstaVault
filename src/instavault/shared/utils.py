from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast
from urllib.parse import urlparse

if TYPE_CHECKING:
    from django.http import HttpRequest

    from instavault.apps.users.models import CustomUser


def get_user(request: HttpRequest) -> CustomUser:
    return cast("CustomUser", request.user)


def is_valid_domain(domain: str) -> bool:
    if not domain or " " in domain:
        return False

    if any(ord(c) > 127 for c in domain):
        return "." in domain

    pattern = (
        r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?"
        r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)+$"
    )
    return bool(re.match(pattern, domain))


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()

    domain = domain.removeprefix("www.")

    if not domain:
        return "unknown"

    if any(yt in domain for yt in ["youtube.com", "youtu.be"]):
        return "youtube"
    if any(h in domain for h in ["habr.com", "habr.ru"]):
        return "habr"
    if is_valid_domain(domain):
        return domain
    return "unknown"


def extract_external_id(url: str, platform: str) -> str | None:
    if platform == "youtube":
        match = re.search(r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})", url)
        if match:
            return match.group(1)

    elif platform == "habr":
        match = re.search(r"/(?:articles|news|posts|sandbox)/(\d+)", url)
        if match:
            return match.group(1)

    return None
