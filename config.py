import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
EXPORT_DIR = Path("exports")
MAX_URL_LENGTH = 2048
USER_UPDATE_INTERVAL_HOURS = 12
USER_COMMANDS = "\n/start — начать\n/help — помощь"
ADMIN_COMMANDS = "\n/start — начать\n/help — помощь"
ADMIN_IDS = [
    int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()
]
RESOURCES_PER_PAGE = 5
USERS_PER_PAGE = 5
EXIT_TEXTS = {
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
