from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Update

from ui.tg_bot.utils.message import with_action_label


class CheckUserBanMiddleware(BaseMiddleware):
    def __init__(self, user_db) -> None:
        self.user_db = user_db
        super().__init__()

    async def __call__(self, handler, event, data):
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
                        await real_event.answer(
                            msg,
                            show_alert=True,
                        )
                    else:
                        await real_event.answer(msg)
                    return
        return await handler(event, data)
