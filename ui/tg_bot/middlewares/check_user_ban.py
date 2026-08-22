from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from data.db.users import UserDB
from ui.tg_bot.utils.message import with_action_label


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
        if isinstance(event, Update):
            real_event = event.message or event.callback_query
            if real_event and real_event.from_user:
                if not self.user_db.is_active(real_event.from_user.id):
                    msg = with_action_label(
                        "info",
                        "Вы заблокированы и не можете использовать бота.\n"
                        "Если считаете это ошибкой, свяжитесь с администратором.",
                    )
                    if isinstance(real_event, CallbackQuery):
                        await real_event.answer(msg, show_alert=True)
                    elif isinstance(real_event, Message):
                        await real_event.answer(msg)
                    return
        return await handler(event, data)
