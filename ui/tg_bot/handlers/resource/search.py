from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from config import RESOURCES_PER_PAGE
from core.models.resource import Resource
from data.db.resources import ResourceDB
from data.filter import ResourceFilter
from ui.tg_bot.callbacks.resource import SearchCallback
from ui.tg_bot.handlers.resource.form import show_save_summary
from ui.tg_bot.keyboards.resource import (
    create_confirm_delete_res_keyboard,
    create_search_keyboard,
    create_view_res_search_keyboards,
)
from ui.tg_bot.states.resource import ResourceFormState, SearchState
from ui.tg_bot.utils.fsm import exit_fsm
from ui.tg_bot.utils.message import get_editable_message, with_action_label
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

search_router = Router()


@search_router.message(Command("search"))
@search_router.message(F.text == "Поиск")
async def cmd_search(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=with_action_label("search", "Введите ключевые слова для поиска:"),
        state_clear=True,
    )
    await state.set_state(SearchState.waiting_for_search)


@search_router.message(SearchState.waiting_for_search)
async def process_search(
    message: Message,
    state: FSMContext,
    bot: Bot,
    resource_db: ResourceDB,
) -> None:
    if message.from_user is None:
        return
    if message.text is None:
        return

    if await exit_fsm(message, state):
        return

    keywords = message.text.strip()

    if len(keywords) > 100:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text="Слишком длинный запрос. Максимум 100 символов.",
        )
        return

    tg_id = message.from_user.id
    f = ResourceFilter(tg_id=tg_id, keywords=keywords, limit=10)
    results = resource_db.search(tg_id=tg_id, resource_filter=f)

    if not results:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text="Ничего не найдено.",
            state_clear=True,
        )
        return

    await state.update_data(search_results=results)

    total_pages = (len(results) + RESOURCES_PER_PAGE - 1) // RESOURCES_PER_PAGE
    page_results = results[:RESOURCES_PER_PAGE]

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=_render_search_results(page_results, 1, total_pages),
        reply_markup=create_search_keyboard(page_results, 1, total_pages),
    )


@search_router.callback_query(SearchCallback.filter())
async def search_callback(
    callback: types.CallbackQuery,
    callback_data: SearchCallback,
    state: FSMContext,
    resource_db: ResourceDB,
    bot: Bot,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    data = await state.get_data()
    results: list[tuple[Resource, int]] = data.get("search_results", [])
    action = callback_data.action
    page = callback_data.page or 1
    resource_id = callback_data.resource_id

    if action in ("page", "prev", "next"):
        total = (len(results) + RESOURCES_PER_PAGE - 1) // RESOURCES_PER_PAGE
        start = (page - 1) * RESOURCES_PER_PAGE
        page_results = results[start : start + RESOURCES_PER_PAGE]

        await message.edit_text(
            _render_search_results(page_results, page, total),
            reply_markup=create_search_keyboard(page_results, page, total),
        )

    elif action == "results":
        total = (len(results) + RESOURCES_PER_PAGE - 1) // RESOURCES_PER_PAGE
        page_results = results[:RESOURCES_PER_PAGE]

        await message.edit_text(
            _render_search_results(page_results, 1, total),
            reply_markup=create_search_keyboard(page_results, 1, total),
        )

    elif action == "view":
        if resource_id is None:
            await callback.answer("Ошибка: ресурс не указан", show_alert=True)
            return
        tg_id = callback.from_user.id
        res = resource_db.get_resource(resource_id, tg_id)
        if res is None:
            await callback.answer("Ресурс не найден", show_alert=True)
            return
        if res.id is None:
            return

        await message.edit_text(
            _format_resource_detail(res),
            reply_markup=create_view_res_search_keyboards(res.id),
        )

    elif action == "confirm_delete":
        if resource_id is None:
            await callback.answer("Ошибка: ресурс не указан", show_alert=True)
            return
        res = resource_db.get_resource(resource_id, callback.from_user.id)
        if res is None:
            await callback.answer("Ресурс не найден", show_alert=True)
            return
        if res.id is None:
            return

        await message.edit_text(
            f"Удалить ресурс «{res.title}»?",
            reply_markup=create_confirm_delete_res_keyboard(res.id),
        )

    elif action == "delete":
        if resource_id is None:
            await callback.answer("Ошибка: ресурс не указан", show_alert=True)
            return
        resource_db.delete(resource_id, callback.from_user.id)
        await callback.answer("Удалено")

        results = [(r, s) for r, s in results if r.id != resource_id]
        await state.update_data(search_results=results)

        if not results:
            await transition_callback(
                callback=callback,
                state=state,
                bot=bot,
                text="Ресурс удалён. Больше нет результатов поиска.",
                state_clear=True,
            )
            return

        total = (len(results) + RESOURCES_PER_PAGE - 1) // RESOURCES_PER_PAGE
        page_results = results[:RESOURCES_PER_PAGE]

        await transition_callback(
            callback=callback,
            state=state,
            bot=bot,
            text=_render_search_results(page_results, 1, total),
            reply_markup=create_search_keyboard(page_results, 1, total),
        )

    elif action == "edit":
        if resource_id is None:
            await callback.answer("Ошибка: ресурс не указан", show_alert=True)
            return
        tg_id = callback.from_user.id
        r = resource_db.get_resource(resource_id, tg_id)
        if r is None:
            await callback.answer("Ресурс не найден", show_alert=True)
            return

        await state.update_data(resource=r, title=r.title, edit_mode=True)
        await state.set_state(ResourceFormState.waiting_for_save)

        await show_save_summary(callback, state)

    await callback.answer()


def _render_search_results(
    results: list[tuple[Resource, int]],
    page: int,
    total_pages: int,
) -> str:
    lines = [f"{hbold('Результаты поиска:')}"]

    for i, (r, _) in enumerate(results, 1):
        lines.append(f"{i}. {r.title} — {r.resource_type.label}")

    if total_pages > 1:
        lines.append(f"\nСтраница {page}/{total_pages}")

    return "\n".join(lines)


def _format_resource_detail(r: Resource) -> str:
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
