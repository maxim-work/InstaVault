import os

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.service_db import ResourceDB
from data_io.export_data import write_data_file, write_urls_file
from ui.tg_bot.callbacks.resource import SettingsCallback
from ui.tg_bot.utils.message import get_editable_message

export_router = Router()


@export_router.callback_query(SettingsCallback.filter(F.action == "export_urls"))
async def export_urls_callback(
    callback: CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
):
    await _export(callback, state, resource_db, "urls")


@export_router.callback_query(SettingsCallback.filter(F.action == "export_data"))
async def export_data_callback(
    callback: CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
):
    await _export(callback, state, resource_db, "data")


async def _export(
    callback: CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
    mode: str,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id

    if mode == "urls":
        data = resource_db.export_urls(tg_id)
        filepath, count = write_urls_file(data, f"urls_{tg_id}.txt")
        caption = f"Экспортировано {count} ссылок"
        filename = "urls_export.txt"
    else:
        data = resource_db.export_data(tg_id)
        filepath, count = write_data_file(data, f"data_{tg_id}.json")
        caption = f"Экспортировано {count} ресурсов"
        filename = "data_export.json"

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
