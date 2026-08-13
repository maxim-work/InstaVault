from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update

from ui.tg_bot.middlewares.utils import get_real_event


class RegistrationMiddleware(BaseMiddleware):
    def __init__(self, user_db, user_service):
        self.user_db = user_db
        self.user_service = user_service
        super().__init__()

    async def __call__(self, handler, event, data):
        if not isinstance(event, Update):
            return await handler(event, data)
        data["user_db"] = self.user_db
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
