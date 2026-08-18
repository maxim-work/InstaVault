from aiogram.filters.callback_data import CallbackData


class AdminCallback(CallbackData, prefix="main"):
    action: str | None = None
    option: str | None = None
    page: int | None = None
    period: str | None = None


class ModerationCallback(CallbackData, prefix="moder"):
    action: str
    tg_id: int
    page: int
