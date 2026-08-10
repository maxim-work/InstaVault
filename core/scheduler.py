from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler


scheduler = AsyncIOScheduler()


async def recalc_daily_stats(user_db, resource_db, stats_db):
    today = datetime.now().strftime("%Y-%m-%d")
    since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    new_users = user_db.count_new_users_since(since)
    new_resources = resource_db.count_all_resources()
    banned_users = user_db.count_banned_users()
    active_users = user_db.count_active_users_since(since)

    stats_db.upsert_daily_stats(
        date=today,
        new_users=new_users,
        active_users=active_users,
        new_resources=new_resources,
        banned_users=banned_users,
    )


def start_scheduler(user_db, resource_db, stats_db):
    scheduler.add_job(
        recalc_daily_stats,
        "cron",
        hour=3,
        minute=0,
        args=(user_db, resource_db, stats_db),
    )
    scheduler.start()
