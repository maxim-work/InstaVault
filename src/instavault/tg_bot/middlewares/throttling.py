from collections import defaultdict
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from config import ADMIN_IDS
from core.logger import get_logger

logger = get_logger("security")


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(
        self,
        rate_limit: int = 3,
        window: int = 1,
    ) -> None:
        self.rate_limit = rate_limit
        self.window = window
        self.requests: dict[int, list[float]] = defaultdict(list)
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):  # noqa: SIM108
            real_event = event.message or event.callback_query
        else:
            real_event = event

        user_id: int | None = None
        if isinstance(real_event, (Message, CallbackQuery)):
            user_id = real_event.from_user.id if real_event.from_user else None

        if user_id is None:
            return await handler(event, data)

        if user_id in ADMIN_IDS:
            return await handler(event, data)

        now = monotonic()
        self.requests[user_id] = [ts for ts in self.requests[user_id] if ts > now - self.window]

        if len(self.requests[user_id]) >= self.rate_limit:
            logger.warning("Throttling: user %s exceeded rate limit", user_id)
            if isinstance(real_event, CallbackQuery):
                await real_event.answer(
                    "Слишком много действий. Подождите секунду.", show_alert=True
                )
            elif isinstance(real_event, Message):
                await real_event.answer("Слишком много сообщений. Подождите секунду.")
            return None

        self.requests[user_id].append(now)
        return await handler(event, data)
