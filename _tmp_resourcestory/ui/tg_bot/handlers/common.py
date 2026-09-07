from aiogram import Bot, F, Router
from aiogram.filters.command import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import ADMIN_COMMANDS, ADMIN_IDS, USER_COMMANDS
from ui.tg_bot.keyboards.reply import (
    create_admin_start_keyboard,
    create_user_start_keyboard,
)
from ui.tg_bot.utils.transition import transition_to_message

common_router = Router()


@common_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None:
        return

    user = message.from_user
    name = user.full_name or user.first_name

    if user.id in ADMIN_IDS:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=f"Привет админ {name}",
            reply_markup=create_admin_start_keyboard(),
            state_clear=True,
        )
    else:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=f"Привет, {name}!",
            reply_markup=create_user_start_keyboard(),
            state_clear=True,
        )


@common_router.message(Command("help"))
@common_router.message(F.text == "Помощь")
async def cmd_help(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None:
        return

    if message.from_user.id in ADMIN_IDS:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=f"Вот наши команды: {ADMIN_COMMANDS}!",
            state_clear=True,
        )
    else:
        await transition_to_message(
            message=message,
            state=state,
            bot=bot,
            text=f"Вот наши команды: {USER_COMMANDS}!",
            state_clear=True,
        )


@common_router.message(~F.text.startswith("/"))
async def unknown_text(message: Message) -> None:
    await message.answer("Я пока не умею разговаривать на свободные темы...")


@common_router.message(F.text)
async def unknown_command(message: Message) -> None:
    await message.answer("Не знаю такой команды... Введите /help для списка команд.")
