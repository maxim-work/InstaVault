class DataError(Exception):
    pass


class DuplicateResourceError(DataError):
    url: str

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Ресурс с таким url({url}) уже существует!")


class DuplicateUserError(DataError):
    tg_id: int

    def __init__(self, tg_id: int) -> None:
        self.tg_id = tg_id
        super().__init__(f"Пользователь с таким tg_id({tg_id}) уже существует!")


class EmptyDatabaseError(DataError):
    def __init__(self):
        super().__init__("База данных пуста")


class InvalidFilterError(Exception):
    pass
