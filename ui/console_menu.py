"""
Консольное меню v2: выбор сайта/режима/файла, показ плана, запуск генерации.
"""
import builtins
import os


DATA_DIR = "data"
SITES = ["aistudio"]
MODES_BY_SITE = {"aistudio": ["standard", "multiformat", "multiformat_with_refs"]}


def show_current_config(settings: dict) -> None:
    from utils import api_client

    site = settings.get("CURRENT_SITE") or "не выбрано"
    mode = settings.get("CURRENT_MODE") or "не выбрано"
    prompts_file = settings.get("PROMPTS_FILE") or "не выбрано"
    generation_method = settings.get("GENERATION_METHOD", "browser")

    print(f"Текущий сайт: {site}")
    print(f"Текущий режим: {mode}")
    print(f"Файл промптов: {prompts_file}")
    print(f"Метод генерации: {generation_method}")
    if generation_method == "api":
        provider = api_client.get_api_provider(settings, with_reference=False)
        provider_with_refs = api_client.get_api_provider(settings, with_reference=True)
        print(f"API provider: {api_client.get_provider_display_name(provider)}")
        print(f"API provider c refs: {api_client.get_provider_display_name(provider_with_refs)}")
        print(
            f"Ключ nanobanana: {'задан' if api_client.get_api_key(settings, api_client.PROVIDER_NANOBANANA) else 'не задан'}"
        )
        print(
            f"Ключ chatgpt: {'задан' if api_client.get_api_key(settings, api_client.PROVIDER_CHATGPT) else 'не задан'}"
        )


def select_site(settings: dict) -> None:
    print("Выберите сайт:")
    for i, site_id in enumerate(SITES, start=1):
        print(f"  {i}. {site_id}")
    try:
        idx = int(input("Номер: ").strip())
        if 1 <= idx <= len(SITES):
            settings["CURRENT_SITE"] = SITES[idx - 1]
            print(f"Выбран сайт: {settings['CURRENT_SITE']}")
        else:
            print("Неверный номер.")
    except ValueError:
        print("Введите число.")


def select_mode_for_site(settings: dict) -> None:
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
        idx = int(input("Номер: ").strip())
        if 1 <= idx <= len(modes):
            settings["CURRENT_MODE"] = modes[idx - 1]
            print(f"Выбран режим: {settings['CURRENT_MODE']}")
        else:
            print("Неверный номер.")
    except ValueError:
        print("Введите число.")


def select_prompts_file(settings: dict) -> None:
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
        idx = int(input("Номер файла: ").strip())
        if 1 <= idx <= len(names):
            path = os.path.join(DATA_DIR, names[idx - 1])
            settings["PROMPTS_FILE"] = path
            print(f"Выбран файл: {path}")
        else:
            print("Неверный номер.")
    except ValueError:
        print("Введите число.")


def select_generation_method(settings: dict) -> None:
    from utils import api_client

    current = settings.get("GENERATION_METHOD", "browser")
    print(f"Текущий метод: {current}")
    print("Выберите метод генерации:")
    print("  1. browser")
    print("  2. api")
    raw = input("Номер: ").strip()
    if raw == "1":
        settings["GENERATION_METHOD"] = "browser"
        print("Метод генерации: browser")
        return
    if raw != "2":
        print("Неверный номер.")
        return

    settings["GENERATION_METHOD"] = "api"
    print("Провайдер для промптов без референсов:")
    print("  1. nanobanana")
    print("  2. chatgpt")
    provider_choice = input("Номер: ").strip()
    settings["API_PROVIDER"] = (
        api_client.PROVIDER_CHATGPT if provider_choice == "2" else api_client.PROVIDER_NANOBANANA
    )
    settings["API_PROVIDER_WITH_REFS"] = api_client.PROVIDER_NANOBANANA
    print("Метод генерации: api")
    print("Не забудьте настроить API ключи (пункт 7).")


def configure_api_key(settings: dict) -> None:
    from utils import api_client

    print("Какой ключ настроить?")
    print("  1. nanobanana")
    print("  2. chatgpt")
    provider_choice = input("Номер: ").strip()
    provider = api_client.PROVIDER_CHATGPT if provider_choice == "2" else api_client.PROVIDER_NANOBANANA
    field_name = api_client.get_api_key_field(provider)
    current = settings.get(field_name, "")

    if current:
        print(f"Текущий ключ {api_client.get_provider_display_name(provider)}: {current[:10]}...")
    else:
        print(f"Ключ {api_client.get_provider_display_name(provider)} не задан.")

    if provider == api_client.PROVIDER_NANOBANANA:
        print("Получить ключ: https://aistudio.google.com/apikey")
    else:
        print("Введите ключ OpenAI API.")

    new_key = input("API ключ: ").strip()
    if not new_key:
        print("Отмена.")
        return

    key_valid, key_error = api_client.check_api_key_format(new_key, provider=provider)
    if not key_valid:
        print(f"Ошибка: {key_error}")
        return

    settings[field_name] = new_key
    if provider == api_client.PROVIDER_NANOBANANA:
        settings["API_KEY"] = new_key
    print("API ключ сохранён.")


def show_generation_plan(settings: dict) -> None:
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
        print("Неизвестный режим.")
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
    except (OSError, ImportError, ValueError):
        print("Ошибка при чтении файла или файл не найден.")


def start_generation_with_process(settings: dict, coordinates: dict, relative_movements: dict) -> None:
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
        run_multiformat_with_refs_worker,
        run_multiformat_worker,
        run_standard_worker,
    )

    ok, err = can_start_generation(settings)
    if not ok:
        print(err)
        return

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

    process_control.start_worker(worker, (settings, coordinates, relative_movements), worker_type="browser")
    print("Генерация запущена в подпроцессе. Для остановки по Esc запускайте программу без --menu.")


def show_main_menu(settings: dict, coordinates: dict, relative_movements: dict) -> None:
    from utils import process_control
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
        print("6 — Выбрать метод генерации (browser/api)")
        print("7 — Настроить API ключ")
        print("0 — Выход")
        choice = builtins.input("Выбор: ").strip()

        if choice == "0":
            current_worker = process_control.get_current_worker()
            if current_worker is not None and current_worker.is_alive():
                print("Перед выходом останавливаем активный воркер.")
                process_control.stop_worker(current_worker)
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
        elif choice == "6":
            select_generation_method(settings)
        elif choice == "7":
            configure_api_key(settings)
        else:
            print("Неверный ввод. Введите 0–7.")


if __name__ == "__main__":
    from utils.coordinates_store import load_coordinates
    from utils.settings_store import load_settings

    settings = load_settings()
    coordinates, relative_movements = load_coordinates()
    show_main_menu(settings, coordinates, relative_movements)
