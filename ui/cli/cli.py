import io
import sys
from pathlib import Path

from data.db.resources import ResourceDB
from data_io.export_data import write_data_file, write_urls_file
from data_io.import_data import parse_data
from ui.cli.handlers import add_video_cli, edit_video_cli, search_cli, show_all_videos


def setup_encoding() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)


def clear() -> None:
    print("\033[H\033[2J", end="", flush=True)


def pause() -> None:
    input("\nEnter — дальше")


def start_cli(db: ResourceDB) -> None:
    clear()

    while True:
        _print_main_menu()
        user_enter = input("\n: ").strip()

        if user_enter in ("0", "exit"):
            clear()
            return

        _handle_main_choice(db, user_enter)


def _print_main_menu() -> None:
    print("=== База знаний ===\n")
    print("1. Добавить")
    print("2. Поиск")
    print("3. Удалить по id")
    print("4. Удалить все")
    print("5. Показать все")
    print("6. Редактировать")
    print("7. Экспорт")
    print("8. Импорт")
    print("0. Выход")


def _handle_main_choice(db: ResourceDB, choice: str) -> None:
    match choice:
        case "1":
            add_video_cli(db, clear, pause)
        case "2":
            search_cli(db, clear, pause)
        case "3":
            _delete_by_id(db)
        case "4":
            _delete_all(db)
        case "5":
            show_all_videos(db, clear, pause)
        case "6":
            edit_video_cli(db, clear, pause)
        case "7":
            _handle_export(db)
        case "8":
            _handle_import(db)
        case _:
            clear()
            print("=== База знаний ===\n")
            print("Неверный ввод, попробуйте снова", flush=True)
            pause()
            return

    clear()


def _delete_by_id(db: ResourceDB) -> None:
    clear()
    print("=== Удаление по id ===\n")
    id_resource = input("Введите id: ").strip()
    if id_resource.isdigit():
        db.delete(int(id_resource), 0)
        print("Done!", flush=True)
        pause()


def _delete_all(db: ResourceDB) -> None:
    clear()
    print("=== Очистка всей базы ===\n")
    confirm = input("Точно удалить ВСЁ? (yes/no): ").strip()
    if confirm.lower() == "yes":
        db.delete_all(0)
        print("Done!", flush=True)
        pause()


def _handle_export(db: ResourceDB) -> None:
    clear()
    print("=== Экспорт ===\n")
    print("1. Экспорт ссылок")
    print("2. Экспорт всей базы")

    choice = input("\n: ").strip()

    if choice not in ("1", "2"):
        clear()
        print("=== Экспорт ===\n")
        print("Неверный выбор", flush=True)
        pause()
        return

    clear()
    print("=== Экспорт ===\n")
    fname = input("Имя файла (Enter — по умолчанию): ").strip()

    if choice == "1":
        urls = db.export_urls(0)
        path, count = write_urls_file(urls, fname or "urls.txt")
        message = f"{count} ссылок → {path}"
    else:
        data = db.export_data(0)
        path, count = write_data_file(data, fname or "data.json")
        message = f"{count} шт. → {path}"

    clear()
    print("=== Экспорт ===\n")
    print(message, flush=True)
    pause()


def _handle_import(db: ResourceDB) -> None:
    clear()
    print("=== Импорт ===\n")
    filepath = input("Путь к JSON файлу: ").strip()

    if not filepath:
        print("Путь не указан", flush=True)
        pause()
        return

    if not Path(filepath).exists():
        print(f"Файл не найден: {filepath}", flush=True)
        pause()
        return

    try:
        data = parse_data(filepath)
        added, total, _ = db.import_data(data, 0)
        clear()
        print("=== Импорт ===\n")
        print(
            f"Добавлено {added} из {total} (пропущено {total - added})",
            flush=True,
        )
    except Exception as e:  # noqa: BLE001
        clear()
        print("=== Импорт ===\n")
        print(f"Ошибка: {e}", flush=True)

    pause()
