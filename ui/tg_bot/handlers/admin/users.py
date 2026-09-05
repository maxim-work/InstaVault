from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, USERS_PER_PAGE
from core.logger import get_logger
from core.models.user import User
from data.db.users import UserDB
from ui.tg_bot.callbacks.admin import AdminCallback, ModerationCallback
from ui.tg_bot.handlers.admin.formatting import render_page_users, render_view_user
from ui.tg_bot.handlers.admin.panel import show_admin_panel
from ui.tg_bot.keyboards.admin import (
    create_keyboard_confirm_delete,
    create_keyboard_confirm_delete_all,
    create_keyboard_page_users,
    create_keyboard_view_user,
)
from ui.tg_bot.middlewares.admin import AdminMiddleware
from ui.tg_bot.utils.message import get_editable_message, with_action_label
from ui.tg_bot.utils.transition import transition_to_message

logger = get_logger("users")

admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


@admin_router.callback_query(AdminCallback.filter(F.option == "1"))
async def cmd_view_users(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    users = user_db.get_all_users()
    await show_users_page(message, users, 1, state, bot, edit=True)
    await callback.answer()


@admin_router.callback_query(AdminCallback.filter(F.action.in_(["prev", "page", "next"])))
async def handle_pagination(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None or callback_data.page is None:
        return

    users = user_db.get_all_users()
    await show_users_page(message, users, callback_data.page, state, bot, edit=True)
    await callback.answer()


@admin_router.callback_query(ModerationCallback.filter(F.action == "view"))
async def cmd_view_user(
    callback: CallbackQuery,
    callback_data: ModerationCallback,
    state: FSMContext,
    user_db: UserDB,
) -> None:
    await view_user(callback, callback_data, state, user_db)


@admin_router.callback_query(ModerationCallback.filter(F.action == "confirm_delete"))
async def confirm_delete_user(
    callback: CallbackQuery,
    callback_data: ModerationCallback,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    user = user_db.get_user(callback_data.tg_id)
    if user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await message.edit_text(
        f"🗑 <b>Удалить пользователя?</b>\n\n"
        f"👤 {user.full_name}\n"
        f"🆔 <code>{user.tg_id}</code>\n\n"
        f"<i>Это действие нельзя отменить!</i>\n"
        f"<i>Все его ресурсы тоже будут удалены!</i>",
        reply_markup=create_keyboard_confirm_delete(page=callback_data.page, tg_id=user.tg_id),
        parse_mode="HTML",
    )
    await callback.answer()


@admin_router.callback_query(ModerationCallback.filter(F.action == "delete"))
async def delete_user(
    callback: CallbackQuery,
    callback_data: ModerationCallback,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    user = user_db.get_user(callback_data.tg_id)
    user_name = user.full_name if user else "Неизвестный"

    if callback_data.tg_id == callback.from_user.id:
        await callback.answer("Нельзя удалять самого себя", show_alert=True)
        return

    user_db.delete(callback_data.tg_id)
    await callback.answer(f"Пользователь {user_name} удален", show_alert=True)
    logger.info("Admin %s delete user(%s)", callback.from_user.id, callback_data.tg_id)

    data = await state.get_data()
    search_results = data.get("search_results")

    if search_results:
        search_results = [u for u in search_results if u.tg_id != callback_data.tg_id]
        if not search_results:
            await message.edit_text("Пользователей больше нет")
            await state.clear()
            return

        await state.update_data(search_results=search_results)
        await show_users_page(message, search_results, 1, state, bot, edit=True)
        return

    users = user_db.get_all_users()
    page = callback_data.page or 1

    if not users:
        await message.edit_text("Пользователей больше нет")
        return

    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    start = (page - 1) * USERS_PER_PAGE
    page_users = users[start : start + USERS_PER_PAGE]

    if not page_users and page > 1:
        page -= 1
        start = (page - 1) * USERS_PER_PAGE
        page_users = users[start : start + USERS_PER_PAGE]

    await message.edit_text(
        render_page_users(page_users, page, total_pages),
        reply_markup=create_keyboard_page_users(page_users, page, total_pages),
        parse_mode="HTML",
    )


@admin_router.callback_query(ModerationCallback.filter(F.action.in_(["ban", "unban"])))
async def toggle_user_ban(
    callback: CallbackQuery,
    callback_data: ModerationCallback,
    bot: Bot,
    user_db: UserDB,
    state: FSMContext,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    user = user_db.get_user(callback_data.tg_id)
    if user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    if callback_data.tg_id == callback.from_user.id:
        await callback.answer("Нельзя банить самого себя", show_alert=True)
        return

    if callback_data.action == "ban":
        user_db.ban(callback_data.tg_id)
        logger.info("Admin %s ban user(%s)", callback.from_user.id, callback_data.tg_id)
        action_text = "забанен"
        await bot.send_message(
            chat_id=callback_data.tg_id,
            text=with_action_label("info", "Вы были забанены админом!"),
        )
    else:
        user_db.unban(callback_data.tg_id)
        logger.info("Admin %s unban user(%s)", callback.from_user.id, callback_data.tg_id)
        action_text = "разбанен"
        await bot.send_message(
            chat_id=callback_data.tg_id,
            text=with_action_label("info", "Вы были разбанены админом!"),
        )

    await callback.answer(f"Пользователь {action_text}", show_alert=True)

    data = await state.get_data()
    search_results = data.get("search_results")
    is_search = search_results is not None

    user = user_db.get_user(callback_data.tg_id)
    if user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await message.edit_text(
        render_view_user(user),
        reply_markup=create_keyboard_view_user(
            page=callback_data.page or 1,
            tg_id=user.tg_id,
            is_active=user.is_active,
            search=is_search,
        ),
        parse_mode="HTML",
    )


@admin_router.callback_query(AdminCallback.filter(F.option == "5"))
async def confirm_delete_all_users(
    callback: CallbackQuery,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    users = user_db.get_all_users()
    if not users:
        await callback.answer("Нет пользователей для удаления", show_alert=True)
        return

    await message.edit_text(
        f"⚠️ <b>Удалить ВСЕХ пользователей?</b>\n\n"
        f"Количество: {len(users)}\n\n"
        f"<i>Это действие нельзя отменить!</i>",
        reply_markup=create_keyboard_confirm_delete_all(),
        parse_mode="HTML",
    )
    await callback.answer()


@admin_router.callback_query(AdminCallback.filter(F.action == "delete_all"))
async def cmd_delete_all_users(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    exclude_ids = [*ADMIN_IDS, callback.from_user.id]
    users = user_db.get_all_tg_ids_except(exclude_ids)
    count = len(users)

    if not users:
        await callback.answer("Нет пользователей для удаления", show_alert=True)
        return

    user_db.delete_all_users_except(exclude_ids)

    await callback.answer(f"Удалено {count} пользователей", show_alert=True)
    logger.warning("Admin %s delete all users", callback.from_user.id)

    await show_admin_panel(callback, state, bot)


async def show_users_page(
    message: Message,
    users: list[User],
    page: int,
    state: FSMContext,
    bot: Bot,
    edit: bool = False,
) -> None:
    if not users:
        if edit:
            await message.edit_text("Нет зарегистрированных пользователей")
        else:
            await transition_to_message(
                message=message,
                state=state,
                bot=bot,
                text="Нет зарегистрированных пользователей",
            )
        return

    page_users, total_pages = _get_users_page(users, page)
    text = render_page_users(page_users, page, total_pages)
    markup = create_keyboard_page_users(page_users, page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=text,
            reply_markup=markup,
            parse_mode="HTML",
        )


async def view_user(
    callback: CallbackQuery,
    callback_data: ModerationCallback,
    state: FSMContext,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    user = user_db.get_user(callback_data.tg_id)
    if user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    data = await state.get_data()
    search_results = data.get("search_results")
    is_search = search_results is not None

    await message.edit_text(
        render_view_user(user),
        reply_markup=create_keyboard_view_user(
            page=callback_data.page or 1,
            tg_id=user.tg_id,
            is_active=user.is_active,
            search=is_search,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


def _get_users_page(
    users: list[User],
    page: int,
) -> tuple[list[User], int]:
    total_pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    start = (page - 1) * USERS_PER_PAGE
    page_users = users[start : start + USERS_PER_PAGE]
    return page_users, total_pages
