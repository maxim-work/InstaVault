from typing import cast

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.markdown import hbold
from core.logger import get_logger
from core.models.resource import Resource, ResourceKind, ResourceStatus, ResourceType
from data.db.resources import ResourceDB
from data.exceptions import DuplicateResourceError
from ui.tg_bot.callbacks.resource import (
    ResourceCallback,
    get_callback_data,
    pack_callback_data_list,
)
from ui.tg_bot.handlers.resource.import_data import start_next_resource_from_callback
from ui.tg_bot.handlers.resource.import_urls import start_next_url_from_callback
from ui.tg_bot.keyboards.resource import (
    create_kb_tags,
    create_kb_type,
    create_rating_keyboard,
    create_save_summary_keyboard,
)
from ui.tg_bot.states.resource import ResourceFormState
from ui.tg_bot.utils.message import get_editable_message, with_action_label
from ui.tg_bot.utils.transition import transition_to_message

logger = get_logger("resource_form")


async def _handle_import_next_step(
    callback: CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
    data: dict[str, object],
    results: dict[str, object],
    index: int,
    message: Message,
    bot: Bot,
) -> None:
    if "import_urls" in data:
        source_list = cast("list[object]", data["import_urls"])
        next_func = start_next_url_from_callback
    else:
        source_list = cast("list[object]", data["import_resources"])
        next_func = start_next_resource_from_callback

    if index >= len(source_list):
        label = "ссылок" if "import_urls" in data else "ресурсов"
        msg = f"Импортировано {results['count']} из {len(source_list)} {label}."

        if results["errors"]:
            msg += "\n\nОшибки:\n" + "\n".join(cast("list[str]", results["errors"])[-10:])

        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=msg,
            disable_web_page_preview=True,
            state_clear=True,
            parse_mode="HTML",
        )
        return

    await next_func(callback, state, resource_db, bot, index)


async def handle_form_actions(
    callback: CallbackQuery,
    callback_data: ResourceCallback,
    state: FSMContext,
    resource_db: ResourceDB,
    message: Message,
    bot: Bot,
) -> None:
    action = callback_data.action

    if action == "save":
        await _handle_save(callback, state, resource_db, message, bot)
    elif action == "cancel":
        await _handle_cancel(callback, state, resource_db, message, bot)
    elif action == "apply_new_tags":
        await _handle_apply_new_tags(callback, state)
    elif action == "keep_old_tags":
        await _handle_keep_old_tags(callback, state)
    elif action == "back":
        await show_save_summary(callback, state)
    elif action in (
        "change_type",
        "change_format",
        "change_status",
        "change_tags",
        "change_notes",
        "change_rating",
        "change_date",
    ):
        await _handle_change_field(callback_data, state, message)
    elif action == "edit":
        await show_edit_menu(state, message, bot)


async def show_edit_menu(
    state: FSMContext,
    message: Message,
    bot: Bot,
) -> None:
    data = await state.get_data()
    resource: Resource = data["resource"]
    is_edit = data.get("edit_mode", False)

    if is_edit:
        msg = (
            f"{hbold('Выберите, что хотите изменить')}\n\n"
            f"{hbold('Тип:')} {resource.resource_type.label}\n"
            f"{hbold('Формат:')} {resource.kind.label}\n"
            f"{hbold('Статус:')} {resource.status.label}\n"
            f"{hbold('Тэги:')} {', '.join(resource.tags) if resource.tags else 'не указаны'}\n"
            f"{hbold('Заметки:')} {resource.my_notes or 'нет'}\n"
            f"{hbold('Рейтинг:')} {resource.my_rating or '—'}/5\n"
            f"{hbold('Дата завершения:')} {resource.completed_at or 'не указана'}"
        )
        buttons = [
            "Тип",
            "Формат",
            "Статус",
            "Тэги",
            "Заметки",
            "Рейтинг",
            "Дата",
            "Назад",
        ]
        actions = [
            "change_type",
            "change_format",
            "change_status",
            "change_tags",
            "change_notes",
            "change_rating",
            "change_date",
            "back",
        ]
    else:
        msg = (
            f"{hbold('Выберите, что хотите изменить')}\n\n"
            f"{hbold('Тип:')} {resource.resource_type.label}\n"
            f"{hbold('Формат:')} {resource.kind.label}\n"
            f"{hbold('Тэги:')} {', '.join(resource.tags) if resource.tags else 'не указаны'}"
        )
        buttons = ["Тип", "Формат", "Тэги", "Назад"]
        actions = ["change_type", "change_format", "change_tags", "back"]

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=msg,
        reply_markup=create_kb_tags(buttons, pack_callback_data_list(actions)),
        parse_mode="HTML",
    )


