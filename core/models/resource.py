import json
from datetime import datetime
from math import log10
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationInfo, field_serializer, field_validator

from config import MAX_URL_LENGTH
from core.config import RATING_CONFIG
from core.enum import ResourceKind, ResourcePlatform, ResourceStatus, ResourceType
from core.exceptions import InvalidParamError, InvalidRatingError, UnknownClassCodeError
from core.utils import detect_platform

_PLATFORM_RATING_PARAMS = {
    ResourcePlatform.YOUTUBE: {
        "view_smoothing": RATING_CONFIG.view_smoothing,
        "engagement_smoothing": RATING_CONFIG.engagement_smoothing,
        "view_norm": RATING_CONFIG.video_view_norm,
        "reach_multiplier": RATING_CONFIG.video_reach_multiplier,
        "engagement_rate_multiplier": RATING_CONFIG.video_engagement_rate_multiplier,
        "engagement_multiplier": RATING_CONFIG.video_engagement_multiplier,
    },
    ResourcePlatform.HABR: {
        "view_smoothing": RATING_CONFIG.habr_view_smoothing,
        "engagement_smoothing": RATING_CONFIG.habr_engagement_smoothing,
        "view_norm": RATING_CONFIG.habr_view_norm,
        "reach_multiplier": RATING_CONFIG.habr_reach_multiplier,
        "engagement_rate_multiplier": RATING_CONFIG.habr_engagement_rate_multiplier,
        "engagement_multiplier": RATING_CONFIG.habr_engagement_multiplier,
    },
}


