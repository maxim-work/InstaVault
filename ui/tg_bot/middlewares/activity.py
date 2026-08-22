from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update, TelegramObject
from collections.abc import Awaitable, Callable
from typing import Any

from data.db.users import UserDB
from ui.tg_bot.middlewares.utils import get_real_event


class ActivityMiddleware(BaseMiddleware):
    def __init__(self, user_db: UserDB) -> None:
        self.user_db = user_db
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)

        real_event = get_real_event(event)

        if isinstance(real_event, (Message, CallbackQuery)) and real_event.from_user:
            self.user_db.update_last_active(real_event.from_user.id)

        return await handler(event, data)
