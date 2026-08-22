import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import PROXY_URL, YOUTUBE_API_KEY
from core.models.resource import Resource, ResourceType
from core.service import ResourceService
from data.exceptions import DuplicateResourceError
from data.db.resources import ResourceDB
from ui.tg_bot.callbacks.resource import get_callback_data
from ui.tg_bot.keyboards.resource import create_kb_type
from ui.tg_bot.states.resource import ImportState, ResourceFormState
from ui.tg_bot.utils.message import with_action_label
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

import_urls_router = Router()


@import_urls_router.message(ImportState.waiting_for_urls, F.document)
async def process_import_file(
    message: Message,
    state: FSMContext,
    resource_db: ResourceDB,
    bot: Bot,
    logger: logging.Logger,
):
    if message.from_user is None or message.document is None:
        return

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
    dest = str(imports_dir / f"urls_{message.from_user.id}.txt")
    await bot.download_file(file_path, dest)

    text = Path(dest).read_text(encoding="utf-8")

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text="Обрабатываю ссылки...",
    )

    await _handle_urls_text(
        message=message,
        state=state,
        resource_db=resource_db,
        logger=logger,
        text=text,
        bot=bot,
    )


@import_urls_router.message(ImportState.waiting_for_urls, F.text)
async def process_import_text(
    message: Message,
    state: FSMContext,
    resource_db: ResourceDB,
    logger: logging.Logger,
    bot: Bot,
):
    if message.from_user is None or message.text is None:
        return

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text="Обрабатываю ссылки...",
    )

    await _handle_urls_text(
        message=message,
        state=state,
        resource_db=resource_db,
        logger=logger,
        text=message.text,
        bot=bot,
    )


async def _handle_urls_text(
    message: Message,
    state: FSMContext,
    resource_db: ResourceDB,
    logger: logging.Logger,
    text: str,
    bot: Bot,
):
    urls = [line.strip() for line in text.split("\n") if line.strip()]

    if not urls:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text="Не найдено ссылок.",
            state_clear=True,
        )
        return

    data = await state.get_data()
    mode = data.get("import_mode", "fast")

    if mode == "fast":
        count = 0
        errors = []

        for url in urls:
            try:
                if not Resource._is_valid_url(url):
                    errors.append(f"Некорректная ссылка: {url}")
                    continue
                if message.from_user is None:
                    return

                resource = ResourceService.create_resource(
                    url=url,
                    tg_id=message.from_user.id,
                    resource_type=ResourceType.OTHER,
                    proxy=PROXY_URL,
                    youtube_api_key=YOUTUBE_API_KEY,
                )
                resource_db.insert(resource)
                count += 1

            except DuplicateResourceError:
                errors.append(f"Дубликат: {url}")
            except Exception as e:
                errors.append(str(e))

        msg = f"Импортировано {count} из {len(urls)} ссылок."
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
            import_urls=urls,
            import_index=0,
            import_results={"count": 0, "errors": []},
        )
        await _start_next_url(message, state, resource_db, logger, bot)


async def _start_next_url(
    message: Message,
    state: FSMContext,
    resource_db: ResourceDB,
    logger: logging.Logger,
    bot: Bot,
):
    data = await state.get_data()
    urls = data["import_urls"]
    index = data["import_index"]
    total = len(urls)

    if message.from_user is None:
        return

    tg_id = message.from_user.id

    if index >= total:
        results = data["import_results"]
        msg = f"Импортировано {results['count']} из {total} ссылок."
        if results["errors"]:
            msg += "\n\nОшибки:\n" + "\n".join(results["errors"][-10:])

        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=msg,
            disable_web_page_preview=True,
            state_clear=True,
        )
        return

    url = urls[index]

    existing = resource_db.get_by_url(url, tg_id)
    if existing is not None:
        results = data["import_results"]
        results["errors"].append(f"Дубликат: {url}")
        await state.update_data(import_index=index + 1, import_results=results)
        await _start_next_url(message, state, resource_db, logger, bot)
        return

    try:
        info = ResourceService.get_info_for_url(url, YOUTUBE_API_KEY, PROXY_URL)
        title = info["title"]
    except Exception:
        results = data["import_results"]
        results["errors"].append(f"Ошибка получения: {url}")
        await state.update_data(import_index=index + 1, import_results=results)
        await _start_next_url(message, state, resource_db, logger, bot)
        return

    await state.update_data(link=url, title=title)
    await state.set_state(ResourceFormState.waiting_for_type)

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=with_action_label(
            "add", f"[{index + 1}/{total}] {title}\n\nВыберите тип:"
        ),
        reply_markup=create_kb_type(list(ResourceType), get_callback_data),
    )


async def start_next_url_from_callback(
    callback,
    state: FSMContext,
    resource_db: ResourceDB,
    logger: logging.Logger,
    bot: Bot,
    index: int,
):
    data = await state.get_data()
    urls = data["import_urls"]
    total = len(urls)

    if index >= total:
        results = data["import_results"]
        msg = f"Импортировано {results['count']} из {total} ссылок."
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

    url = urls[index]

    try:
        info = ResourceService.get_info_for_url(url, YOUTUBE_API_KEY, PROXY_URL)
        title = info["title"]
    except Exception:
        results = data["import_results"]
        results["errors"].append(f"Ошибка получения: {url}")
        await state.update_data(import_index=index + 1, import_results=results)
        await start_next_url_from_callback(
            callback,
            state,
            resource_db,
            logger,
            bot,
            index + 1,
        )
        return

    await state.update_data(link=url, title=title, import_index=index)
    await state.set_state(ResourceFormState.waiting_for_type)

    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text=with_action_label(
            "add", f"[{index + 1}/{total}] {title}\n\nВыберите тип:"
        ),
        reply_markup=create_kb_type(list(ResourceType), get_callback_data),
    )
