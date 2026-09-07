from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import EXIT_TEXTS
from core.logger import get_logger
from ui.tg_bot.utils.message import auto_delete
from ui.tg_bot.utils.tasks import create_background_task

logger = get_logger("fsm")


async def exit_fsm(message: Message, state: FSMContext) -> bool:
    if message.text not in EXIT_TEXTS:
        return False

    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")

    await state.clear()
    await message.delete()

    if prompt_msg_id is not None and message.bot is not None:
        try:
            await message.bot.delete_message(message.chat.id, prompt_msg_id)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Не удалось удалить сообщение %s в чате %s",
                prompt_msg_id,
                message.chat.id,
                exc_info=True,
            )

    msg = await message.answer("Предыдущая операция отменена, повторите пожалуйста команду.")

    if msg.bot is not None:
        create_background_task(auto_delete(msg.bot, msg.chat.id, msg.message_id, delay=3))

    return True
