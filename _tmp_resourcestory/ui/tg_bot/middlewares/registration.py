from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

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
        if real_event is None:
            return await handler(event, data)

        from_user = real_event.from_user
        if from_user is None:
            return await handler(event, data)

        if self.user_db.get_user(from_user.id) is None:
            user = self.user_service.create_user(
                tg_id=from_user.id,
                first_name=from_user.first_name or "Пользователь",
                username=from_user.username,
                last_name=from_user.last_name,
            )
            self.user_db.insert(user)

        return await handler(event, data)
