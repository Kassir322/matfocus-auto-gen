"""
Консольное меню v2: выбор сайта/режима/файла, показ плана генерации, запуск генерации (пункт 5).
"""
import os

# Директория с файлами промптов (сканируем только файлы)
DATA_DIR = "data"

# Доступные сайты и режимы по сайту (по INTERFACE_console_menu, SETTINGS_V2)
SITES = ["aistudio"]
MODES_BY_SITE = {"aistudio": ["standard", "multiformat", "multiformat_with_refs"]}


def show_current_config(settings: dict) -> None:
    """Выводит текущие значения: сайт, режим, файл промптов."""
    site = settings.get("CURRENT_SITE") or "не выбрано"
    mode = settings.get("CURRENT_MODE") or "не выбрано"
    prompts_file = settings.get("PROMPTS_FILE") or "не выбрано"
    print(f"Текущий сайт: {site}")
    print(f"Текущий режим: {mode}")
    print(f"Файл промптов: {prompts_file}")


def select_site(settings: dict) -> None:
    """Предлагает выбрать сайт из списка, записывает в settings['CURRENT_SITE']."""
    print("Выберите сайт:")
    for i, site_id in enumerate(SITES, start=1):
        print(f"  {i}. {site_id}")
    try:
        raw = input("Номер: ").strip()
        idx = int(raw)
        if 1 <= idx <= len(SITES):
            settings["CURRENT_SITE"] = SITES[idx - 1]
            print(f"Выбран сайт: {settings['CURRENT_SITE']}")
        else:
            print("Неверный номер.")
    except ValueError:
        print("Введите число.")


def select_mode_for_site(settings: dict) -> None:
    """Предлагает выбрать режим для текущего сайта, записывает в settings['CURRENT_MODE']."""
    site = settings.get("CURRENT_SITE")
    if not site:
        print("Сначала выберите сайт (пункт 1).")
        return
    modes = MODES_BY_SITE.get(site, [])
    if not modes:
        print("Нет режимов для этого сайта.")
        return
    print("Выберите режим:")
    for i, mode_id in enumerate(modes, start=1):
        print(f"  {i}. {mode_id}")
    try:
        raw = input("Номер: ").strip()
        idx = int(raw)
        if 1 <= idx <= len(modes):
            settings["CURRENT_MODE"] = modes[idx - 1]
            print(f"Выбран режим: {settings['CURRENT_MODE']}")
        else:
            print("Неверный номер.")
    except ValueError:
        print("Введите число.")


def select_prompts_file(settings: dict) -> None:
    """Сканирует data/, показывает только файлы нумерованным списком, записывает путь в settings['PROMPTS_FILE']."""
    if not os.path.isdir(DATA_DIR):
        print("Папка data/ не найдена.")
        return
    names = [n for n in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, n))]
    if not names:
        print("В папке data/ нет файлов.")
        return
    names.sort()
    print("Файлы в data/:")
    for i, name in enumerate(names, start=1):
        print(f"  {i}. {name}")
    try:
        raw = input("Номер файла: ").strip()
        idx = int(raw)
        if 1 <= idx <= len(names):
            path = os.path.join(DATA_DIR, names[idx - 1])
            settings["PROMPTS_FILE"] = path
            print(f"Выбран файл: {path}")
        else:
            print("Неверный номер.")
    except ValueError:
        print("Введите число.")


def show_generation_plan(settings: dict) -> None:
    """Разбирает файл выбранным режимом и выводит сводку (карточки, генерации/пары, изображения)."""
    site = settings.get("CURRENT_SITE")
    mode = settings.get("CURRENT_MODE")
    path = settings.get("PROMPTS_FILE")
    if not site or not mode:
        print("Выберите сайт и режим (пункты 1 и 2).")
        return
    if not path or not path.strip():
        print("Выберите файл промптов (пункт 3).")
        return
    if mode not in ("standard", "multiformat", "multiformat_with_refs"):
        print("Неизвестный режим. План доступен для standard, multiformat и multiformat_with_refs.")
        return
    try:
        if mode == "multiformat":
            from sites.aistudio import mode_multiformat
            tasks = mode_multiformat.load_tasks_from_file(path)
            if not tasks:
                print("Файл пустой или не содержит валидных строк.")
                return
            info = mode_multiformat.get_plan_info(tasks)
            print("--- План генерации (multiformat) ---")
            print(f"Карточек: {info['cards_count']}")
            print(f"Пар: {info['pairs_count']}")
            print(f"Будет сгенерировано изображений: {info['images_planned']}")
            print("-----------------------------------")
        elif mode == "multiformat_with_refs":
            from sites.aistudio import mode_multiformat_with_refs
            tasks = mode_multiformat_with_refs.load_tasks_from_file(path)
            if not tasks:
                print("Файл пустой или не содержит валидных строк.")
                return
            info = mode_multiformat_with_refs.get_plan_info(tasks)
            print("--- План генерации (multiformat_with_refs) ---")
            print(f"Карточек: {info['cards_count']}")
            print(f"Пар: {info['pairs_count']}")
            print(f"Будет сгенерировано изображений: {info['images_planned']}")
            print("---------------------------------------------")
        else:
            from sites.aistudio import mode_standard
            tasks = mode_standard.load_tasks_from_file(path)
            if not tasks:
                print("Файл пустой или не содержит валидных строк.")
                return
            info = mode_standard.get_plan_info(tasks)
            print("--- План генерации ---")
            print(f"Карточек: {info['cards_count']}")
            print(f"Генераций (промптов): {info['generations_count']}")
            print(f"Будет сгенерировано изображений: {info['images_planned']}")
            print("----------------------")
    except Exception:
        print("Ошибка при чтении файла или файл не найден.")
        return


