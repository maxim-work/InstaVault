from collections.abc import Callable

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.markdown import hbold
from core.logger import get_logger
from data.db.resources import ResourceDB
from data.db.users import UserDB
from ui.tg_bot.callbacks.resource import SettingsCallback
from ui.tg_bot.handlers.resource.export import export
from ui.tg_bot.keyboards.resource import (
    create_del_import,
    create_import_data_menu,
    create_import_urls_menu,
    create_settings_menu,
)
from ui.tg_bot.states.resource import ImportState
from ui.tg_bot.utils.message import get_editable_message
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

logger = get_logger("settings")

settings_router = Router()


@settings_router.message(Command("settings"))
@settings_router.message(F.text == "Ещё")
async def cmd_settings(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    await _build_settings_menu(message, state, bot)


_IMPORT_MENUS: dict[str, tuple[str, Callable[[], InlineKeyboardMarkup]]] = {
    "import_urls_menu": (
        "Импорт ссылок:\n\n"
        "• Быстрый — все ссылки сохранятся с типом «Другое» и форматом по умолчанию.\n"
        "• Детальный — для каждой ссылки можно выбрать тип и формат.",
        create_import_urls_menu,
    ),
    "import_data_menu": (
        "Импорт данных:\n\n"
        "• Быстрый — загрузите JSON-файл, ресурсы добавятся без подтверждения.\n"
        "• Детальный — для каждого ресурса из файла можно изменить данные перед сохранением.",
        create_import_data_menu,
    ),
}


_IMPORT_START = {
    "import_urls_fast": (
        ImportState.waiting_for_urls,
        "urls",
        "fast",
        "Пришлите список ссылок (по одной на строку) или файл.txt:",
    ),
    "import_urls_detailed": (
        ImportState.waiting_for_urls,
        "urls",
        "detailed",
        "Пришлите список ссылок (по одной на строку) или файл.txt:",
    ),
    "import_data_fast": (
        ImportState.waiting_for_data,
        "data",
        "fast",
        "Пришлите JSON-файл с данными:",
    ),
    "import_data_detailed": (
        ImportState.waiting_for_data,
        "data",
        "detailed",
        "Пришлите JSON-файл с данными:",
    ),
}


@settings_router.callback_query(SettingsCallback.filter())
async def settings_callback(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    state: FSMContext,
    resource_db: ResourceDB,
    user_db: UserDB,
    bot: Bot,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id
    action = callback_data.action

    if action == "settings":
        await _build_settings_menu(message=message, state=state, bot=bot)

    elif action == "export_urls":
        await export(callback, state, resource_db, "urls")

    elif action == "export_data":
        await export(callback, state, resource_db, "data")

    elif action in _IMPORT_MENUS:
        text, kb_factory = _IMPORT_MENUS[action]
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text=text,
            reply_markup=kb_factory(),
        )

    elif action in _IMPORT_START:
        await _handle_import_start(callback, state, bot, action)

    elif action == "delete":
        await _handle_delete_menu(callback, state, bot, resource_db, tg_id)

    elif action == "del_all_resources":
        await _handle_del_all_resources(callback, state, bot, resource_db, tg_id)

    elif action == "del_account":
        await _handle_del_account(callback, state, bot, user_db, tg_id)

    else:
        logger.warning("Unknown settings action: %s", action)

    await callback.answer()


async def _handle_import_start(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    action: str,
) -> None:
    new_state, import_type, import_mode, text = _IMPORT_START[action]
    await state.set_state(new_state)
    await state.update_data(import_mode=import_mode, import_type=import_type)
    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text=text,
    )


async def _handle_delete_menu(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    resource_db: ResourceDB,
    tg_id: int,
) -> None:
    count = resource_db.count_user_resources(tg_id)
    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text=(
            "Удаление\n\n"
            f"• Всех ресурсов — удалит все {count}.\n"
            "• Аккаунта — очистит всю информацию о вас.\n\n"
            "<b>⚠️ Действия выполняются сразу, без дополнительного подтверждения.</b>\n\n"
            "Выберите вариант или нажмите назад, если вам это не нужно."
        ),
        reply_markup=create_del_import(),
        parse_mode="HTML",
        state_clear=True,
    )


async def _handle_del_all_resources(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    resource_db: ResourceDB,
    tg_id: int,
) -> None:
    count = resource_db.count_user_resources(tg_id)
    if count:
        resource_db.delete_all(tg_id)
        logger.warning("User %s deleted all resources (%s)", tg_id, count)
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text="Все ваши ресурсы удалены!",
            state_clear=True,
        )
        return

    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text="У вас нет ресурсов...",
    )


async def _handle_del_account(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
    tg_id: int,
) -> None:
    user_db.delete(tg_id)
    logger.warning("User %s deleted account", tg_id)
    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text="Ваш профиль удален!",
        state_clear=True,
    )


async def _build_settings_menu(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    if message.from_user is None:
        return

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=hbold("Дополнительные действия"),
        reply_markup=create_settings_menu(),
        parse_mode="HTML",
        state_clear=True,
    )