class Resource(BaseModel):
    model_config = {"frozen": False}

    id: int | None = None
    tg_id: int | None = None
    title: str
    url: str
    description: str | None = None
    resource_type: ResourceType = ResourceType.OTHER
    platform: ResourcePlatform = ResourcePlatform.OTHER
    kind: ResourceKind = ResourceKind.OTHER
    external_id: str | None = None
    status: ResourceStatus = ResourceStatus.TO_TEACH
    tags: list[str] = Field(default_factory=list)
    my_notes: str | None = None
    my_rating: int | None = None
    engagement: int | None = None
    views: int | None = None
    duration: int | None = None
    published_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise InvalidParamError("title", str(v), "Название обязательно")
        return v

    @field_validator("url")
    @classmethod
    def url_must_be_valid(cls, v: str) -> str:
        if not v:
            raise InvalidParamError("url", str(v), "URL обязателен")
        if not cls._is_valid_url(v):
            raise InvalidParamError("url", v, f"Некорректный URL: {v}")
        return v

    @field_validator("resource_type", mode="before")
    @classmethod
    def coerce_resource_type(cls, v) -> ResourceType:
        if isinstance(v, str):
            try:
                return ResourceType.from_code(v)
            except UnknownClassCodeError:
                return ResourceType.OTHER
        if not isinstance(v, ResourceType):
            raise TypeError("resource_type должен быть ResourceType")
        return v

    @field_validator("platform", mode="before")
    @classmethod
    def coerce_and_detect_platform(cls, v, info: ValidationInfo) -> ResourcePlatform:
        if isinstance(v, str):
            try:
                v = ResourcePlatform.from_code(v)
            except UnknownClassCodeError:
                v = ResourcePlatform.OTHER
        if not isinstance(v, ResourcePlatform):
            raise TypeError("platform должна быть ResourcePlatform")
        if v == ResourcePlatform.OTHER:
            url = info.data.get("url") if info.data else None
            if url:
                detected = detect_platform(url)
                if detected in ("youtube", "habr"):
                    return ResourcePlatform.from_code(detected)
        return v

    @field_validator("kind", mode="before")
    @classmethod
    def coerce_and_detect_kind(cls, v, info: ValidationInfo) -> ResourceKind:
        if isinstance(v, str):
            try:
                v = ResourceKind.from_code(v)
            except UnknownClassCodeError:
                v = ResourceKind.OTHER
        if not isinstance(v, ResourceKind):
            raise TypeError("kind должен быть ResourceKind")
        if v == ResourceKind.OTHER:
            platform = info.data.get("platform") if info.data else None
            if platform == ResourcePlatform.YOUTUBE:
                return ResourceKind.VIDEO
            elif platform == ResourcePlatform.HABR:
                return ResourceKind.ARTICLE
        return v

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, v) -> ResourceStatus:
        if isinstance(v, str):
            try:
                return ResourceStatus.from_code(v)
            except UnknownClassCodeError:
                return ResourceStatus.TO_TEACH
        if not isinstance(v, ResourceStatus):
            raise TypeError("status должна быть ResourceStatus")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        if isinstance(v, list):
            return v
        return []

    @field_validator("my_rating")
    @classmethod
    def validate_my_rating(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= RATING_CONFIG.max_personal_rating:
            raise InvalidRatingError(v, RATING_CONFIG.max_personal_rating)
        return v

    @field_validator("duration", "views", "engagement")
    @classmethod
    def validate_positive(cls, v: int | None, info: ValidationInfo) -> int | None:
        if v is not None and v < 0:
            field_name = info.field_name or "поле"
            raise InvalidParamError(
                field_name, str(v), f"{field_name} не может быть отрицательным"
            )
        return v

    @field_serializer("resource_type", "platform", "kind", "status")
    def serialize_enum(self, value) -> str:
        return value.code

    @field_serializer("tags")
    def serialize_tags(self, value: list[str]) -> str:
        return json.dumps(value, ensure_ascii=False)

    @classmethod
    def from_url(cls, url: str, title: str = "") -> "Resource":
        return cls(url=url, title=title)

    def update_my_rating(self, rating: int) -> None:
        if not 1 <= rating <= RATING_CONFIG.max_personal_rating:
            raise InvalidRatingError(rating, RATING_CONFIG.max_personal_rating)
        self.my_rating = rating

    def update_stats(
        self, views: int | None = None, engagement: int | None = None
    ) -> None:
        if views is not None:
            self.views = views
        if engagement is not None:
            self.engagement = engagement

    def update_status(self, status: ResourceStatus) -> None:
        if status == ResourceStatus.TO_TEACH:
            self.reset()
        elif status == ResourceStatus.TEACHED:
            self.complete()
        else:
            self.status = status

    def complete(self, rating: int | None = None) -> None:
        self.status = ResourceStatus.TEACHED
        self.completed_at = datetime.now()
        if rating is not None:
            self.update_my_rating(rating)

    def master(self) -> None:
        self.status = ResourceStatus.MASTERED
        if not self.completed_at:
            self.completed_at = datetime.now()

    def archive(self) -> None:
        self.status = ResourceStatus.ARCHIVED

    def reset(self, reset_rating: bool = True) -> None:
        self.status = ResourceStatus.TO_TEACH
        self.completed_at = None
        if reset_rating:
            self.my_rating = None

    @property
    def is_completed(self) -> bool:
        return self.status in (ResourceStatus.TEACHED, ResourceStatus.MASTERED)

    @property
    def is_active(self) -> bool:
        return self.status != ResourceStatus.ARCHIVED

    @property
    def has_tags(self) -> bool:
        return bool(self.tags)

    @property
    def score(self) -> float:
        if not self.views or self.views <= 0:
            return self._personal_rating_score()

        params = _PLATFORM_RATING_PARAMS.get(self.platform)
        if params:
            return self._calculate_rating(**params)

        return self._personal_rating_score()

    @property
    def duration_display(self) -> str:
        if self.duration is None:
            return "Не указано"
        hours, minutes = divmod(self.duration, 60)
        return f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"

    def format_detailed(self) -> str:
        parts = [
            self.title,
            f"[{self.resource_type.label}]",
            f"- {self.status.label}",
        ]
        if self.my_rating is not None:
            parts.append(f"(Ваша оценка: {self.my_rating}/5)")
        return " ".join(parts)

    def to_db_dict(self) -> dict:
        return {
            "tg_id": self.tg_id,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "resource_type": self.resource_type.code,
            "platform": self.platform.code,
            "kind": self.kind.code,
            "external_id": self.external_id,
            "status": self.status.code,
            "tags": json.dumps(self.tags, ensure_ascii=False),
            "my_notes": self.my_notes,
            "my_rating": self.my_rating,
            "engagement": self.engagement,
            "views": self.views,
            "duration": self.duration,
            "published_at": self.published_at.isoformat()
            if self.published_at
            else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self) -> str:
        return f"{self.title} [{self.resource_type.label}]"

    def __repr__(self) -> str:
        fields = {k: v for k, v in self.__dict__.items() if k != "args"}
        parts = [f"{k}={v!r}" for k, v in fields.items()]
        return f"Resource({', '.join(parts)})"

    def __rich_repr__(self):
        yield "id", self.id
        yield "title", self.title
        yield "url", self.url
        yield "type", self.resource_type.label
        yield "status", self.status.label
        yield "score", self.score

    def _calculate_rating(
        self,
        view_smoothing: int,
        engagement_smoothing: int,
        view_norm: float,
        reach_multiplier: float,
        engagement_rate_multiplier: float,
        engagement_multiplier: float,
    ) -> float:
        cfg = RATING_CONFIG
        v = self.views or 1
        e = self.engagement or 0

        smoothed_v = v + view_smoothing
        smoothed_e = e + engagement_smoothing

        reach_raw = log10(1.0 + smoothed_v / view_norm)
        reach_score = min(cfg.max_score / 2, reach_raw * reach_multiplier)

        capped_e = min(smoothed_e, float(smoothed_v))
        engagement_rate = capped_e / smoothed_v

        eng_raw = (
            log10(1.0 + engagement_rate * engagement_rate_multiplier)
            if engagement_rate > 0
            else 0.0
        )
        eng_score = min(cfg.max_score / 2, eng_raw * engagement_multiplier)

        platform_score = reach_score + eng_score

        if self.my_rating is not None:
            personal_score = self._personal_rating_score()
            return round(
                cfg.platform_weight * platform_score
                + cfg.personal_weight * personal_score,
                2,
            )

        return round(min(cfg.max_score, platform_score), 2)

    def _personal_rating_score(self) -> float:
        if self.my_rating is None:
            return 0.0
        return (
            self.my_rating / RATING_CONFIG.max_personal_rating
        ) * RATING_CONFIG.max_score

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            return bool(
                parsed.scheme in ("http", "https")
                and parsed.netloc
                and len(url) <= MAX_URL_LENGTH
            )
        except Exception:
            return False
