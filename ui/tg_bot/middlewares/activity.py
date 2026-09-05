import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from config import ACTIVITY_UPDATE_INTERVAL_SECONDS
from data.db.users import UserDB
from ui.tg_bot.middlewares.utils import get_real_event


class ActivityMiddleware(BaseMiddleware):
    def __init__(self, user_db: UserDB) -> None:
        self.user_db = user_db
        self.last_flush: dict[int, float] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            real_event = get_real_event(event)

            if isinstance(real_event, (Message, CallbackQuery)) and real_event.from_user:
                tg_id = real_event.from_user.id
                now = time.monotonic()

                if (
                    tg_id not in self.last_flush
                    or now - self.last_flush[tg_id] > ACTIVITY_UPDATE_INTERVAL_SECONDS
                ):
                    self.user_db.update_last_active(tg_id)
                    self.last_flush[tg_id] = now

        return await handler(event, data)
