from collections.abc import Callable
from typing import Any

from aiogram.types import CallbackQuery, Message
from core.exceptions import (
    APIResponseError,
    InvalidParamError,
    InvalidRatingError,
    InvalidUrlParamError,
    NetworkError,
    ProxyRequestError,
    ResourceNotFoundError,
)
from core.logger import get_logger
from ui.tg_bot.utils.message import get_editable_message

logger = get_logger("error_handler")

USER_ERRORS: dict[type[Exception], str | Callable[[Exception], str]] = {
    InvalidUrlParamError: "Некорректная ссылка.",
    InvalidParamError: lambda e: f"Некорректный параметр: {_format_invalid_param_error(e)}",
    InvalidRatingError: "Некорректный рейтинг.",
}

SYSTEM_ERRORS: tuple[type[Exception], ...] = (
    ProxyRequestError,
    APIResponseError,
    NetworkError,
    ResourceNotFoundError,
)


async def handle_resource_error(
    error: Exception,
    context: dict[str, Any],
    with_action_label: Callable[[str, str], str],
    action: str = "error_add",
    callback: CallbackQuery | None = None,
    message: Message | None = None,
) -> bool:
    if message is None and callback is not None:
        message = get_editable_message(callback)
    if message is None:
        return False

    if type(error) in USER_ERRORS:
        handler = USER_ERRORS[type(error)]
        msg = handler(error) if callable(handler) else handler
        await message.edit_text(with_action_label(action, msg))
        return True

    if isinstance(error, SYSTEM_ERRORS):
        logger.error(
            "Ошибка при создании ресурса: %s",
            type(error).__name__,
            exc_info=error,
            extra=context,
        )
        await message.edit_text(
            with_action_label(action, "Ошибка сервиса. Мы уже работаем над этим.")
        )
        return True

    logger.error(
        "Неизвестная ошибка: %s",
        type(error).__name__,
        exc_info=error,
        extra=context,
    )
    await message.edit_text(with_action_label(action, "Ошибка сервиса. Мы уже работаем над этим."))
    return True


def _format_invalid_param_error(e: Exception) -> str:
    if not isinstance(e, InvalidParamError):
        return "Некорректный параметр."
    return f"Некорректный параметр: {e.param}"
