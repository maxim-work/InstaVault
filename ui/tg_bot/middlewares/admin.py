from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import ADMIN_IDS


class AdminMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            if event.from_user.id not in ADMIN_IDS:
                if isinstance(event, CallbackQuery):
                    await event.answer("У вас нет доступа", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer("У вас нет доступа")
                return
            return await handler(event, data)
        return await handler(event, data)
