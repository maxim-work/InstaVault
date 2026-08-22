from typing import Any

from aiogram import BaseMiddleware


class DBMiddleware(BaseMiddleware):
    def __init__(self, user_db, resource_db, stats_db):
        self.user_db = user_db
        self.resource_db = resource_db
        self.stats_db = stats_db
        super().__init__()

    async def __call__(self, handler, event, data):
        data["user_db"] = self.user_db
        data["resource_db"] = self.resource_db
        data["stats_db"] = self.stats_db
        return await handler(event, data)
