import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import TypeVar

from config import YOUTUBE_API_KEY
from core.enum import BaseEnum
from core.exceptions import (
    APIResponseError,
    InvalidParamError,
    InvalidRatingError,
    InvalidUrlParamError,
    NetworkError,
    ProxyRequestError,
    ResourceNotFoundError,
)
from core.models.resource import Resource, ResourceKind, ResourceStatus, ResourceType
from core.service import ResourceService
from data.db.resources import ResourceDB
from data.exceptions import DuplicateResourceError, EmptyDatabaseError
from data.filter import InvalidFilterError, ResourceFilter

T = TypeVar("T", bound=BaseEnum)


def clean_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []

    for tag in tags:
        clean_tag = re.sub(r"[^\w\s\-]", "", tag).strip()
        if clean_tag:
            cleaned.append(clean_tag)

    return cleaned


def _choose_enum[T: BaseEnum](
    clear: Callable[[], None],
    pause: Callable[[], None],
    title: str,
    enum_cls: type[T],
    default: T | None = None,
) -> T | None:
    while True:
        clear()
        print(f"=== {title} ===\n")
        items = list(enum_cls)

        for i, item in enumerate(items, 1):
            print(f"  {i}. {item.label}")

        prompt = f"Номер (Enter={default.label}): " if default else "Номер: "
        choice = input(prompt).strip()

        if not choice:
            return default

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(items):
                return items[idx - 1]

        print(f"ERROR: Введите число от 1 до {len(items)}", flush=True)
        pause()


