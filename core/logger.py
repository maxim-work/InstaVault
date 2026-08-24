import logging
import os
from logging.handlers import RotatingFileHandler

os.makedirs("logs", exist_ok=True)

FORMATTER = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _create_file_handler(
    filename: str,
    level: int = logging.INFO,
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        f"logs/{filename}",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(FORMATTER)
    handler.setLevel(level)
    return handler


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(FORMATTER)
    console.setLevel(logging.INFO)
    root.addHandler(console)

    error_handler = _create_file_handler("errors.log", logging.WARNING)
    root.addHandler(error_handler)

    aiogram_logger = logging.getLogger("aiogram")
    aiogram_handler = _create_file_handler("bot.log")
    aiogram_logger.addHandler(aiogram_handler)
    aiogram_logger.propagate = False

    app_logger = logging.getLogger("app")
    app_handler = _create_file_handler("app.log")
    app_logger.addHandler(app_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"app.{name}")
