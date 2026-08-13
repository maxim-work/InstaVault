from typing import Any

from aiogram import BaseMiddleware

from data.service_db import ResourceDB, StatsDB, UserDB


class DBMiddleware(BaseMiddleware):
    def __init__(self, user_db: UserDB, resource_db: ResourceDB, stats_db: StatsDB):
        self.user_db = user_db
        self.resource_db = resource_db
        self.stats_db = stats_db
        super().__init__()

    async def __call__(self, handler, event, data):
        data["user_db"] = self.user_db
        data["resource_db"] = self.resource_db
        data["stats_db"] = self.stats_db
        return await handler(event, data)