def _choose_tags(
    clear: Callable[[], None],
    title: str,
    existing_tags: list[str] | None,
) -> list[str]:
    clear()
    print("=== Тэги ===\n")
    print(f"Title: {title}\n")

    if existing_tags:
        print(f"Текущие: {', '.join(existing_tags)}")
        print("\n[y] оставить  [n] новые  [Enter] дополнить")
        choice = input(": ").strip().lower()

        if choice == "n":
            tags_input = input("Новые тэги: ").strip()
            return [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []

        if choice == "":
            tags_input = input("Дополнить: ").strip()
            extra = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
            return existing_tags + extra

        return existing_tags

    tags_input = input("Тэги через запятую: ").strip()
    return [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []


def add_video_cli(
    db: ResourceDB,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    clear()
    print("=== Добавление ресурса ===\n")

    url = input("URL: ").strip()
    if not url:
        print("ERROR: URL обязателен", flush=True)
        pause()
        return

    resource_type = _choose_enum(clear, pause, "Тип ресурса", ResourceType, ResourceType.OTHER)
    kind = _choose_enum(clear, pause, "Формат ресурса", ResourceKind)

    clear()
    print("=== Добавление ресурса ===\n")
    proxy_input = input("Прокси host:port (Enter=без прокси, d=127.0.0.1:10809): ").strip()
    proxy = "127.0.0.1:10809" if proxy_input.lower() == "d" else (proxy_input or None)

    try:
        resource = ResourceService.create_resource(
            tg_id=1,
            url=url,
            resource_type=resource_type or ResourceType.OTHER,
            kind=kind,
            proxy=proxy,
            youtube_api_key=YOUTUBE_API_KEY,
        )
    except (
        InvalidUrlParamError,
        InvalidParamError,
        InvalidRatingError,
        ResourceNotFoundError,
        ProxyRequestError,
        APIResponseError,
        NetworkError,
    ) as e:
        clear()
        print(f"ERROR: {e}")
        pause()
        return

    tags = _choose_tags(clear, resource.title, resource.tags)
    resource.tags = clean_tags(tags)

    try:
        resource_id = db.insert(resource)
    except DuplicateResourceError as e:
        clear()
        print(f"ERROR: {e}")
        pause()
        return

    clear()
    print("=== Добавлен ресурс ===\n")
    print(f"  {resource.title}")
    print(f"   Тип: {resource.resource_type.label}")
    print(f"   Формат: {resource.kind.label}")
    print(f"   Платформа: {resource.platform.label}")
    print(f"   Тэги: {', '.join(resource.tags)}")
    print(f"   Длительность: {resource.duration_display}")
    print(f"   Рейтинг: {resource.score:.1f}")
    print(f"   ID: {resource_id}")

    pause()


def search_cli(
    db: ResourceDB,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    f = _collect_search_filter(clear, pause)
    if f is None:
        return

    results = _run_search(db, f, clear, pause)
    if results is None:
        return

    _show_search_results(results, clear)


def _collect_search_filter(
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> ResourceFilter | None:
    resource_type = _pick_enum(clear, pause, "Тип ресурса", ResourceType)
    status = _pick_enum(clear, pause, "Статус", ResourceStatus)

    clear()
    print("=== Поиск ===\n")
    keywords = input("Ключевые слова (Enter — пропустить): ").strip() or None

    clear()
    print("=== Поиск ===\n")
    tags_input = input("Тэги через запятую (Enter — пропустить): ").strip()
    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else None

    view_status = _ask_view_status(clear, pause)
    uncompleted_only = view_status.get("uncompleted_only", True)
    recently_completed = view_status.get("recently_completed", False)
    long_ago_completed = view_status.get("long_ago_completed", False)

    clear()
    print("=== Поиск ===\n")
    max_dur = input("Макс. длительность в минутах (Enter — любая): ").strip()
    max_duration = int(max_dur) if max_dur.isdigit() else None

    clear()
    print("=== Поиск ===\n")
    limit_input = input("Сколько показать (Enter=10): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else 10

    try:
        return ResourceFilter(
            tg_id=1,
            resource_type=resource_type,
            status=status,
            tags=tags,
            keywords=keywords,
            uncompleted_only=uncompleted_only,
            recently_completed=recently_completed,
            long_ago_completed=long_ago_completed,
            max_duration=max_duration,
            limit=limit,
        )
    except InvalidFilterError as e:
        clear()
        print(f"ERROR: {e}")
        pause()
        return None


def _ask_view_status(
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> dict[str, bool]:
    while True:
        clear()
        print("=== Поиск ===\n")
        print("Статус просмотра:")
        print("  0. Любые")
        print("  1. Непросмотренные")
        print("  2. Недавно просмотренные")
        print("  3. Давно просмотренные")
        choice = input("Выбор (Enter=1): ").strip()

        if not choice or choice == "1":
            return {"uncompleted_only": True}
        if choice == "0":
            return {"uncompleted_only": False}
        if choice == "2":
            return {"uncompleted_only": False, "recently_completed": True}
        if choice == "3":
            return {"uncompleted_only": False, "long_ago_completed": True}

        print("ERROR: Введите 0-3", flush=True)
        pause()


def _run_search(
    db: ResourceDB,
    f: ResourceFilter,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> Sequence[tuple[Resource, int]] | None:
    try:
        results = db.search(0, f)
    except EmptyDatabaseError:
        clear()
        print("База пуста")
        pause()
        return None

    clear()
    if not results:
        print("Ничего не найдено")
        pause()
        return None

    return results


def _show_search_results(
    results: Sequence[tuple[Resource, int]],
    clear: Callable[[], None],
) -> None:
    page = 0
    total_pages = len(results)

    while True:
        clear()
        _print_result_page(results, page, total_pages)
        cmd = input(": ").strip().lower()

        if cmd == "n" and page < total_pages - 1:
            page += 1
        elif cmd == "p" and page > 0:
            page -= 1
        elif cmd == "q":
            break


def _print_result_page(
    results: Sequence[tuple[Resource, int]],
    page: int,
    total_pages: int,
) -> None:
    resource, _score = results[page]

    print(f"=== Результаты ({len(results)}) стр. {page + 1}/{total_pages} ===\n")
    print(f"{page + 1:2d}. {resource.title}")
    print(f"    url: {resource.url}")
    print(f"    id: {resource.id}")
    print(
        f"    {resource.resource_type.label} | {resource.duration_display} | "
        f"Рейтинг: {resource.score:.1f}"
    )
    if resource.tags:
        print(f"    Тэги: {', '.join(resource.tags)}")
    print()

    nav = []
    if page > 0:
        nav.append("p — назад")
    if page < total_pages - 1:
        nav.append("n — вперёд")
    nav.append("q — выход")
    print(" | ".join(nav))


def _pick_enum[T: BaseEnum](
    clear: Callable[[], None],
    pause: Callable[[], None],
    title: str,
    enum_cls: type[T],
) -> T | None:
    while True:
        clear()
        print(f"=== {title} ===\n")
        items = list(enum_cls)
        print("  0. Любой")

        for i, item in enumerate(items, 1):
            print(f"  {i}. {item.label}")

        choice = input("Номер (Enter=0): ").strip()

        if not choice or choice == "0":
            return None

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(items):
                return items[idx - 1]

        print(f"ERROR: Введите число от 0 до {len(items)}", flush=True)
        pause()


def show_all_videos(
    db: ResourceDB,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    clear()

    f = ResourceFilter(
        tg_id=1,
        resource_type=None,
        status=None,
        tags=None,
        sort_by_my_rating=False,
        sort_by_rating=False,
        newest_published=False,
        oldest_published=False,
        uncompleted_only=False,
        recently_completed=False,
        long_ago_completed=False,
        keywords=None,
        max_duration=None,
        limit=1000,
    )

    try:
        results = db.search(0, f)
    except EmptyDatabaseError:
        clear()
        print("=== Все ресурсы ===\n")
        print("База пуста")
        pause()
        return

    if not results:
        print("=== Все ресурсы ===\n")
        print("База пуста")
        pause()
        return

    idx = 0
    total = len(results)

    while True:
        clear()
        resource, _ = results[idx]

        print(f"{'─' * 50}")
        print(f"#{idx + 1} из {total} (ID: {resource.id})")
        print(f"Название: {resource.title}")
        desc = resource.description or ""
        print(f"Описание: {desc[:200]}{'...' if len(desc) > 200 else ''}")
        print(f"Тип: {resource.resource_type.label}")
        print(f"Формат: {resource.kind.label}")
        print(f"Статус: {resource.status.label}")
        print(f"Платформа: {resource.platform.label}")
        print(f"URL: {resource.url}")
        print(f"External ID: {resource.external_id}")
        print(f"Тэги: {', '.join(resource.tags) if resource.tags else 'нет'}")
        print(f"Заметки: {resource.my_notes or 'нет'}")
        print(f"Мой рейтинг: {resource.my_rating or '—'}/5")
        print(f"Вовлеченность: {resource.engagement}, Просмотров: {resource.views}")
        print(f"Рейтинг: {resource.score:.1f}")
        print(f"Длительность: {resource.duration_display}")
        print(f"Опубликовано: {resource.published_at or 'неизвестно'}")
        print(f"Завершено: {resource.completed_at or 'нет'}")
        print(f"Добавлено: {resource.created_at}")

        print(f"\n{'─' * 50}")

        nav_parts = []
        if idx > 0:
            nav_parts.append("p — назад")
        if idx < total - 1:
            nav_parts.append("n — вперёд")
        nav_parts.append("q — выход")
        print(" | ".join(nav_parts))

        cmd = input(": ").strip().lower()

        if cmd == "n" and idx < total - 1:
            idx += 1
        elif cmd == "p" and idx > 0:
            idx -= 1
        elif cmd == "q":
            break

    clear()


def edit_video_cli(
    db: ResourceDB,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    clear()
    print("=== Редактирование ===\n")

    resource = _find_resource_for_edit(db, clear, pause)
    if resource is None:
        return

    _edit_resource_menu(db, resource, clear, pause)


def _find_resource_for_edit(
    db: ResourceDB,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> Resource | None:
    id_input = input("ID ресурса (Enter — найти поиском): ").strip()

    if id_input.isdigit():
        resource = db.get_resource(int(id_input), 1)
        if resource is None:
            clear()
            print("ERROR: Ресурс не найден")
            pause()
            return None
        return resource

    return _find_resource_by_search(db, clear, pause)


def _find_resource_by_search(
    db: ResourceDB,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> Resource | None:
    clear()
    print("=== Редактирование ===\n")
    keywords = input("Ключевые слова для поиска: ").strip()

    if not keywords:
        clear()
        print("=== Редактирование ===\n")
        print("ERROR: Нужен ID или ключевые слова", flush=True)
        pause()
        return None

    f = ResourceFilter(tg_id=1, keywords=keywords, limit=10)

    try:
        results = db.search(0, f)
    except EmptyDatabaseError:
        clear()
        print("База пуста")
        pause()
        return None

    if not results:
        clear()
        print("=== Редактирование ===\n")
        print("ERROR: Ничего не найдено", flush=True)
        pause()
        return None

    return _select_resource_from_list(results, clear, pause)


def _select_resource_from_list(
    results: Sequence[tuple[Resource, int]],
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> Resource | None:
    while True:
        clear()
        print(f"=== Найдено ({len(results)}) ===\n")

        for i, (r, _) in enumerate(results, 1):
            print(f"{i}. {r.title}")

        choice = input("\nНомер: ").strip()

        if choice.isdigit() and 1 <= int(choice) <= len(results):
            return results[int(choice) - 1][0]

        print(f"ERROR: Введите число от 1 до {len(results)}", flush=True)
        pause()


def _edit_resource_menu(
    db: ResourceDB,
    resource: Resource,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    while True:
        clear()
        _print_edit_menu(resource)
        choice = input("\nЧто меняем: ").strip()

        if choice == "0":
            db.update(resource)
            clear()
            print(f"=== {resource.title} ===\n")
            print("Сохранено!", flush=True)
            pause()
            return

        if not _apply_edit_choice(resource, choice, clear, pause):
            print("ERROR: Неверный выбор")
            pause()


def _print_edit_menu(resource: Resource) -> None:
    print(f"=== Редактирование: {resource.title} ===\n")
    print(f"1. Тип: {resource.resource_type.label}")
    print(f"2. Формат: {resource.kind.label}")
    print(f"3. Статус: {resource.status.label}")
    print(f"4. Тэги: {', '.join(resource.tags) if resource.tags else 'нет'}")
    print(f"5. Заметки: {resource.my_notes or 'нет'}")
    print(f"6. Мой рейтинг: {resource.my_rating or '—'}/5")
    print(f"7. Дата завершения: {resource.completed_at or 'нет'}")
    print("0. Сохранить и выйти")


def _apply_edit_choice(
    resource: Resource,
    choice: str,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> bool:
    match choice:
        case "1":
            _assign_enum(resource, "resource_type", ResourceType, clear, pause)
        case "2":
            _assign_enum(resource, "kind", ResourceKind, clear, pause)
        case "3":
            _assign_enum(resource, "status", ResourceStatus, clear, pause, via_update_status=True)
        case "4":
            resource.tags = clean_tags(_choose_tags(clear, resource.title, resource.tags))
        case "5":
            _edit_notes(resource, clear, pause)
        case "6":
            _edit_rating(resource, clear, pause)
        case "7":
            _edit_date(resource, clear, pause)
        case _:
            return False
    return True


def _assign_enum(
    resource: Resource,
    attr: str,
    enum_cls: type,
    clear: Callable[[], None],
    pause: Callable[[], None],
    *,
    via_update_status: bool = False,
) -> None:
    new_value = _choose_enum(clear, pause, attr, enum_cls)
    if new_value is None:
        return
    if via_update_status:
        resource.update_status(new_value)
    else:
        setattr(resource, attr, new_value)


def _edit_notes(
    resource: Resource,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    clear()
    print("=== Заметка ===\n")

    if resource.my_notes:
        print(f"Текущая:\n{resource.my_notes}\n")
        print("1. Исправить")
        print("2. Новая")
        print("3. Удалить")
        print("0. Оставить")
        action = input("\n: ").strip()

        if action == "1":
            clear()
            print("=== Заметка ===\n")
            print(f"Текущая:\n{resource.my_notes}\n")
            new_notes = input("Исправленная: ").strip()
            if new_notes:
                resource.my_notes = new_notes
        elif action == "2":
            clear()
            resource.my_notes = input("Новая заметка: ").strip()
        elif action == "3":
            resource.my_notes = None
    else:
        resource.my_notes = input("Новая заметка: ").strip()

    pause()


def _edit_rating(
    resource: Resource,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    while True:
        clear()
        print("=== Мой рейтинг ===\n")
        r = input("Рейтинг (1-5): ").strip()

        if r.isdigit() and 1 <= int(r) <= 5:
            try:
                resource.update_my_rating(int(r))
                break
            except InvalidRatingError as e:
                print(f"ERROR: {e}")
                pause()
                continue

        print("ERROR: Введите 1-5")
        pause()


def _edit_date(
    resource: Resource,
    clear: Callable[[], None],
    pause: Callable[[], None],
) -> None:
    clear()
    print("=== Дата завершения ===\n")

    d = input("Дата (YYYY-MM-DD HH:MM, Enter — сейчас): ").strip()

    if d:
        try:
            resource.completed_at = datetime.fromisoformat(d)
        except ValueError:
            print("ERROR: Неверный формат", flush=True)
            pause()
    else:
        resource.completed_at = datetime.now(UTC)
