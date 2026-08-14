import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import BOT_TOKEN, PROXY_URL
from ui.tg_bot.handlers.admin import admin_router
from ui.tg_bot.handlers.common import common_router
from ui.tg_bot.handlers.resource import resource_router
from ui.tg_bot.middlewares.activity import ActivityMiddleware
from ui.tg_bot.middlewares.logger import LoggerMiddleware
from ui.tg_bot.middlewares.registration import RegistrationMiddleware
from ui.tg_bot.middlewares.user_update import UserUpdateMiddleware
from ui.tg_bot.middlewares.check_user_ban import CheckUserBanMiddleware
from ui.tg_bot.middlewares.append_db import DBMiddleware

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def main(user_db, resource_db, stats_db, user_service):
    bot = None
    try:
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN не указан!")

        if PROXY_URL:
            session = AiohttpSession(proxy=PROXY_URL)
            bot = Bot(
                token=BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                session=session,
            )
            logging.info(f"Бот запущен через прокси: {PROXY_URL}")
        else:
            bot = Bot(
                token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            logging.info("Бот запущен без прокси")

        dp = Dispatcher()
        dp.update.middleware(RegistrationMiddleware(user_db, user_service))
        dp.update.middleware(CheckUserBanMiddleware(user_db))
        dp.update.middleware(UserUpdateMiddleware(user_db, user_service))
        dp.update.middleware(ActivityMiddleware(user_db, resource_db))
        dp.update.middleware(LoggerMiddleware(logger))
        dp.update.middleware(DBMiddleware(user_db, resource_db, stats_db))
        dp.include_router(admin_router)
        dp.include_router(resource_router)
        dp.include_router(common_router)
        logging.info("Роутеры подключены")

        logging.info("Запуск поллинга...")
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if bot is not None:
            await bot.session.close()
            logging.info("Сессия закрыта")


def start_bot(user_db, resource_db, stats_db, user_service):
    asyncio.run(main(user_db, resource_db, stats_db, user_service))