def start_generation_with_process(
    settings: dict,
    coordinates: dict,
    relative_movements: dict,
) -> None:
    """Запуск генерации в подпроцессе (standard, multiformat или multiformat_with_refs). Проверки перед стартом, затем process_control.start_worker."""
    if settings.get("CURRENT_SITE") != "aistudio":
        print("Запуск генерации поддерживается только для сайта aistudio.")
        return
    mode = settings.get("CURRENT_MODE")
    if mode not in ("standard", "multiformat", "multiformat_with_refs"):
        print("Запуск генерации поддерживается только для режимов standard, multiformat и multiformat_with_refs.")
        return
    from utils import process_control
    from utils.generation_runner import (
        can_start_generation,
        run_standard_worker,
        run_multiformat_worker,
        run_multiformat_with_refs_worker,
    )

    ok, err = can_start_generation(settings)
    if not ok:
        print(err)
        return

    # Сводка перед стартом: карточек, промптов/пар, изображений (ROADMAP этап 10)
    path = settings.get("PROMPTS_FILE") or ""
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)

    if mode == "standard":
        from sites.aistudio import mode_standard
        tasks = mode_standard.load_tasks_from_file(path)
        if end_card is None and tasks:
            end_card = max(t["card_number"] for t in tasks)
        filtered = [t for t in tasks if start_card <= t["card_number"] <= end_card] if tasks else []
        info = mode_standard.get_plan_info(filtered)
        print(f"Сводка: карточек: {info['cards_count']}, промптов: {info['generations_count']}, изображений: {info['images_planned']}")
        worker = run_standard_worker
    elif mode == "multiformat":
        from sites.aistudio import mode_multiformat
        tasks = mode_multiformat.load_tasks_from_file(path)
        if end_card is None and tasks:
            end_card = max(t["card_number"] for t in tasks)
        filtered = [t for t in tasks if start_card <= t["card_number"] <= end_card] if tasks else []
        info = mode_multiformat.get_plan_info(filtered)
        print(f"Сводка: карточек: {info['cards_count']}, пар: {info['pairs_count']}, изображений: {info['images_planned']}")
        worker = run_multiformat_worker
    else:
        from sites.aistudio import mode_multiformat_with_refs
        tasks = mode_multiformat_with_refs.load_tasks_from_file(path)
        if end_card is None and tasks:
            end_card = max(t["card_number"] for t in tasks)
        filtered = [t for t in tasks if start_card <= t["card_number"] <= end_card] if tasks else []
        info = mode_multiformat_with_refs.get_plan_info(filtered)
        print(f"Сводка: карточек: {info['cards_count']}, пар: {info['pairs_count']}, изображений: {info['images_planned']}")
        worker = run_multiformat_with_refs_worker

    process_control.start_worker(worker, (settings, coordinates, relative_movements))
    print("Генерация запущена в подпроцессе. Для остановки по Esc запускайте программу без --menu (режим с хоткеями).")


def show_main_menu(
    settings: dict,
    coordinates: dict,
    relative_movements: dict,
) -> None:
    """Главный цикл меню: конфигурация, пункты 1–5 и 0 (выход). При выходе сохраняем настройки."""
    from utils import settings_store
    while True:
        print()
        show_current_config(settings)
        print()
        print("1 — Выбрать сайт")
        print("2 — Выбрать режим")
        print("3 — Выбрать файл промптов")
        print("4 — Показать план генерации")
        print("5 — Запустить генерацию")
        print("0 — Выход")
        choice = input("Выбор: ").strip()
        if choice == "0":
            settings_store.save_settings(settings)
            print("Выход.")
            break
        if choice == "1":
            select_site(settings)
        elif choice == "2":
            select_mode_for_site(settings)
        elif choice == "3":
            select_prompts_file(settings)
        elif choice == "4":
            show_generation_plan(settings)
        elif choice == "5":
            start_generation_with_process(settings, coordinates, relative_movements)
        else:
            print("Неверный ввод. Введите 0–5.")


if __name__ == "__main__":
    # Точка входа для проверки меню v2: python -m ui.console_menu
    from utils.settings_store import load_settings
    from utils.coordinates_store import load_coordinates

    settings = load_settings()
    coordinates, relative_movements = load_coordinates()
    show_main_menu(settings, coordinates, relative_movements)
