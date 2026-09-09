from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, Update
from core.logger import get_logger
from data.db.users import UserDB
from ui.tg_bot.utils.message import with_action_label

logger = get_logger("security")


class CheckUserBanMiddleware(BaseMiddleware):
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

        real_event = event.message or event.callback_query
        if not (real_event and real_event.from_user):
            return await handler(event, data)

        if self.user_db.is_active(real_event.from_user.id):
            return await handler(event, data)

        msg = with_action_label(
            "info",
            "Вы заблокированы и не можете использовать бота.\n"
            "Если считаете это ошибкой, свяжитесь с администратором.",
        )
        if isinstance(real_event, CallbackQuery):
            await real_event.answer(msg, show_alert=True)
        else:
            await real_event.answer(msg)

        logger.warning(
            "Banned user %s tried to access bot",
            real_event.from_user.id,
        )
        return None
