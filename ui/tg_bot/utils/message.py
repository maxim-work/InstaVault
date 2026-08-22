import asyncio

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold


async def auto_delete(bot: Bot, chat_id: int, message_id: int, delay: int = 3) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def safe_delete_many(bot: Bot, chat_id: int, *message_ids: int) -> None:
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass


ACTION_TEMPLATES: dict[str, tuple[str, str]] = {
    "add": ("➕", "Добавление ресурса"),
    "edit": ("✏️", "Редактирование ресурса"),
    "search": ("🔍", "Поиск ресурса"),
    "delete": ("🗑", "Удаление ресурса"),
    "export": ("📤", "Экспорт"),
    "import": ("📥", "Импорт"),
    "settings": ("⚙️", "Настройки"),
    "error_add": ("⚠️", "Ошибка при добавлении ресурса"),
    "error_edit": ("⚠️", "Ошибка при редактировании ресурса"),
    "error_delete": ("⚠️", "Ошибка при удалении ресурса"),
    "error_fetch": ("⚠️", "Ошибка при получении ресурса"),
    "error_not_found": ("❌", "Ресурс не найден"),
    "error_validate": ("❌", "Ошибка валидации"),
    "error_import": ("⚠️", "Ошибка при импорте ресурсов"),
    "error_export": ("⚠️", "Ошибка при экспорте ресурсов"),
    "info": ("ℹ️", "Информация"),
}


def with_action_label(action: str, text: str, title: str | None = None) -> str:
    emoji, action_name = ACTION_TEMPLATES.get(action, ("⚙️", str(action)))

    label = f"{emoji} {action_name}"
    if title:
        label += f" «{title}»"

    return f"{hbold(label)}\n\n{text}"


def get_editable_message(callback: CallbackQuery) -> Message | None:
    return callback.message if isinstance(callback.message, Message) else None


async def cleanup_previous_message(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")
    if prompt_msg_id is not None:
        try:
            await bot.delete_message(message.chat.id, prompt_msg_id)
        except Exception:
            pass
