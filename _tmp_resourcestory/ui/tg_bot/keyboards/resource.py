from collections.abc import Callable
from typing import Any, TypeVar

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import RESOURCES_PER_PAGE
from core.models.resource import Resource
from ui.tg_bot.callbacks.resource import (
    ResourceCallback,
    SearchCallback,
    SettingsCallback,
    pack_callback_data_list,
)

T = TypeVar("T")


def create_kb_type(
    options: list[Any],
    get_cb: Callable[[str], str],
    len_row: int = 2,
) -> InlineKeyboardMarkup:
    return _build_keyboard(
        [(opt.label, get_cb(opt.code)) for opt in options],
        len_row,
    )


def create_kb_tags(
    labels: list[str],
    data: list[str],
    len_row: int = 2,
) -> InlineKeyboardMarkup:
    return _build_keyboard(list(zip(labels, data, strict=True)), len_row)


def create_list_keyboard(
    resources: list[Resource],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    return _build_paginated_keyboard(
        items=resources,
        page=page,
        total_pages=total_pages,
        get_text=lambda i, _: str(i + 1),
        get_callback=lambda flag, val: (
            ResourceCallback(action="page", page=val).pack()
            if flag == "nav"
            else ResourceCallback(
                action="view",
                resource_id=val.id if isinstance(val, Resource) else None,
                page=page,
            ).pack()
        ),
    )


def create_search_keyboard(
    results: list[tuple[Resource, int]],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    return _build_paginated_keyboard(
        items=results,
        page=page,
        total_pages=total_pages,
        get_text=lambda i, _: str((page - 1) * RESOURCES_PER_PAGE + i + 1),
        get_callback=lambda flag, val: (
            SearchCallback(action="page", page=val).pack()
            if flag == "nav"
            else SearchCallback(
                action="view",
                resource_id=val[0].id if isinstance(val, tuple) else None,
                page=page,
            ).pack()
        ),
    )


def create_settings_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Экспорт ссылок",
        callback_data=SettingsCallback(action="export_urls").pack(),
    )
    builder.button(
        text="Экспорт данных",
        callback_data=SettingsCallback(action="export_data").pack(),
    )
    builder.button(
        text="Импорт ссылок",
        callback_data=SettingsCallback(action="import_urls_menu").pack(),
    )
    builder.button(
        text="Импорт данных",
        callback_data=SettingsCallback(action="import_data_menu").pack(),
    )
    builder.button(
        text="Удаление",
        callback_data=SettingsCallback(action="delete").pack(),
    )
    builder.adjust(2)
    return builder.as_markup()


def create_import_urls_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Быстрый импорт",
        callback_data=SettingsCallback(action="import_urls_fast").pack(),
    )
    builder.button(
        text="Детальный импорт",
        callback_data=SettingsCallback(action="import_urls_detailed").pack(),
    )
    builder.button(
        text="Назад",
        callback_data=SettingsCallback(action="settings").pack(),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def create_import_data_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Быстрый импорт",
        callback_data=SettingsCallback(action="import_data_fast").pack(),
    )
    builder.button(
        text="Детальный импорт",
        callback_data=SettingsCallback(action="import_data_detailed").pack(),
    )
    builder.button(
        text="Назад",
        callback_data=SettingsCallback(action="settings").pack(),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def create_save_summary_keyboard() -> InlineKeyboardMarkup:
    return create_kb_tags(
        ["Сохранить", "Изменить", "Отмена"],
        pack_callback_data_list(["save", "edit", "cancel"]),
    )


def create_rating_keyboard(current: int | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for i in range(1, 6):
        text = f"★{i}" if current and i <= current else str(i)
        builder.button(
            text=text,
            callback_data=ResourceCallback(action=f"set_rating_{i}").pack(),
        )

    builder.button(
        text="Убрать оценку",
        callback_data=ResourceCallback(action="set_rating_0").pack(),
    )
    builder.button(
        text="Назад",
        callback_data=ResourceCallback(action="edit").pack(),
    )
    builder.adjust(5, 2)
    return builder.as_markup()


def create_view_resource_keyboard(resource_id: int, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Редактировать",
        callback_data=ResourceCallback(action="edit", resource_id=resource_id).pack(),
    )
    builder.button(
        text="Удалить",
        callback_data=ResourceCallback(
            action="confirm_delete", resource_id=resource_id, page=page
        ).pack(),
    )
    builder.button(
        text="К списку",
        callback_data=ResourceCallback(action="page", page=1).pack(),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def create_confirm_delete_keyboard(resource_id: int, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Да, удалить",
        callback_data=ResourceCallback(action="delete", resource_id=resource_id, page=page).pack(),
    )
    builder.button(
        text="Нет",
        callback_data=ResourceCallback(action="view", resource_id=resource_id, page=page).pack(),
    )
    builder.adjust(2)
    return builder.as_markup()


def create_view_res_search_keyboards(resource_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Редактировать",
        callback_data=SearchCallback(action="edit", resource_id=resource_id).pack(),
    )
    builder.button(
        text="Удалить",
        callback_data=SearchCallback(action="confirm_delete", resource_id=resource_id).pack(),
    )
    builder.button(
        text="К результатам",
        callback_data=SearchCallback(action="results", page=1).pack(),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def create_confirm_delete_res_keyboard(resource_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Да, удалить",
        callback_data=SearchCallback(action="delete", resource_id=resource_id).pack(),
    )
    builder.button(
        text="Нет",
        callback_data=SearchCallback(action="view", resource_id=resource_id).pack(),
    )
    builder.adjust(2)
    return builder.as_markup()


def create_del_import() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Удаление всех ресурсов",
        callback_data=SettingsCallback(action="del_all_resources").pack(),
    )
    builder.button(
        text="Удаление аккаунта",
        callback_data=SettingsCallback(action="del_account").pack(),
    )
    builder.button(
        text="Назад",
        callback_data=SettingsCallback(action="settings").pack(),
    )
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def _build_keyboard(
    items: list[tuple[str, str]],
    len_row: int = 2,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for text, callback_data in items:
        row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        if len(row) == len_row:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_paginated_keyboard[T](
    items: list[T],
    page: int,
    total_pages: int,
    get_text: Callable[[int, T], str],
    get_callback: Callable[[int | str, Any], str],
    compact_threshold: int = 3,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    compact = len(items) <= compact_threshold

    nav_buttons: list[InlineKeyboardButton] = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀ Назад",
                callback_data=get_callback("nav", page - 1),
            )
        )

    item_buttons: list[InlineKeyboardButton] = []
    for i, item in enumerate(items):
        item_buttons.append(
            InlineKeyboardButton(
                text=get_text(i, item),
                callback_data=get_callback(i, item),
            )
        )

    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперёд ▶",
                callback_data=get_callback("nav", page + 1),
            )
        )

    if compact:
        all_buttons: list[InlineKeyboardButton] = []
        if page > 1:
            all_buttons.extend(nav_buttons[:1])
        all_buttons.extend(item_buttons)
        if page < total_pages:
            all_buttons.extend(nav_buttons[-1:])

        for btn in all_buttons:
            builder.button(text=btn.text, callback_data=btn.callback_data)
        builder.adjust(len(all_buttons))
    else:
        for btn in item_buttons:
            builder.button(text=btn.text, callback_data=btn.callback_data)
        builder.adjust(3)

        if nav_buttons:
            builder.row(*nav_buttons)

    return builder.as_markup()
