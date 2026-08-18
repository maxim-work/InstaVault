import os
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from core.models.stats import Statistics
from ui.tg_bot.callbacks.admin import AdminCallback
from ui.tg_bot.keyboards.admin import create_stats_keyboard
from ui.tg_bot.middlewares.admin import AdminMiddleware
from ui.tg_bot.utils.message import get_editable_message

admin_router = Router()
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())


@admin_router.callback_query(AdminCallback.filter(F.option == "4"))
async def show_statistics_period(
    callback: types.CallbackQuery,
    callback_data: AdminCallback,
    stats_db,
    state: FSMContext,
):
    message = get_editable_message(callback)
    if message is None:
        return

    period = callback_data.period

    if period == "save":
        data = await state.get_data()
        selected_period = data.get("stats_period", "week")
        label = _get_period_label(selected_period)
        stats = _get_statistics(stats_db, selected_period)
        text = _format_statistics_for_file(stats, label)
        filepath = f"/tmp/stats_{callback.from_user.id}.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)

        await message.answer_document(
            document=types.FSInputFile(filepath, filename="statistics.txt"),
            caption="Статистика",
        )

        os.remove(filepath)
        await callback.answer()
        return

    if period is None:
        period = "week"

    await state.update_data(stats_period=period)

    label = _get_period_label(period)
    stats = _get_statistics(stats_db, period)

    await message.edit_text(
        _format_statistics(stats, label),
        reply_markup=create_stats_keyboard(period),
    )
    await callback.answer()


def _get_statistics(stats_db, period: str) -> Statistics:
    today = datetime.now().strftime("%Y-%m-%d")

    if period == "week":
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == "month":
        since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period == "year":
        since = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    else:
        since = "1970-01-01"

    stats = stats_db.get_stats_for_period(since, today)
    active = stats_db.get_active_users_for_period(since, today)

    return Statistics(
        all_users=stats["total_users"],
        banned_users=stats["banned_users"],
        all_resources=stats["total_resources"],
        new_users_since=stats["new_users"],
        active_users_since=active,
    )


def _get_period_label(period: str) -> str:
    return {"week": "неделю", "month": "месяц", "year": "год", "all": "всё время"}[
        period
    ]


def _format_statistics_for_file(stats: Statistics, period_label: str) -> str:
    lines = [
        f"Статистика за {period_label}",
        "",
        "Пользователи:",
        f"  Всего: {stats.all_users}",
        f"  Забанено: {stats.banned_users}",
        "",
        "Ресурсы:",
        f"  Всего: {stats.all_resources}",
        "",
        f"Новые пользователи: {stats.new_users_since}",
        f"Активные пользователи: {stats.active_users_since}",
    ]
    return "\n".join(lines)


def _format_statistics(stats: Statistics, period_label: str) -> str:
    return (
        f"📊 <b>Статистика за {period_label}</b>\n\n"
        f"👥 <b>Пользователи</b>\n"
        f"Всего: {stats.all_users}\n"
        f"Забанено: {stats.banned_users}\n\n"
        f"📦 <b>Ресурсы</b>\n"
        f"Всего: {stats.all_resources}\n\n"
        f"🆕 <b>Новые пользователи:</b> {stats.new_users_since}\n"
        f"⚡ <b>Активные пользователи:</b> {stats.active_users_since}"
    )
