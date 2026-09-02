from enum import Enum
from typing import Self, TypeVar

from core.exceptions import UnknownClassCodeError

T = TypeVar("T", bound="BaseEnum")


class BaseEnum(Enum):
    @property
    def code(self) -> str:
        return self._value_[0]

    @property
    def label(self) -> str:
        return self._value_[1]

    @classmethod
    def from_code(cls, code: str) -> Self:
        if code == "others":
            code = "other"
        for item in cls:
            if item.code == code:
                return item
        raise UnknownClassCodeError(cls.__name__, code)


class ResourceStatus(BaseEnum):
    TO_TEACH = ("to_teach", "В очереди на изучение")
    TEACHED = ("teached", "Изучил")
    MASTERED = ("mastered", "Полностью усвоил, знаю тему")
    OUTDATED = ("outdated", "Устарело: версия, подход, инструмент")
    ARCHIVED = ("archived", "Скрыто из активной выдачи")


class ResourceType(BaseEnum):
    IT = ("it", "IT")
    DIY = ("diy", "Do It Yourself")
    CHESS = ("chess", "Шахматы")
    GUITAR = ("guitar", "Гитара")
    MATH = ("math", "Математика")
    PHYSICS = ("physics", "Физика")
    SELF_DEVELOPMENT = ("self_development", "Саморазвитие")
    ENGLISH = ("english", "Английский язык")
    SCIENCE = ("science", "Наука")
    HISTORY = ("history", "История")
    OTHER = ("other", "Другое")


class ResourceKind(BaseEnum):
    VIDEO = ("video", "Видео")
    ARTICLE = ("article", "Статья")
    SITE = ("site", "Сайт/Ресурс")
    BOOK = ("book", "Книга")
    COURSE = ("course", "Курс")
    PODCAST = ("podcast", "Подкаст")
    OTHER = ("other", "Другое")


class ResourcePlatform(BaseEnum):
    YOUTUBE = ("youtube", "YouTube")
    HABR = ("habr", "Habr")
    COURSERA = ("coursera", "Coursera")
    UDEMY = ("udemy", "Udemy")
    STEPIK = ("stepik", "Stepik")
    MEDIUM = ("medium", "Medium")
    GITHUB = ("github", "GitHub")
    TELEGRAM = ("telegram", "Telegram")
    OTHER = ("other", "Другое")
