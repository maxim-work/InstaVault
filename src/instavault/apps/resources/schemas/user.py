from datetime import UTC, datetime

from core.exceptions import InvalidParamError
from pydantic import BaseModel, Field, field_validator


def _now_utc() -> datetime:
    return datetime.now(UTC)


class User(BaseModel):
    model_config = {"frozen": False}

    id: int | None = None
    tg_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None
    is_active: bool = True
    last_active_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now_utc)

    @field_validator("tg_id")
    @classmethod
    def validate_tg_id(cls, v: int) -> int:
        if v < 2_000_000 and v != 0:
            raise InvalidParamError("tg_id", str(v), "tg_id должен быть >= 2 000 000")
        return v

    @field_validator("first_name")
    @classmethod
    def first_name_must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise InvalidParamError("first_name", v, "first_name обязательно")
        return v

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def is_inactive(self) -> bool:
        return not self.is_active

    def update(
        self,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> None:
        if username is not None:
            self.username = username
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

    def to_db_dict(self) -> dict[str, object]:
        return {
            "tg_id": self.tg_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }

    def __str__(self) -> str:
        return f"{self.full_name} @{self.username or 'отсутствует'}"

    def __repr__(self) -> str:
        return f"{self.full_name} is_active={self.is_active} last_active_at={self.last_active_at}"