async def show_save_summary(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    data = await state.get_data()
    resource: Resource = data["resource"]
    is_edit = data.get("edit_mode", False)
    msg = _build_save_summary_text(resource, is_edit)

    await message.edit_text(msg, reply_markup=create_save_summary_keyboard(), parse_mode="HTML")


async def show_save_summary_direct(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    data = await state.get_data()
    resource: Resource = data["resource"]
    is_edit = data.get("edit_mode", False)
    msg = _build_save_summary_text(resource, is_edit)

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=msg,
        reply_markup=create_save_summary_keyboard(),
        parse_mode="HTML",
    )


async def _handle_save(
    callback: CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
    message: Message,
    bot: Bot,
) -> None:
    data = await state.get_data()
    resource: Resource = data["resource"]
    is_edit = data.get("edit_mode", False)

    try:
        if is_edit:
            resource_db.update(resource)
            msg = (
                f"{hbold('Ресурс обновлён')}\n\n"
                f"{hbold('Название:')} {resource.title}\n"
                f"{hbold('Тип:')} {resource.resource_type.label}\n"
                f"{hbold('Формат:')} {resource.kind.label}\n"
                f"{hbold('Статус:')} {resource.status.label}\n"
                f"{hbold('Платформа:')} {resource.platform.label}\n"
                f"{hbold('Тэги:')} {', '.join(resource.tags) if resource.tags else 'не указаны'}\n"
                f"{hbold('Заметки:')} {resource.my_notes or 'нет'}\n"
                f"{hbold('Рейтинг:')} {resource.my_rating or '—'}/5\n"
                f"{hbold('Дата завершения:')} {resource.completed_at or 'нет'}"
            )
        else:
            resource_db.insert(resource)
            logger.info("Resource created")
            msg = (
                f"{hbold('Ресурс сохранён')}\n\n"
                f"{hbold('Название:')} {resource.title}\n"
                f"{hbold('Тип:')} {resource.resource_type.label}\n"
                f"{hbold('Формат:')} {resource.kind.label}\n"
                f"{hbold('Платформа:')} {resource.platform.label}\n"
                f"{hbold('Тэги:')} {', '.join(resource.tags) if resource.tags else 'не указаны'}\n"
                f"{hbold('Длительность:')} {resource.duration_display}\n"
                f"{hbold('Рейтинг:')} {resource.my_rating or '—'}/5\n"
            )
    except DuplicateResourceError:
        logger.warning("User %s tried to duplicate resource", callback.from_user.id)
        msg = "Ресурс с такой ссылкой уже существует"

    if "import_urls" in data or "import_resources" in data:
        results = data["import_results"]
        results["count"] += 1
        index = data["import_index"] + 1
        await state.update_data(import_index=index, import_results=results)
        await _handle_import_next_step(
            callback, state, resource_db, data, results, index, message, bot
        )
        return

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=msg,
        state_clear=True,
        parse_mode="HTML",
    )


async def _handle_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    resource_db: ResourceDB,
    message: Message,
    bot: Bot,
) -> None:
    data = await state.get_data()

    if "import_urls" in data or "import_resources" in data:
        results = data["import_results"]

        if "import_urls" in data:
            results["errors"].append(f"Пропущено: {data['import_urls'][data['import_index']]}")
        else:
            results["errors"].append(
                f"Пропущено: {data['import_resources'][data['import_index']].title}"
            )

        index = data["import_index"] + 1
        await state.update_data(import_index=index, import_results=results)
        await _handle_import_next_step(
            callback, state, resource_db, data, results, index, message, bot
        )
        return

    is_edit = data.get("edit_mode", False)

    if is_edit:
        msg = f"{hbold('Редактирование отменено')}\n\nИзменения не сохранены."
    else:
        msg = (
            f"{hbold('Добавление отменено')}\n\n"
            "Ресурс не сохранён. Чтобы начать заново, используйте /add"
        )

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=msg,
        state_clear=True,
        parse_mode="HTML",
    )


