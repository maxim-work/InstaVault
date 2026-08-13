from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def create_user_start_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="Добавить ресурс")
    builder.button(text="Поиск")
    builder.button(text="Мои ресурсы")
    builder.button(text="Помощь")
    builder.button(text="Ещё")
    builder.adjust(2, 2, 1)
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def create_admin_start_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="Добавить ресурс")
    builder.button(text="Поиск")
    builder.button(text="Мои ресурсы")
    builder.button(text="Помощь")
    builder.button(text="Ещё")
    builder.button(text="Админ-панель")
    builder.adjust(2, 2, 2)
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
