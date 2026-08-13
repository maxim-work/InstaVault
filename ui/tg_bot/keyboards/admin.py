from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ui.tg_bot.callbacks.admin import AdminCallback, ModerationCallback


def create_keyboard_admin_panel():
    builder = InlineKeyboardBuilder()
    builder.button(text="1", callback_data=AdminCallback(option="1").pack())
    builder.button(text="2", callback_data=AdminCallback(option="2").pack())
    builder.button(text="3", callback_data=AdminCallback(option="3").pack())
    builder.button(text="4", callback_data=AdminCallback(option="4").pack())
    builder.button(text="5", callback_data=AdminCallback(option="5").pack())
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def create_keyboard_page_users(users, page, total_page, compact_threshold: int = 3):
    builder = InlineKeyboardBuilder()
    nav_buttons = []
    user_buttons = []

    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀ Назад",
                callback_data=AdminCallback(action="prev", page=page - 1).pack(),
            )
        )
    if page < total_page:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперёд ▶",
                callback_data=AdminCallback(action="next", page=page + 1).pack(),
            )
        )

    for i, user in enumerate(users):
        user_buttons.append(
            InlineKeyboardButton(
                text=str(i + 1),
                callback_data=ModerationCallback(
                    action="view", tg_id=user.tg_id, page=page
                ).pack(),
            )
        )

    compact = len(users) <= compact_threshold
    if compact:
        all_buttons = []
        if page > 1:
            all_buttons.append(nav_buttons[0])
        all_buttons.extend(user_buttons)
        if page < total_page:
            all_buttons.append(nav_buttons[-1])
        for btn in all_buttons:
            builder.button(text=btn.text, callback_data=btn.callback_data)
        builder.adjust(len(all_buttons))
    else:
        for btn in user_buttons:
            builder.button(text=btn.text, callback_data=btn.callback_data)
        builder.adjust(3)

        if nav_buttons:
            builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=AdminCallback(action="back_to_panel").pack(),
        )
    )

    return builder.as_markup()


def create_keyboard_view_user(page, is_active, tg_id, search: bool = False):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Забанить" if is_active else "Разбанить",
        callback_data=ModerationCallback(
            action="ban" if is_active else "unban", tg_id=tg_id, page=page
        ).pack(),
    )
    builder.button(
        text="Удалить",
        callback_data=ModerationCallback(
            action="confirm_delete", tg_id=tg_id, page=page
        ).pack(),
    )
    if search:
        builder.button(
            text="Назад", callback_data=AdminCallback(action="back_to_search").pack()
        )
    else:
        builder.button(
            text="Назад", callback_data=AdminCallback(action="page", page=page).pack()
        )
    builder.adjust(1, 2)
    return builder.as_markup()


def create_keyboard_confirm_delete(page, tg_id):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Да",
        callback_data=ModerationCallback(
            action="delete", tg_id=tg_id, page=page
        ).pack(),
    )
    builder.button(
        text="Нет",
        callback_data=ModerationCallback(action="view", tg_id=tg_id, page=page).pack(),
    )

    builder.adjust(2)
    return builder.as_markup()


def create_keyboard_confirm_delete_all():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Да",
        callback_data=AdminCallback(action="delete_all").pack(),
    )
    builder.button(
        text="Нет",
        callback_data=AdminCallback(action="back_to_panel").pack(),
    )

    builder.adjust(2)
    return builder.as_markup()


def create_stats_keyboard(current: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    periods = [
        ("Неделя", "week"),
        ("Месяц", "month"),
        ("Год", "year"),
        ("Всё время", "all"),
    ]

    for label, period in periods:
        if period == current:
            builder.button(
                text=f"✅ {label}",
                callback_data=AdminCallback(option="4", period=period).pack(),
            )
        else:
            builder.button(
                text=label,
                callback_data=AdminCallback(option="4", period=period).pack(),
            )

    builder.button(
        text="Сохранить в файл",
        callback_data=AdminCallback(option="4", period="save").pack(),
    )
    builder.button(
        text="Назад", callback_data=AdminCallback(action="back_to_panel").pack()
    )
    builder.adjust(4, 1, 1)
    return builder.as_markup()


def create_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Да",
        callback_data=AdminCallback(action="confirm_send", option="yes").pack(),
    )
    builder.button(
        text="Нет",
        callback_data=AdminCallback(action="confirm_send", option="no").pack(),
    )
    builder.adjust(2)
    return builder.as_markup()


def create_back_to_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="В админ-панель",
        callback_data=AdminCallback(action="back_to_panel").pack(),
    )
    return builder.as_markup()
