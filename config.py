import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: Final[str | None] = os.getenv("BOT_TOKEN")
PROXY_URL: Final[str | None] = os.getenv("PROXY_URL")
YOUTUBE_API_KEY: Final[str | None] = os.getenv("YOUTUBE_API_KEY")

EXPORT_DIR: Final[Path] = Path("exports")
MAX_URL_LENGTH: Final[int] = 2048
USER_UPDATE_INTERVAL_HOURS: Final[int] = 12

USER_COMMANDS: Final[str] = "\n/start — начать\n/help — помощь"
ADMIN_COMMANDS: Final[str] = "\n/start — начать\n/help — помощь"

ADMIN_IDS: Final[list[int]] = [
    int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()
]

RESOURCES_PER_PAGE: Final[int] = 5
USERS_PER_PAGE: Final[int] = 5

EXIT_TEXTS: Final[set[str]] = {
    "/start",
    "/add",
    "Добавить ресурс",
    "/list",
    "Мои ресурсы",
    "/search",
    "Поиск",
    "/help",
    "Помощь",
    "/settings",
    "Ещё",
}

MESSAGES_PER_SECOND: Final[int] = 20
MESSAGES_PER_MINUTE: Final[int] = 600
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[int] = 2

ACTIVITY_UPDATE_INTERVAL_SECONDS: Final[int] = 120
