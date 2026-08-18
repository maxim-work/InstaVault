from aiogram import Bot, F, Router, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from ui.tg_bot.callbacks.admin import AdminCallback
from ui.tg_bot.keyboards.admin import create_keyboard_admin_panel
from ui.tg_bot.middlewares.admin import AdminMiddleware
from ui.tg_bot.utils.transition import transition_callback, transition_to_message

admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


@admin_router.message(F.text == "Админ-панель")
@admin_router.message(Command("admin"))
async def cmd_admin_panel(message: types.Message, state: FSMContext, bot: Bot) -> None:
    await transition_to_message(
        message=message,
        state=state,
        bot=bot,
        text=_get_admin_panel_text(),
        reply_markup=create_keyboard_admin_panel(),
        state_clear=True,
    )


@admin_router.callback_query(AdminCallback.filter(F.action == "back_to_panel"))
async def back_to_admin_panel(
    callback: types.CallbackQuery, state: FSMContext, bot: Bot
):
    await transition_callback(
        callback=callback,
        state=state,
        bot=bot,
        text=_get_admin_panel_text(),
        reply_markup=create_keyboard_admin_panel(),
        state_clear=True,
    )
    await callback.answer()


async def show_admin_panel(target, state: FSMContext, bot: Bot):
    text = _get_admin_panel_text()
    markup = create_keyboard_admin_panel()

    if isinstance(target, types.Message):
        await transition_to_message(
            message=target,
            state=state,
            bot=bot,
            text=text,
            reply_markup=markup,
            state_clear=True,
        )
    elif isinstance(target, types.CallbackQuery):
        await transition_callback(
            callback=target,
            state=state,
            bot=bot,
            text=text,
            reply_markup=markup,
            state_clear=True,
        )


def _get_admin_panel_text() -> str:
    return (
        "Админ панель\n"
        "Выбор действия:\n"
        "1. Просмотр пользователей\n"
        "2. Поиск пользователя\n"
        "3. Рассылка сообщений\n"
        "4. Статистика\n"
        "5. Удалить всех пользователей"
    )
