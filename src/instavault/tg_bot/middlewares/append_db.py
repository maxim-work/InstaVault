from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from data.db.resources import ResourceDB
from data.db.stats import StatsDB
from data.db.users import UserDB


class DBMiddleware(BaseMiddleware):
    def __init__(
        self,
        user_db: UserDB,
        resource_db: ResourceDB,
        stats_db: StatsDB,
    ) -> None:
        self.user_db = user_db
        self.resource_db = resource_db
        self.stats_db = stats_db
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["user_db"] = self.user_db
        data["resource_db"] = self.resource_db
        data["stats_db"] = self.stats_db
        return await handler(event, data)
