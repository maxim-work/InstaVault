from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from config import MAX_SEARCH_QUERY_LENGTH, USERS_PER_PAGE
from data.db.users import UserDB
from ui.tg_bot.callbacks.admin import AdminCallback
from ui.tg_bot.handlers.admin.formatting import render_page_users, render_view_user
from ui.tg_bot.handlers.admin.panel import show_admin_panel
from ui.tg_bot.handlers.admin.users import show_users_page
from ui.tg_bot.keyboards.admin import (
    create_keyboard_page_users,
    create_keyboard_view_user,
    create_search_back_to_panel,
)
from ui.tg_bot.middlewares.admin import AdminMiddleware
from ui.tg_bot.states.admin import SearchState
from ui.tg_bot.utils.message import get_editable_message
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


@admin_router.callback_query(AdminCallback.filter(F.option == "2"))
async def cmd_search_user(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    await message.edit_text(
        "🔍 <b>Поиск пользователя</b>\n\nВведите TG ID или username пользователя:",
        reply_markup=create_search_back_to_panel(),
        parse_mode="HTML",
    )
    await state.update_data(prompt_msg_id=message.message_id)
    await state.set_state(SearchState.waiting_for_query)
    await callback.answer()


@admin_router.message(SearchState.waiting_for_query)
async def search_user_result(
    message: Message,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
) -> None:
    query = message.text
    if not query:
        return

    if len(query) > MAX_SEARCH_QUERY_LENGTH:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text="Слишком длинный запрос. Попробуйте ещё раз.",
        )
        return

    if query.isdigit():
        user = user_db.get_user(int(query))
        if user is None:
            await transition_to_message(
                message=message,
                state=state,
                bot=bot,
                text="Пользователь не найден. Попробуйте ещё раз:",
                reply_markup=create_search_back_to_panel(),
            )
            return

        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=render_view_user(user),
            reply_markup=create_keyboard_view_user(
                page=1, tg_id=user.tg_id, is_active=user.is_active
            ),
            parse_mode="HTML",
        )
        await state.clear()
        return

    users = user_db.search_users(query)

    if not users:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text="Пользователи не найдены. Попробуйте ещё раз:",
            reply_markup=create_search_back_to_panel(),
        )
        return

    if len(users) == 1:
        user = users[0]
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=render_view_user(user),
            reply_markup=create_keyboard_view_user(
                page=1, tg_id=user.tg_id, is_active=user.is_active, search=True
            ),
            parse_mode="HTML",
        )
        await state.clear()
        return

    await state.update_data(search_results=users)
    await show_users_page(message, users, 1, state, bot, edit=False)
    await state.set_state(SearchState.viewing_results)


@admin_router.callback_query(AdminCallback.filter(F.action == "back_to_search"))
async def back_to_search(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    data = await state.get_data()
    users = data.get("search_results", [])

    if not users:
        await show_admin_panel(callback, state, bot)
        await callback.answer()
        return

    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    page_users = users[:USERS_PER_PAGE]

    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text=render_page_users(page_users, 1, total_pages),
        reply_markup=create_keyboard_page_users(page_users, 1, total_pages),
        parse_mode="HTML",
    )
    await callback.answer()
