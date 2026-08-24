from pathlib import Path

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from core.logger import get_logger
from core.models.resource import Resource
from data.db.resources import ResourceDB
from data_io.import_data import parse_data
from ui.tg_bot.callbacks.resource import pack_callback_data_list
from ui.tg_bot.keyboards.resource import create_kb_tags
from ui.tg_bot.states.resource import ImportState, ResourceFormState
from ui.tg_bot.utils.error_handler import handle_resource_error
from ui.tg_bot.utils.message import with_action_label
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

logger = get_logger("import_data")

import_data_router = Router()


@import_data_router.message(ImportState.waiting_for_data, F.document)
async def process_import_data(
    message: Message,
    state: FSMContext,
    resource_db: ResourceDB,
    bot: Bot,
) -> None:
    if message.document is None or message.from_user is None:
        return

    data = await state.get_data()
    mode = data.get("import_mode", "fast")
    tg_id = message.from_user.id

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text="Скачиваю файл...",
    )

    file = await bot.get_file(message.document.file_id)
    file_path = file.file_path

    if file_path is None:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text="Ошибка: не удалось получить файл.",
        )
        return

    imports_dir = Path("imports")
    imports_dir.mkdir(exist_ok=True)
    dest = str(imports_dir / f"{tg_id}_{message.document.file_name}")
    await bot.download_file(file_path, dest)

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text="Обрабатываю данные...",
    )

    try:
        resources = parse_data(dest)
    except Exception as e:
        await handle_resource_error(
            error=e,
            with_action_label=with_action_label,
            action="error_import",
            message=message,
            context={"user_id": tg_id},
        )
        await state.clear()
        return
    finally:
        Path(dest).unlink(missing_ok=True)

    if mode == "fast":
        try:
            count, total, errors = resource_db.import_data(resources, tg_id)
        except Exception as e:
            await handle_resource_error(
                error=e,
                with_action_label=with_action_label,
                action="error_import",
                message=message,
                context={"user_id": tg_id},
            )
            await state.clear()
            return

        logger.info(f"User imported {count}/{total} resources (fast mode)")

        msg = f"Импортировано {count} из {total} ресурсов."

        if errors:
            msg += "\n\nОшибки:\n" + "\n".join(errors[-10:])

        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=msg,
            disable_web_page_preview=True,
            state_clear=True,
        )

    elif mode == "detailed":
        await state.update_data(
            import_resources=resources,
            import_index=0,
            import_results={"count": 0, "errors": []},
        )
        await _start_next_resource(message, state, resource_db, bot)


async def _start_next_resource(
    message: Message,
    state: FSMContext,
    resource_db: ResourceDB,
    bot: Bot,
) -> None:
    data = await state.get_data()
    resources: list[Resource] = data["import_resources"]
    index: int = data["import_index"]
    total = len(resources)

    if message.from_user is None:
        return

    tg_id = message.from_user.id

    if index >= total:
        results = data["import_results"]
        msg = f"Импортировано {results['count']} из {total} ресурсов."

        if results["errors"]:
            msg += "\n\nОшибки:\n" + "\n".join(results["errors"][-10:])

        logger.info(f"User finished detailed import: {results['count']}/{total}")

        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=msg,
            disable_web_page_preview=True,
            state_clear=True,
        )
        return

    resource = resources[index]

    existing = resource_db.get_by_url(resource.url, tg_id)

    if existing is not None:
        results = data["import_results"]
        results["errors"].append(f"Дубликат: {resource.url}")
        await state.update_data(import_index=index + 1, import_results=results)
        await _start_next_resource(message, state, resource_db, bot)
        return

    await state.update_data(
        resource=resource,
        title=resource.title,
        edit_mode=True,
    )
    await state.set_state(ResourceFormState.waiting_for_save)

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=(
            f"[{index + 1}/{total}] {hbold(resource.title)}\n\n"
            f"Проверьте данные и сохраните или измените."
        ),
        reply_markup=create_kb_tags(
            ["Сохранить", "Изменить", "Отмена"],
            pack_callback_data_list(["save", "edit", "cancel"]),
        ),
        disable_web_page_preview=True,
    )


async def start_next_resource_from_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
    bot: Bot,
    index: int,
) -> None:
    data = await state.get_data()
    resources: list[Resource] = data["import_resources"]
    total = len(resources)
    tg_id = callback.from_user.id

    if index >= total:
        results = data["import_results"]
        msg = f"Импортировано {results['count']} из {total} ресурсов."

        if results["errors"]:
            msg += "\n\nОшибки:\n" + "\n".join(results["errors"][-10:])

        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text=msg,
            disable_web_page_preview=True,
            state_clear=True,
        )
        return

    resource = resources[index]

    existing = resource_db.get_by_url(resource.url, tg_id)

    if existing is not None:
        results = data["import_results"]
        results["errors"].append(f"Дубликат: {resource.url}")
        await state.update_data(import_index=index + 1, import_results=results)
        await start_next_resource_from_callback(
            callback,
            state,
            resource_db,
            bot,
            index + 1,
        )
        return

    await state.update_data(
        resource=resource,
        title=resource.title,
        edit_mode=True,
        import_index=index,
    )
    await state.set_state(ResourceFormState.waiting_for_save)

    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text=(
            f"[{index + 1}/{total}] {hbold(resource.title)}\n\n"
            f"{hbold('Проверьте данные перед сохранением')}\n\n"
            f"{hbold('Название:')} {resource.title}\n"
            f"{hbold('Тип:')} {resource.resource_type.label}\n"
            f"{hbold('Формат:')} {resource.kind.label}\n"
            f"{hbold('Тэги:')} {', '.join(resource.tags) if resource.tags else 'не указаны'}"
        ),
        reply_markup=create_kb_tags(
            ["Сохранить", "Изменить", "Отмена"],
            pack_callback_data_list(["save", "edit", "cancel"]),
        ),
        disable_web_page_preview=True,
    )
