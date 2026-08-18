import asyncio

from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from ui.tg_bot.callbacks.admin import AdminCallback
from ui.tg_bot.keyboards.admin import (
    create_back_to_panel_keyboard,
    create_confirm_keyboard,
)
from ui.tg_bot.middlewares.admin import AdminMiddleware
from ui.tg_bot.states.admin import NewsletterState
from ui.tg_bot.utils.message import get_editable_message
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

from ui.tg_bot.handlers.admin.panel import show_admin_panel

admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


@admin_router.callback_query(AdminCallback.filter(F.option == "3"))
async def get_sending_message(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
):
    message = get_editable_message(callback)
    if message is None:
        return

    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text="Введите сообщение которое мы отправим всем пользователям кроме админов:",
        state_clear=True,
    )
    await state.set_state(NewsletterState.waiting_for_message)
    await callback.answer()


@admin_router.message(NewsletterState.waiting_for_message)
async def confirm_sending_message(
    message: types.Message,
    state: FSMContext,
    bot: Bot,
):
    if message.text is None:
        return

    await state.update_data(message_text=message.text)

    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=f"Отправить это сообщение всем пользователям?\n{message.text}",
        reply_markup=create_confirm_keyboard(),
    )
    await state.set_state(NewsletterState.waiting_for_confirm)


@admin_router.callback_query(
    NewsletterState.waiting_for_confirm,
    AdminCallback.filter(),
)
async def sending_message(
    callback: types.CallbackQuery,
    callback_data: AdminCallback,
    state: FSMContext,
    bot: Bot,
    user_db,
):
    message = get_editable_message(callback)
    if message is None:
        return

    data = await state.get_data()

    if callback_data.option == "no":
        await callback.answer("Отправка отменена", show_alert=True)
        await show_admin_panel(callback, state, bot)
        return

    message_text = data.get("message_text")
    if message_text is None:
        await callback.answer("Сообщение не найдено", show_alert=True)
        await show_admin_panel(callback, state, bot)
        return

    await message.delete()

    tg_ids = user_db.get_all_tg_ids_except(ADMIN_IDS)
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