async def _handle_apply_new_tags(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    resource: Resource = data["resource"]
    new_tags = data.get("new_tags")
    resource.tags = new_tags if new_tags is not None else []

    await state.update_data(resource=resource, new_tags=None, old_tags=None)
    await show_save_summary(callback, state)


async def _handle_keep_old_tags(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.update_data(new_tags=None, old_tags=None)
    await show_save_summary(callback, state)


async def _handle_change_field(
    callback_data: ResourceCallback,
    state: FSMContext,
    message: Message,
) -> None:
    data = await state.get_data()
    await state.update_data(edit_target=callback_data.action)

    title = data.get("title", "")
    action = callback_data.action

    if action == "change_type":
        new_state = ResourceFormState.waiting_for_type
        text = with_action_label("edit", "Выберите новый тип:", title)
        markup = create_kb_type(list(ResourceType), get_callback_data)

    elif action == "change_format":
        new_state = ResourceFormState.waiting_for_format
        text = with_action_label("edit", "Выберите новый формат:", title)
        markup = create_kb_type(list(ResourceKind), get_callback_data)

    elif action == "change_status":
        new_state = ResourceFormState.waiting_for_save
        text = with_action_label("edit", "Выберите новый статус:", title)
        markup = create_kb_type(list(ResourceStatus), get_callback_data)

    elif action == "change_tags":
        new_state = ResourceFormState.waiting_for_new_tags
        text = with_action_label(
            "edit",
            "Отправьте новые теги.\n"
            "Если менять не нужно — введите что угодно, "
            "на следующем шаге можно вернуть старые.",
        )
        markup = None

    elif action == "change_notes":
        new_state = ResourceFormState.waiting_for_notes
        current = data["resource"].my_notes or "нет"
        text = with_action_label(
            "edit",
            f"Текущая заметка: {current}\n\nНапишите новую (или '-' для удаления):",
            title,
        )
        markup = None

    elif action == "change_rating":
        new_state = ResourceFormState.waiting_for_rating
        current = data["resource"].my_rating
        text = with_action_label(
            "edit",
            f"Текущий рейтинг: {current or '—'}/5\n\nВыберите новый:",
            title,
        )
        markup = create_rating_keyboard(current)

    elif action == "change_date":
        new_state = ResourceFormState.waiting_for_date
        current = data["resource"].completed_at or "не указана"
        text = with_action_label(
            "edit",
            f"Текущая дата: {current}\n\nВведите дату (ГГГГ-ММ-ДД или '-' для сброса):",
            title,
        )
        markup = None

    else:
        logger.warning("Unknown change action: %s", action)
        return

    await state.set_state(new_state)
    prompt_msg = await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    if isinstance(prompt_msg, Message):
        await state.update_data(prompt_msg_id=prompt_msg.message_id)


def _build_save_summary_text(resource: Resource, is_edit: bool) -> str:
    if is_edit:
        return (
            f"Проверьте изменения перед сохранением\n\n"
            f"{hbold('Название:')} {resource.title}\n"
            f"{hbold('Тип:')} {resource.resource_type.label}\n"
            f"{hbold('Формат:')} {resource.kind.label}\n"
            f"{hbold('Статус:')} {resource.status.label}\n"
            f"{hbold('Тэги:')} {', '.join(resource.tags) if resource.tags else 'не указаны'}\n"
            f"{hbold('Заметки:')} {resource.my_notes or 'нет'}\n"
            f"{hbold('Рейтинг:')} {resource.my_rating or '—'}/5\n"
            f"{hbold('Дата завершения:')} {resource.completed_at or 'не указана'}"
        )

    return (
        f"Проверьте данные перед сохранением\n\n"
        f"{hbold('Ссылка:')} {resource.url}\n"
        f"{hbold('Название:')} {resource.title}\n"
        f"{hbold('Тип:')} {resource.resource_type.label}\n"
        f"{hbold('Формат:')} {resource.kind.label}\n"
        f"{hbold('Тэги:')} {', '.join(resource.tags) if resource.tags else 'не указаны'}"
    )
