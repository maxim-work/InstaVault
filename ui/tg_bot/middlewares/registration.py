from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from core.service import UserService
from data.db.users import UserDB
from ui.tg_bot.middlewares.utils import get_real_event


class RegistrationMiddleware(BaseMiddleware):
    def __init__(self, user_db: UserDB, user_service: UserService) -> None:
        self.user_db = user_db
        self.user_service = user_service
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
            if self.user_db.get_user(real_event.from_user.id) is None:
                user = self.user_service.create_user(
                    tg_id=real_event.from_user.id,
                    first_name=real_event.from_user.first_name,
                    username=real_event.from_user.username,
                    last_name=real_event.from_user.last_name,
                )
                self.user_db.insert(user)

        return await handler(event, data)
