import json
from pydantic import TypeAdapter, ValidationError
from core.models.resource import Resource


def parse_data(filepath: str) -> list[Resource]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка в JSON: {e}") from e
    except FileNotFoundError:
        raise ValueError("Файл не найден") from None
    except Exception as e:
        raise ValueError(f"Ошибка чтения файла: {e}") from e

    adapter = TypeAdapter(list[Resource])

    try:
        return adapter.validate_python(data)
    except ValidationError as e:
        raise ValueError(f"Ошибка в JSON: {e}") from e
