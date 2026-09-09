from datetime import UTC, datetime
from typing import Any

from config import MIN_TG_ID
from core.exceptions import (
    InvalidParamError,
    InvalidUrlParamError,
    UnknownClassCodeError,
)
from core.models.resource import (
    Resource,
    ResourceKind,
    ResourcePlatform,
    ResourceStatus,
    ResourceType,
)
from core.models.user import User
from core.parse_info import fetch_page_info, fetch_youtube_video_info
from core.utils import detect_platform, extract_external_id


class ResourceService:
    @staticmethod
    def create_resource(
        url: str,
        tg_id: int,
        resource_type: ResourceType = ResourceType.OTHER,
        kind: ResourceKind | None = None,
        user_tags: list[str] | None = None,
        youtube_api_key: str | None = None,
        proxy: str | None = None,
        proxy_type: str = "socks5",
    ) -> Resource:
        info = ResourceService.get_info_for_url(url, youtube_api_key, proxy, proxy_type)
        return Resource(
            tg_id=tg_id,
            title=info["title"],
            description=info["description"],
            platform=info["platform_enum"],
            kind=kind or info["kind"],
            external_id=info["external_id"],
            url=info["url"],
            resource_type=resource_type,
            tags=user_tags or info["tags"],
            engagement=info["engagement"],
            views=info["views"],
            duration=info["duration"],
            published_at=info["published_at"],
        )

    @staticmethod
    def edit_resource(
        resource: Resource,
        resource_type: ResourceType | None = None,
        kind: ResourceKind | None = None,
        status: ResourceStatus | None = None,
        my_notes: str | None = None,
        my_rating: int | None = None,
        completed_at: datetime | None = None,
    ) -> Resource:
        if resource_type is not None:
            resource.resource_type = resource_type
        if kind is not None:
            resource.kind = kind
        if status is not None:
            resource.update_status(status)
        if my_notes is not None:
            resource.my_notes = my_notes
        if my_rating is not None:
            resource.update_my_rating(my_rating)
        if completed_at is not None and resource.status != ResourceStatus.TO_TEACH:
            resource.completed_at = completed_at
        return resource

    @staticmethod
    def get_info_for_url(
        url: str,
        youtube_api_key: str | None = None,
        proxy: str | None = None,
        proxy_type: str = "socks5",
    ) -> dict[str, Any]:
        info = None
        external_id = None

        platform = detect_platform(url)

        if platform == "unknown":
            raise InvalidUrlParamError(
                "platform", url, f"Не удалось определить платформу для url: {url}"
            )

        if platform in ("youtube", "habr"):
            external_id = extract_external_id(url, platform)

            if not external_id:
                raise InvalidUrlParamError(
                    "external_id",
                    url,
                    f"Не смогли выделить external id из url({url})",
                )

        if platform == "youtube" and external_id is not None:
            if not youtube_api_key:
                raise InvalidUrlParamError(
                    "youtube_api_key",
                    str(youtube_api_key),
                    "Нету API ключа для youtube",
                )
            info = fetch_youtube_video_info(external_id, youtube_api_key, proxy, proxy_type)
            kind = ResourceKind.VIDEO
        elif platform == "habr":
            info = fetch_page_info(url, platform="habr", proxy=proxy, proxy_type=proxy_type)
            kind = ResourceKind.ARTICLE
        else:
            info = fetch_page_info(url, proxy=proxy, proxy_type=proxy_type)
            kind = ResourceKind.SITE

        if not info:
            raise InvalidUrlParamError(
                "info", url, f"Не получилось получить информацию по url({url})"
            )
        try:
            platform_enum = ResourcePlatform.from_code(platform)
        except UnknownClassCodeError:
            platform_enum = ResourcePlatform.OTHER
        return {
            "title": info["title"],
            "description": info["description"],
            "platform_enum": platform_enum,
            "kind": kind,
            "external_id": external_id,
            "url": url,
            "tags": info["tags"],
            "engagement": info["engagement"],
            "views": info["views"],
            "duration": info["duration"],
            "published_at": info["published_at"],
        }


class UserService:
    @staticmethod
    def create_user(
        tg_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
    ) -> User:
        if tg_id < MIN_TG_ID:
            raise InvalidParamError("tg_id", str(tg_id), f"tg id не может быть меньше {MIN_TG_ID}")
        if not first_name:
            raise InvalidParamError("first_name", first_name, "first name обязательное поле")
        return User(
            tg_id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            last_active_at=datetime.now(UTC),
        )

    @staticmethod
    def update_user(
        user: User,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> None:
        user.update(username, first_name, last_name)
