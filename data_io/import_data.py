import json

from pydantic import TypeAdapter, ValidationError

from core.models.resource import Resource


def parse_data(filepath: str) -> list[Resource]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    adapter = TypeAdapter(list[Resource])

    try:
        return adapter.validate_python(data)
    except ValidationError as e:
        raise ValueError(f"Ошибка в JSON: {e}") from e
