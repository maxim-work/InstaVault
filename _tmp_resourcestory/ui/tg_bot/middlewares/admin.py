from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import ADMIN_IDS
from core.logger import get_logger

logger = get_logger("security")


class AdminMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not (isinstance(event, (Message, CallbackQuery)) and event.from_user):
            return await handler(event, data)

        if event.from_user.id in ADMIN_IDS:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer("У вас нет доступа", show_alert=True)
        else:
            await event.answer("У вас нет доступа")

        logger.warning(
            "User %s tried to access admin panel",
            event.from_user.id,
        )
        return None
