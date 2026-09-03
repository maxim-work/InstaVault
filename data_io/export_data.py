import json
from pathlib import Path

from config import EXPORT_DIR
from core.models.resource import Resource


def write_urls_file(urls: list[str], filename: str = "urls.txt") -> tuple[Path, int]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = EXPORT_DIR / filename

    Path(filepath).write_text(
        "\n".join(urls) + ("\n" if urls else ""),
        encoding="utf-8",
    )

    return filepath, len(urls)


def write_data_file(
    data: list[Resource], filename: str = "data.json"
) -> tuple[Path, int]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = EXPORT_DIR / filename

    serialized = [r.model_dump(mode="json") for r in data]

    Path(filepath).write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return filepath, len(data)
