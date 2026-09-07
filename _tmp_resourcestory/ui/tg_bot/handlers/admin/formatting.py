from datetime import UTC, datetime

from core.models.user import User


def render_page_users(
    users: list[User],
    page: int,
    total_pages: int,
) -> str:
    text = []

    text.append("👥 <b>СПИСОК ПОЛЬЗОВАТЕЛЕЙ</b>")
    text.append("")

    for i, user in enumerate(users):
        status_text = "Активен" if user.is_active else "Забанен"
        name = user.full_name or "Неизвестный"
        username = (
            f"@{user.username}" if user.username else "<i>username отсутствует</i>"
        )

        text.append(f"<b>{i + 1}. {name}</b>")
        text.append(f"   ├─ {username}")
        text.append(f"   └─ Статус: {status_text}")
        text.append("")

    text.append(f"📄 Страница <b>{page}</b> из <b>{total_pages}</b>")

    return "\n".join(text)


def render_view_user(user: User) -> str:
    status = "🟢 Активен" if user.is_active else "🔴 Забанен"
    username = f"@{user.username}" if user.username else "<i>отсутствует</i>"
    last_name = user.last_name or "<i>не указана</i>"

    text = [
        "👤 <b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ</b>",
        "",
        f"🆔 <b>TG ID:</b> <code>{user.tg_id}</code>",
        f"👨 <b>First name:</b> {user.first_name}",
        f"👥 <b>Last name:</b> {last_name}",
        f"📝 <b>Username:</b> {username}",
        f"📊 <b>Статус:</b> {status}",
        f"🕐 <b>Последняя активность:</b> {_format_datetime(user.last_active_at)}",
        f"📅 <b>Дата регистрации:</b> {_format_datetime(user.created_at)}",
    ]

    return "\n".join(text)


def _format_datetime(dt: datetime | str | None) -> str:
    if dt is None:
        return "<i>неизвестно</i>"

    try:
        if isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        return dt.strftime("%d.%m.%Y в %H:%M")
    except Exception:  # noqa: BLE001
        return str(dt)
