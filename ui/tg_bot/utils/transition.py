from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram import Bot

from ui.tg_bot.utils.message import get_editable_message, safe_delete_many


async def transition_to_message(
    message: Message,
    state: FSMContext,
    bot: Bot,
    text: str,
    reply_markup=None,
    parse_mode: str | None = None,
    disable_web_page_preview: bool = False,
    state_clear: bool = False,
) -> Message:
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")

    await safe_delete_many(
        bot,
        message.chat.id,
        *([prompt_msg_id] if prompt_msg_id else []),
        message.message_id,
    )

    if state_clear:
        await state.clear()

    new_msg = await message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )
    await state.update_data(prompt_msg_id=new_msg.message_id)
    return new_msg


async def transition_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    text: str,
    reply_markup=None,
    parse_mode: str | None = None,
    disable_web_page_preview: bool = False,
    state_clear: bool = False,
) -> Message | None:
    message = get_editable_message(callback)
    if message is None:
        return None

    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")

    await safe_delete_many(
        bot,
        message.chat.id,
        *([prompt_msg_id] if prompt_msg_id else []),
        message.message_id,
    )
    if state_clear:
        await state.clear()

    new_msg = await message.answer(
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )
    await state.update_data(prompt_msg_id=new_msg.message_id)
    return new_msg
