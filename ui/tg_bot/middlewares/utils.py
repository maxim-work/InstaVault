from aiogram.types import CallbackQuery, Message, Update


def get_real_event(event: Update) -> Message | CallbackQuery | None:
    return event.message or event.callback_query
