from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold

from config import RESOURCES_PER_PAGE
from ui.tg_bot.callbacks.resource import ResourceCallback
from ui.tg_bot.keyboards.resource import create_list_keyboard
from ui.tg_bot.states.resource import ResourceFormState
from ui.tg_bot.utils.message import get_editable_message
from ui.tg_bot.utils.transition import transition_to_message
from ui.tg_bot.handlers.resource.form import show_save_summary

list_router = Router()


@list_router.message(Command("list"))
@list_router.message(F.text == "Мои ресурсы")
async def cmd_list(message: Message, state: FSMContext, resource_db, bot: Bot):
    if message.from_user is None:
        return

    resources = resource_db.get_all_resources(message.from_user.id)

    if not resources:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text="У вас пока нет сохранённых ресурсов.",
            state_clear=True,
        )
        return

    total_pages = (len(resources) + RESOURCES_PER_PAGE - 1) // RESOURCES_PER_PAGE
    page_resources = resources[:RESOURCES_PER_PAGE]

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=_render_resource_list(page_resources, 1, total_pages),
        reply_markup=create_list_keyboard(page_resources, 1, total_pages),
        state_clear=True,
    )


@list_router.callback_query(
    ResourceCallback.filter(F.action.in_(["page", "prev", "next"]))
)
async def handle_pagination(
    callback: CallbackQuery,
    callback_data: ResourceCallback,
    resource_db,
):
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id
    page = callback_data.page or 1

    resources = resource_db.get_all_resources(tg_id)
    total = (len(resources) + RESOURCES_PER_PAGE - 1) // RESOURCES_PER_PAGE
    start = (page - 1) * RESOURCES_PER_PAGE
    page_resources = resources[start : start + RESOURCES_PER_PAGE]

    await message.edit_text(
        _render_resource_list(page_resources, page, total),
        reply_markup=create_list_keyboard(page_resources, page, total),
    )
    await callback.answer()


@list_router.callback_query(ResourceCallback.filter(F.action == "view"))
async def handle_view_resource(
    callback: CallbackQuery,
    callback_data: ResourceCallback,
    resource_db,
):
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id
    resource_id = callback_data.resource_id
    page = callback_data.page or 1

    if resource_id is None:
        await callback.answer("Ошибка: ресурс не указан", show_alert=True)
        return

    r = resource_db.get_resource(resource_id, tg_id)
    if r is None:
        await callback.answer("Ресурс не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(
        text="Редактировать",
        callback_data=ResourceCallback(action="edit", resource_id=r.id).pack(),
    )
    builder.button(
        text="Удалить",
        callback_data=ResourceCallback(
            action="confirm_delete", resource_id=r.id, page=page
        ).pack(),
    )
    builder.button(
        text="К списку",
        callback_data=ResourceCallback(action="page", page=1).pack(),
    )
    builder.adjust(2, 1)

    await message.edit_text(
        _format_resource_detail(r), reply_markup=builder.as_markup()
    )
    await callback.answer()


@list_router.callback_query(ResourceCallback.filter(F.action == "edit"))
async def handle_edit_resource(
    callback: CallbackQuery,
    callback_data: ResourceCallback,
    state: FSMContext,
    resource_db,
):
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id
    resource_id = callback_data.resource_id

    if resource_id is None:
        await callback.answer("Ошибка: ресурс не указан", show_alert=True)
        return

    r = resource_db.get_resource(resource_id, tg_id)
    if r is None:
        await callback.answer("Ресурс не найден", show_alert=True)
        return

    await state.update_data(
        resource=r,
        title=r.title,
        edit_mode=True,
    )
    await state.set_state(ResourceFormState.waiting_for_save)
    await show_save_summary(callback, state)
    await callback.answer()


@list_router.callback_query(ResourceCallback.filter(F.action == "confirm_delete"))
async def handle_confirm_delete(
    callback: CallbackQuery,
    callback_data: ResourceCallback,
    resource_db,
):
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id
    resource_id = callback_data.resource_id
    page = callback_data.page or 1

    if resource_id is None:
        await callback.answer("Ошибка: ресурс не указан", show_alert=True)
        return

    r = resource_db.get_resource(resource_id, tg_id)
    if r is None:
        await callback.answer("Ресурс не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(
        text="Да, удалить",
        callback_data=ResourceCallback(
            action="delete", resource_id=resource_id, page=page
        ).pack(),
    )
    builder.button(
        text="Нет",
        callback_data=ResourceCallback(
            action="view", resource_id=resource_id, page=page
        ).pack(),
    )
    builder.adjust(2)

    await message.edit_text(
        f"Удалить ресурс «{r.title}»?",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@list_router.callback_query(ResourceCallback.filter(F.action == "delete"))
async def handle_delete_resource(
    callback: CallbackQuery,
    callback_data: ResourceCallback,
    resource_db,
):
    message = get_editable_message(callback)
    if message is None:
        return

    tg_id = callback.from_user.id
    resource_id = callback_data.resource_id
    page = callback_data.page or 1

    if resource_id is None:
        await callback.answer("Ошибка: ресурс не указан", show_alert=True)
        return

    resource_db.delete(resource_id, tg_id)
    await callback.answer("Удалено")

    resources = resource_db.get_all_resources(tg_id)

    if not resources:
        await message.edit_text("Ресурс удалён. У вас больше нет сохранённых ресурсов.")
        return

    total = (len(resources) + RESOURCES_PER_PAGE - 1) // RESOURCES_PER_PAGE

    start = (page - 1) * RESOURCES_PER_PAGE
    page_resources = resources[start : start + RESOURCES_PER_PAGE]

    if not page_resources and page > 1:
        page -= 1
        start = (page - 1) * RESOURCES_PER_PAGE
        page_resources = resources[start : start + RESOURCES_PER_PAGE]

    await message.edit_text(
        _render_resource_list(page_resources, page, total),
        reply_markup=create_list_keyboard(page_resources, page, total),
    )
    await callback.answer()


def _render_resource_list(resources: list, page: int, total_pages: int) -> str:
    lines = [f"{hbold('Ваши ресурсы:')}"]
    for i, r in enumerate(resources, 1):
        lines.append(f"{i}. {r.title} — {r.resource_type.label}")
    if total_pages > 1:
        lines.append(f"\nСтраница {page}/{total_pages}")
    return "\n".join(lines)


def _format_resource_detail(r) -> str:
    return (
        f"{hbold(r.title)}\n\n"
        f"{hbold('Ссылка:')} {r.url}\n"
        f"{hbold('Тип:')} {r.resource_type.label}\n"
        f"{hbold('Формат:')} {r.kind.label}\n"
        f"{hbold('Платформа:')} {r.platform.label}\n"
        f"{hbold('Статус:')} {r.status.label}\n"
        f"{hbold('Тэги:')} {', '.join(r.tags) if r.tags else 'не указаны'}\n"
        f"{hbold('Длительность:')} {r.duration_display}\n"
        f"{hbold('Рейтинг:')} {r.my_rating or '—'}\n"
    )
