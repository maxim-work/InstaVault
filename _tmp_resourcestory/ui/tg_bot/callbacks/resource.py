from aiogram.filters.callback_data import CallbackData


class ResourceCallback(CallbackData, prefix="res"):
    action: str
    resource_id: int | None = None
    page: int | None = None


class SearchCallback(CallbackData, prefix="search"):
    action: str
    resource_id: int | None = None
    page: int | None = None


class SettingsCallback(CallbackData, prefix="settings"):
    action: str


def get_callback_data(option: str) -> str:
    return ResourceCallback(action=option).pack()


def pack_callback_data_list(options: list[str]) -> list[str]:
    return [ResourceCallback(action=opt).pack() for opt in options]
