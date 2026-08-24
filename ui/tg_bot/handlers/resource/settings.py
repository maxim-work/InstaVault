import os

from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold

from data.db.resources import ResourceDB
from data.db.users import UserDB
from data_io.export_data import write_data_file, write_urls_file
from ui.tg_bot.callbacks.resource import SettingsCallback
from ui.tg_bot.keyboards.resource import (
    create_del_import,
    create_import_data_menu,
    create_import_urls_menu,
    create_settings_menu,
)
from ui.tg_bot.states.resource import ImportState
from ui.tg_bot.utils.message import get_editable_message
from ui.tg_bot.utils.transition import transition_callback, transition_to_message
from core.logger import get_logger

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
        await _export(callback, state, resource_db, bot, "urls")

    elif action == "export_data":
        await _export(callback, state, resource_db, bot, "data")

    elif action == "import_urls_menu":
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text="Импорт ссылок:\n\n"
            "• Быстрый — все ссылки сохранятся с типом «Другое» и форматом по умолчанию.\n"
            "• Детальный — для каждой ссылки можно выбрать тип и формат.",
            reply_markup=create_import_urls_menu(),
        )

    elif action == "import_data_menu":
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text="Импорт данных:\n\n"
            "• Быстрый — загрузите JSON-файл, ресурсы добавятся без подтверждения.\n"
            "• Детальный — для каждого ресурса из файла можно изменить данные перед сохранением.",
            reply_markup=create_import_data_menu(),
        )

    elif action == "import_urls_fast":
        await state.set_state(ImportState.waiting_for_urls)
        await state.update_data(import_mode="fast", import_type="urls")
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text="Пришлите список ссылок (по одной на строку) или файл.txt:",
        )

    elif action == "import_urls_detailed":
        await state.set_state(ImportState.waiting_for_urls)
        await state.update_data(import_mode="detailed", import_type="urls")
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text="Пришлите список ссылок (по одной на строку) или файл.txt:",
        )

    elif action == "import_data_fast":
        await state.set_state(ImportState.waiting_for_data)
        await state.update_data(import_mode="fast", import_type="data")
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text="Пришлите JSON-файл с данными:",
        )

    elif action == "import_data_detailed":
        await state.set_state(ImportState.waiting_for_data)
        await state.update_data(import_mode="detailed", import_type="data")
        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text="Пришлите JSON-файл с данными:",
        )

    elif action == "delete":
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

    elif action == "del_all_resources":
        count = resource_db.count_user_resources(tg_id)
        if count:
            resource_db.delete_all(tg_id)
            logger.warning(f"User {tg_id} deleted all resources ({count})")
            await transition_callback(
                callback=callback,
                state=state,
                bot=bot,
                text="Все ваши ресурсы удалены!",
                state_clear=True,
            )
        else:
            await transition_callback(
                callback=callback,
                state=state,
                bot=bot,
                text="У вас нет ресурсов...",
            )

    elif action == "del_account":
        user_db.delete(tg_id)
        logger.warning(f"User {tg_id} deleted account")
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
        state_clear=True,
    )


async def _export(
    callback: CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
    bot: Bot,
    mode: str,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id

    if mode == "urls":
        data = resource_db.export_urls(tg_id)
        filepath, count = write_urls_file(data, f"urls_{tg_id}.txt")
        filename = "urls_export.txt"
        caption = f"Экспортировано {count} ссылок"
    else:
        data = resource_db.export_data(tg_id)
        filepath, count = write_data_file(data, f"data_{tg_id}.json")
        filename = "data_export.json"
        caption = f"Экспортировано {count} ресурсов"

    if not data:
        await callback.answer("Нет ресурсов для экспорта", show_alert=True)
        return

    await state.clear()

    prompt_msg = await message.answer_document(
        document=types.FSInputFile(filepath, filename=filename),
        caption=caption,
    )

    await state.update_data(prompt_msg_id=prompt_msg.message_id)
    os.remove(filepath)
    await callback.answer()
