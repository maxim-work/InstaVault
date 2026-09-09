import json
from pathlib import Path

from core.models.resource import Resource
from pydantic import TypeAdapter, ValidationError


def parse_data(filepath: str) -> list[Resource]:
    try:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
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
