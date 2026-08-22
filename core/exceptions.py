class ReprMixinError:
    def __repr__(self) -> str:
        fields = {k: v for k, v in self.__dict__.items() if k != "args"}
        parts = [f"{k}={v!r}" for k, v in fields.items()]
        return f"{self.__class__.__name__}({', '.join(parts)})"


class ResourceError(Exception):
    pass


class InvalidRatingError(ReprMixinError, ResourceError):
    rating: int
    max_rating: int

    def __init__(self, rating: int, max_rating: int = 5) -> None:
        self.rating = rating
        self.max_rating = max_rating
        super().__init__(f"Оценка должна быть от 1 до {max_rating}, получено: {rating}")


class InvalidParamError(ReprMixinError, ResourceError):
    param: str
    value: str

    def __init__(self, param: str, value: str, message: str | None = None) -> None:
        self.param = param
        self.value = value
        super().__init__(message or f"Некорректное значение параметра {param}: {value}")


class InvalidUrlParamError(ReprMixinError, ResourceError):
    param: str
    url: str

    def __init__(self, param: str, url: str, message: str | None = None) -> None:
        self.param = param
        self.url = url
        super().__init__(message or f"Некорректный параметр {param} для url: {url}")


class UnknownClassCodeError(ReprMixinError, ResourceError):
    code: str
    cls_name: str

    def __init__(self, cls_name: str, code: str) -> None:
        self.code = code
        self.cls_name = cls_name
        super().__init__(f"Неизвестный код {cls_name}: {code}")


class ParseError(Exception):
    pass


class APIResponseError(ReprMixinError, ParseError):
    code: int
    text: str

    def __init__(self, code: int, text: str) -> None:
        self.code = code
        self.text = text
        super().__init__(f"Ошибка API:{code} - {text}")


class ResourceNotFoundError(ReprMixinError, ParseError):
    resource_id: str
    source: str | None

    def __init__(self, resource_id: str, source: str | None = None) -> None:
        self.resource_id = resource_id
        self.source = source
        msg = f"Ресурс с ID {resource_id} не найдено"
        if source:
            msg += f" (источник: {source})"
        super().__init__(msg)


class NetworkError(Exception):
    pass


class ProxyRequestError(ReprMixinError, NetworkError):
    proxy: str | None
    original_error: Exception

    def __init__(self, original_error: Exception, proxy: str | None = None) -> None:
        self.proxy = proxy
        self.original_error = original_error
        super().__init__(
            f"Ошибка запроса через прокси {proxy}: {original_error}"
            if proxy
            else f"Ошибка запроса: {original_error}"
        )
