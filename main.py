import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python main.py <tg|cli>")
        sys.exit(1)

    mode = sys.argv[1]

    from data.service_db import ResourceDB, UserDB, StatsDB
    from data.utils import start_db

    start_db()
    resource_db = ResourceDB()
    user_db = UserDB()
    stats_db = StatsDB()

    if mode == "tg":
        from core.service import UserService
        from ui.tg_bot.dispatcher import start_bot
        from core.scheduler import start_scheduler

        start_bot(user_db, resource_db, stats_db, UserService())
        start_scheduler(user_db, resource_db, stats_db)

    elif mode == "cli":
        from ui.cli.cli import start_cli

        start_cli(resource_db)
    else:
        print(f"Неизвестный режим: {mode}")
        sys.exit(1)
