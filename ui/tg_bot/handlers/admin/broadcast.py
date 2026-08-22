import asyncio

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from core.models.user import User
from data.db.users import UserDB
from ui.tg_bot.callbacks.admin import AdminCallback, ModerationCallback
from ui.tg_bot.handlers.admin.panel import show_admin_panel
from ui.tg_bot.handlers.admin.users import view_user
from ui.tg_bot.keyboards.admin import (
    create_back_to_panel_keyboard,
    create_confirm_keyboard,
)
from ui.tg_bot.middlewares.admin import AdminMiddleware
from ui.tg_bot.states.admin import NewsletterState
from ui.tg_bot.utils.message import get_editable_message
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


@admin_router.callback_query(AdminCallback.filter(F.option == "3"))
async def get_sending_message(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    data = await state.get_data()
    search_results = data.get("search_results")
    user: User | None = None
    page: int | None = None

    if callback_data.tg_id is not None:
        user = user_db.get_user(callback_data.tg_id)
        if user is None:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        page = callback_data.page or 1
        msg = f"Введите сообщение которое мы отправим {user.full_name}:"
    else:
        msg = "Введите сообщение которое мы отправим всем пользователям кроме админов:"

    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text=msg,
        state_clear=True,
    )

    if user is not None:
        await state.update_data(user=user, page=page, search_results=search_results)

    await state.set_state(NewsletterState.waiting_for_message)
    await callback.answer()


@admin_router.message(NewsletterState.waiting_for_message)
async def confirm_sending_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    if message.text is None:
        return

    data = await state.get_data()
    user = data.get("user")

    await state.update_data(message_text=message.text)

    if user:
        msg = f"Отправить это сообщение {user.full_name}?\n{message.text}"
    else:
        msg = f"Отправить это сообщение всем пользователям?\n{message.text}"

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=msg,
        reply_markup=create_confirm_keyboard(),
    )
    await state.set_state(NewsletterState.waiting_for_confirm)


@admin_router.callback_query(
    NewsletterState.waiting_for_confirm,
    AdminCallback.filter(),
)
async def sending_message(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext,
    bot: Bot,
    user_db: UserDB,
) -> None:
    message = get_editable_message(callback)
    if message is None:
        return

    data = await state.get_data()
    user = data.get("user")
    page = data.get("page")

    if callback_data.option == "no":
        await callback.answer("Отправка отменена", show_alert=True)
        if user is not None and page is not None:
            call_data = ModerationCallback(action="view", tg_id=user.tg_id, page=page)
            await view_user(callback, call_data, state, user_db)
        else:
            await show_admin_panel(callback, state, bot)
        return

    message_text = data.get("message_text")

    if message_text is None:
        await callback.answer("Сообщение не найдено", show_alert=True)
        if user is not None and page is not None:
            call_data = ModerationCallback(action="view", tg_id=user.tg_id, page=page)
            await view_user(callback, call_data, state, user_db)
        else:
            await show_admin_panel(callback, state, bot)
        return

    if user is not None and page is not None:
        if callback.from_user.id == user.tg_id:
            await callback.answer("Самому себе нельзя отправлять!", show_alert=True)
            call_data = ModerationCallback(action="view", tg_id=user.tg_id, page=page)
            await view_user(callback, call_data, state, user_db)
            return

    await message.delete()

    if user is not None and page is not None:
        try:
            await bot.send_message(chat_id=user.tg_id, text=message_text)
            msg = f"Сообщение: {message_text}, доставлено {user.full_name}!"
        except Exception:
            msg = (
                f"При отправке сообщения({message_text}) "
                f"пользователю({user.full_name}) произошла ошибка."
            )

        await bot.send_message(
            chat_id=callback.from_user.id,
            text=msg,
        )
    else:
        exclude_ids = [*ADMIN_IDS, callback.from_user.id]
        tg_ids = user_db.get_all_tg_ids_except(exclude_ids)
        total = len(tg_ids)
        sent = 0
        failed = 0

        status_msg = await bot.send_message(
            chat_id=callback.from_user.id,
            text=f"Отправка: 0/{total}",
        )

        for tg_id in tg_ids:
            try:
                await bot.send_message(chat_id=tg_id, text=message_text)
                sent += 1
            except Exception:
                failed += 1

            if sent % 10 == 0 or sent + failed == total:
                await status_msg.edit_text(
                    f"Отправка: {sent}/{total}\nУспешно: {sent}\nОшибок: {failed}"
                )
            await asyncio.sleep(0.05)

        await status_msg.edit_text(
            f"Отправка завершена\nУспешно: {sent}\nОшибок: {failed}",
            reply_markup=create_back_to_panel_keyboard(),
        )

    await state.clear()
    await callback.answer()
