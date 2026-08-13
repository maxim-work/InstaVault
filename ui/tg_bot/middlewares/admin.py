from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS


class AdminMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(self, handler, event, data):
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            if event.from_user.id not in ADMIN_IDS:
                if isinstance(event, CallbackQuery):
                    await event.answer("У вас нет доступа", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer("У вас нет доступа")
                return
            return await handler(event, data)
