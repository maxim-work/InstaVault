import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import BOT_TOKEN, PROXY_URL
from core.logger import get_logger, setup_logging
from core.service import UserService
from data.db.resources import ResourceDB
from data.db.stats import StatsDB
from data.db.users import UserDB
from ui.tg_bot.handlers.admin import admin_router
from ui.tg_bot.handlers.common import common_router
from ui.tg_bot.handlers.resource import resource_router
from ui.tg_bot.middlewares.activity import ActivityMiddleware
from ui.tg_bot.middlewares.append_db import DBMiddleware
from ui.tg_bot.middlewares.check_user_ban import CheckUserBanMiddleware
from ui.tg_bot.middlewares.logger import LoggerMiddleware
from ui.tg_bot.middlewares.registration import RegistrationMiddleware
from ui.tg_bot.middlewares.user_update import UserUpdateMiddleware

setup_logging()
logger = get_logger("dispatcher")


async def main(
    user_db: UserDB,
    resource_db: ResourceDB,
    stats_db: StatsDB,
    user_service: UserService,
) -> None:
    bot: Bot | None = None

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
            logger.info(f"Бот запущен через прокси: {PROXY_URL}")
        else:
            bot = Bot(
                token=BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
            logger.info("Бот запущен без прокси")

        dp = Dispatcher()
        dp.update.middleware(RegistrationMiddleware(user_db, user_service))
        dp.update.middleware(CheckUserBanMiddleware(user_db))
        dp.update.middleware(UserUpdateMiddleware(user_db, user_service))
        dp.update.middleware(ActivityMiddleware(user_db))
        dp.update.middleware(LoggerMiddleware(logger))
        dp.update.middleware(DBMiddleware(user_db, resource_db, stats_db))
        dp.include_router(admin_router)
        dp.include_router(resource_router)
        dp.include_router(common_router)
        logger.info("Роутеры подключены")

        logger.info("Запуск поллинга...")
        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if bot is not None:
            await bot.session.close()
            logger.info("Сессия закрыта")


def start_bot(
    user_db: UserDB,
    resource_db: ResourceDB,
    stats_db: StatsDB,
    user_service: UserService,
) -> None:
    asyncio.run(main(user_db, resource_db, stats_db, user_service))
