"""
Консольное меню v2: иерархическая настройка active runtime без ручного
редактирования settings.json.
"""
import builtins
import os

from utils import api_client
from utils.console_control import disable_quick_edit_mode
from utils.paths import DATA_DIR


SITES = ["aistudio"]
MODES_BY_SITE = {"aistudio": ["standard", "multiformat", "multiformat_with_refs"]}


def _save(settings: dict) -> None:
    from utils import settings_store

    settings_store.save_settings(settings)


def _read_choice(prompt: str = "Выбор: ") -> str:
    return builtins.input(prompt).strip()


def _show_section_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _show_bool(value: bool) -> str:
    return "включено" if value else "выключено"


def _prompt_int(current: int, label: str, minimum: int | None = None) -> int | None:
    raw = _read_choice(f"{label} [{current}]: ")
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        print("Ошибка: введите целое число.")
        return None
    if minimum is not None and value < minimum:
        print(f"Ошибка: значение должно быть >= {minimum}.")
        return None
    return value


def _prompt_float(
    current: float,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    raw = _read_choice(f"{label} [{current}]: ")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        print("Ошибка: введите число.")
        return None
    if minimum is not None and value < minimum:
        print(f"Ошибка: значение должно быть >= {minimum}.")
        return None
    if maximum is not None and value > maximum:
        print(f"Ошибка: значение должно быть <= {maximum}.")
        return None
    return value


def _validate_aspect_ratio(value: str) -> bool:
    parts = value.split(":")
    if len(parts) != 2:
        return False
    try:
        left = float(parts[0])
        right = float(parts[1])
        return left > 0 and right > 0
    except ValueError:
        return False


def _select_from_list(title: str, options: list[str], current: str) -> str | None:
    _show_section_header(title)
    for index, option in enumerate(options, start=1):
        mark = " (текущее)" if option == current else ""
        print(f"{index}. {option}{mark}")
    print("0. Назад")
    choice = _read_choice("Номер: ")
    if not choice or choice == "0":
        return None
    try:
        index = int(choice)
    except ValueError:
        print("Ошибка: введите номер.")
        return None
    if 1 <= index <= len(options):
        return options[index - 1]
    print("Ошибка: неверный номер.")
    return None


def show_current_config(settings: dict) -> None:
    print("Текущая конфигурация:")
    print(f"  Сайт: {settings.get('CURRENT_SITE')}")
    print(f"  Режим: {settings.get('CURRENT_MODE')}")
    print(f"  Файл промптов: {settings.get('PROMPTS_FILE') or 'не выбран'}")
    print(
        f"  Диапазон карточек: {settings.get('START_FROM_CARD')}–{settings.get('END_CARD')}"
    )
    print(f"  Метод генерации: {settings.get('GENERATION_METHOD', 'browser')}")

    if settings.get("GENERATION_METHOD") == "api":
        provider = api_client.get_api_provider(settings, with_reference=False)
        provider_with_refs = api_client.get_api_provider(settings, with_reference=True)
        print(f"  API provider: {api_client.get_provider_display_name(provider)}")
        print(
            "  API provider с refs: "
            f"{api_client.get_provider_display_name(provider_with_refs)}"
        )


def select_site(settings: dict) -> None:
    selected = _select_from_list(
        "Выбор сайта",
        SITES,
        settings.get("CURRENT_SITE", "aistudio"),
    )
    if selected is None:
        return
    settings["CURRENT_SITE"] = selected
    _save(settings)
    print(f"Сайт сохранён: {selected}")


def select_mode_for_site(settings: dict) -> None:
    site = settings.get("CURRENT_SITE", "aistudio")
    modes = MODES_BY_SITE.get(site, [])
    if not modes:
        print("Нет режимов для выбранного сайта.")
        return
    selected = _select_from_list(
        f"Выбор режима для {site}",
        modes,
        settings.get("CURRENT_MODE", "standard"),
    )
    if selected is None:
        return
    settings["CURRENT_MODE"] = selected
    _save(settings)
    print(f"Режим сохранён: {selected}")


def select_prompts_file(settings: dict) -> None:
    data_dir = str(DATA_DIR)
    if not os.path.isdir(data_dir):
        print("Папка data/ не найдена.")
        return

    names = []
    for name in os.listdir(data_dir):
        path = os.path.join(data_dir, name)
        if not name.lower().endswith(".txt"):
            continue
        if not os.path.isfile(path):
            continue
        names.append(name)

    names.sort(
        key=lambda name: os.path.getctime(os.path.join(data_dir, name)),
        reverse=True,
    )
    if not names:
        print("В папке data/ нет файлов.")
        return

    _show_section_header("Выбор файла промптов")
    current = settings.get("PROMPTS_FILE", "")
    for index, name in enumerate(names, start=1):
        path = os.path.join(data_dir, name)
        mark = " (текущий)" if path == current else ""
        print(f"{index}. {name}{mark}")
    print("0. Назад")

    choice = _read_choice("Номер файла: ")
    if not choice or choice == "0":
        return
    try:
        index = int(choice)
    except ValueError:
        print("Ошибка: введите номер.")
        return
    if not (1 <= index <= len(names)):
        print("Ошибка: неверный номер.")
        return

    settings["PROMPTS_FILE"] = os.path.join(data_dir, names[index - 1])
    _save(settings)
    print(f"Файл промптов сохранён: {settings['PROMPTS_FILE']}")


def configure_start_card(settings: dict) -> None:
    value = _prompt_int(
        int(settings.get("START_FROM_CARD", 1)),
        "Стартовая карточка",
        minimum=1,
    )
    if value is None:
        return

    end_card = int(settings.get("END_CARD", value))
    if value > end_card:
        settings["END_CARD"] = value
    settings["START_FROM_CARD"] = value
    _save(settings)
    print(f"START_FROM_CARD сохранён: {value}")


def configure_end_card(settings: dict) -> None:
    start_card = int(settings.get("START_FROM_CARD", 1))
    value = _prompt_int(
        int(settings.get("END_CARD", start_card)),
        "Конечная карточка",
        minimum=start_card,
    )
    if value is None:
        return

    settings["END_CARD"] = value
    _save(settings)
    print(f"END_CARD сохранён: {value}")


def select_generation_method(settings: dict) -> None:
    selected = _select_from_list(
        "Выбор метода генерации",
        ["browser", "api"],
        settings.get("GENERATION_METHOD", "browser"),
    )
    if selected is None:
        return
    settings["GENERATION_METHOD"] = selected
    _save(settings)
    print(f"Метод генерации сохранён: {selected}")


def configure_api_provider(settings: dict, with_refs: bool = False) -> None:
    title = "API provider с референсами" if with_refs else "API provider без референсов"
    key = "API_PROVIDER_WITH_REFS" if with_refs else "API_PROVIDER"
    current = settings.get(key, api_client.PROVIDER_NANOBANANA)
    selected = _select_from_list(
        title,
        [api_client.PROVIDER_NANOBANANA, api_client.PROVIDER_CHATGPT],
        current,
    )
    if selected is None:
        return
    settings[key] = selected
    _save(settings)
    print(f"{key} сохранён: {selected}")


def configure_api_key(settings: dict, provider: str) -> None:
    field_name = api_client.get_api_key_field(provider)
    current = settings.get(field_name, "").strip()
    provider_name = api_client.get_provider_display_name(provider)

    _show_section_header(f"Настройка API ключа: {provider_name}")
    if current:
        print(f"Текущий ключ: {current[:10]}...")
    else:
        print("Ключ не задан.")
    if provider == api_client.PROVIDER_NANOBANANA:
        print("Получить ключ: https://aistudio.google.com/apikey")
    new_key = _read_choice("Новый ключ (Enter — отмена): ")
    if not new_key:
        return

    key_valid, key_error = api_client.check_api_key_format(new_key, provider=provider)
    if not key_valid:
        print(f"Ошибка: {key_error}")
        return

    from utils import settings_store

    settings_store.save_secret(provider, new_key)
    refreshed = settings_store.load_settings()
    settings[field_name] = refreshed.get(field_name, "")
    if provider == api_client.PROVIDER_NANOBANANA:
        settings["API_KEY"] = refreshed.get("API_KEY", "")
    print(f"Ключ {provider_name} сохранён в локальный .env.")


def configure_api_models(settings: dict) -> None:
    while True:
        _show_section_header("Настройка API моделей")
        print(f"1. Модель nanobanana без refs: {settings.get('API_MODEL')}")
        print(f"2. Модель nanobanana с refs: {settings.get('API_MODEL_WITH_REFS')}")
        print(f"3. Модель chatgpt: {settings.get('API_MODEL_CHATGPT')}")
        print(f"4. Качество chatgpt: {settings.get('API_CHATGPT_QUALITY')}")
        print(f"5. Размер изображения nanobanana: {settings.get('API_IMAGE_SIZE')}")
        print(f"6. API timeout: {settings.get('API_TIMEOUT')}")
        print("0. Назад")
        choice = _read_choice()

        if choice == "0":
            return
        if choice == "1":
            selected = _select_from_list(
                "Модель nanobanana без refs",
                [
                    "imagen-4.0-fast-generate-001",
                    "imagen-4.0-generate-001",
                    "imagen-4.0-ultra-generate-001",
                    "gemini-2.5-flash-image",
                ],
                settings.get("API_MODEL", "imagen-4.0-generate-001"),
            )
            if selected:
                settings["API_MODEL"] = selected
                _save(settings)
        elif choice == "2":
            selected = _select_from_list(
                "Модель nanobanana с refs",
                ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
                settings.get("API_MODEL_WITH_REFS", "gemini-2.5-flash-image"),
            )
            if selected:
                settings["API_MODEL_WITH_REFS"] = selected
                _save(settings)
        elif choice == "3":
            selected = _select_from_list(
                "Модель chatgpt",
                ["gpt-image-2"],
                settings.get("API_MODEL_CHATGPT", "gpt-image-2"),
            )
            if selected:
                settings["API_MODEL_CHATGPT"] = selected
                _save(settings)
        elif choice == "4":
            selected = _select_from_list(
                "Качество chatgpt",
                ["low", "medium", "high"],
                settings.get("API_CHATGPT_QUALITY", "low"),
            )
            if selected:
                settings["API_CHATGPT_QUALITY"] = selected
                _save(settings)
        elif choice == "5":
            selected = _select_from_list(
                "Размер изображения nanobanana",
                ["1K", "2K"],
                settings.get("API_IMAGE_SIZE", "2K"),
            )
            if selected:
                settings["API_IMAGE_SIZE"] = selected
                _save(settings)
        elif choice == "6":
            value = _prompt_float(
                float(settings.get("API_TIMEOUT", 60.0)),
                "API timeout",
                minimum=1.0,
                maximum=600.0,
            )
            if value is not None:
                settings["API_TIMEOUT"] = value
                _save(settings)
        else:
            print("Ошибка: неверный номер.")


def configure_chatgpt_parallel(settings: dict) -> None:
    while True:
        _show_section_header("Параллельный ChatGPT API")
        print(f"Profile: {settings.get('API_CHATGPT_RATE_LIMIT_PROFILE', 'custom')}")
        print(
            "1. Параллельный режим: "
            f"{_show_bool(bool(settings.get('API_CHATGPT_PARALLEL_ENABLED', True)))}"
        )
        print(f"2. Количество воркеров: {settings.get('API_CHATGPT_MAX_WORKERS', 2)}")
        print(f"3. Лимит запусков в минуту: {settings.get('API_CHATGPT_RATE_LIMIT_IPM', 5)}")
        print(
            "4. Окно лимитера (сек): "
            f"{settings.get('API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS', 60)}"
        )
        print("5. Apply OpenAI Tier 3 preset (50 IPM / 800k TPM)")
        print("0. Назад")
        choice = _read_choice()

        if choice == "0":
            return
        if choice == "1":
            current = bool(settings.get("API_CHATGPT_PARALLEL_ENABLED", True))
            settings["API_CHATGPT_PARALLEL_ENABLED"] = not current
            _save(settings)
        elif choice == "2":
            value = _prompt_int(
                int(settings.get("API_CHATGPT_MAX_WORKERS", 2)),
                "Количество воркеров",
                minimum=1,
            )
            if value is not None:
                settings["API_CHATGPT_RATE_LIMIT_PROFILE"] = "custom"
                settings["API_CHATGPT_MAX_WORKERS"] = value
                _save(settings)
        elif choice == "3":
            value = _prompt_int(
                int(settings.get("API_CHATGPT_RATE_LIMIT_IPM", 5)),
                "Лимит запусков в минуту",
                minimum=1,
            )
            if value is not None:
                settings["API_CHATGPT_RATE_LIMIT_PROFILE"] = "custom"
                settings["API_CHATGPT_RATE_LIMIT_IPM"] = value
                _save(settings)
        elif choice == "4":
            value = _prompt_int(
                int(settings.get("API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS", 60)),
                "Окно лимитера (сек)",
                minimum=1,
            )
            if value is not None:
                settings["API_CHATGPT_RATE_LIMIT_PROFILE"] = "custom"
                settings["API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS"] = value
                _save(settings)
        elif choice == "5":
            settings["API_CHATGPT_PARALLEL_ENABLED"] = True
            settings["API_CHATGPT_RATE_LIMIT_PROFILE"] = "tier3"
            settings["API_CHATGPT_MAX_WORKERS"] = 50
            settings["API_CHATGPT_RATE_LIMIT_IPM"] = 50
            settings["API_CHATGPT_RATE_LIMIT_WINDOW_SECONDS"] = 60
            settings["API_CHATGPT_RATE_LIMIT_TPM"] = 800000
            settings["API_CHATGPT_MONTHLY_USAGE_LIMIT_USD"] = 1000
            _save(settings)
            print("OpenAI Tier 3 preset saved.")
        else:
            print("Ошибка: неверный номер.")


def configure_generation_wait(settings: dict) -> None:
    value = _prompt_float(
        float(settings.get("GENERATION_WAIT", 20.0)),
        "GENERATION_WAIT",
        minimum=10.0,
        maximum=120.0,
    )
    if value is None:
        return
    settings["GENERATION_WAIT"] = value
    _save(settings)
    print(f"GENERATION_WAIT сохранён: {value}")


def configure_image_wait_interval(settings: dict) -> None:
    value = _prompt_float(
        float(settings.get("IMAGE_WAIT_INTERVAL", 2.0)),
        "IMAGE_WAIT_INTERVAL",
        minimum=1.0,
        maximum=60.0,
    )
    if value is None:
        return
    settings["IMAGE_WAIT_INTERVAL"] = value
    _save(settings)
    print(f"IMAGE_WAIT_INTERVAL сохранён: {value}")


def configure_check_image_generated(settings: dict) -> None:
    current = bool(settings.get("CHECK_IMAGE_GENERATED", True))
    _show_section_header("CHECK_IMAGE_GENERATED")
    print(f"Текущее значение: {_show_bool(current)}")
    print("1. Включить")
    print("2. Выключить")
    print("0. Назад")
    choice = _read_choice()
    if choice == "1":
        settings["CHECK_IMAGE_GENERATED"] = True
    elif choice == "2":
        settings["CHECK_IMAGE_GENERATED"] = False
    else:
        return
    _save(settings)
    print(
        "CHECK_IMAGE_GENERATED сохранён: "
        f"{_show_bool(bool(settings['CHECK_IMAGE_GENERATED']))}"
    )


def configure_aspect_ratio(settings: dict, key: str, label: str) -> None:
    current = str(settings.get(key, ""))
    raw = _read_choice(f"{label} [{current}]: ")
    if not raw:
        return
    if not _validate_aspect_ratio(raw):
        print("Ошибка: используйте формат X:Y, например 4:3.")
        return
    settings[key] = raw
    _save(settings)
    print(f"{key} сохранён: {raw}")


def show_generation_plan(settings: dict) -> None:
    site = settings.get("CURRENT_SITE")
    mode = settings.get("CURRENT_MODE")
    path = settings.get("PROMPTS_FILE")
    if not site or not mode:
        print("Выберите сайт и режим.")
        return
    if not path or not path.strip():
        print("Выберите файл промптов.")
        return
    if mode not in ("standard", "multiformat", "multiformat_with_refs"):
        print("Неизвестный режим.")
        return

    if mode == "multiformat":
        from sites.aistudio import mode_multiformat as mode_module

        tasks = mode_module.load_tasks_from_file(path)
        if not tasks:
            print("Файл пустой или не содержит валидных строк.")
            return
        info = mode_module.get_plan_info(tasks)
        print("--- План генерации (multiformat) ---")
        print(f"Карточек: {info['cards_count']}")
        print(f"Пар: {info['pairs_count']}")
        print(f"Будет сгенерировано изображений: {info['images_planned']}")
        print("-----------------------------------")
        return

    if mode == "multiformat_with_refs":
        from sites.aistudio import mode_multiformat_with_refs as mode_module

        tasks = mode_module.load_tasks_from_file(path)
        if not tasks:
            print("Файл пустой или не содержит валидных строк.")
            return
        info = mode_module.get_plan_info(tasks)
        print("--- План генерации (multiformat_with_refs) ---")
        print(f"Карточек: {info['cards_count']}")
        print(f"Пар: {info['pairs_count']}")
        print(f"Будет сгенерировано изображений: {info['images_planned']}")
        print("---------------------------------------------")
        return

    from sites.aistudio import mode_standard as mode_module

    tasks = mode_module.load_tasks_from_file(path)
    if not tasks:
        print("Файл пустой или не содержит валидных строк.")
        return
    info = mode_module.get_plan_info(tasks)
    print("--- План генерации ---")
    print(f"Карточек: {info['cards_count']}")
    print(f"Генераций (промптов): {info['generations_count']}")
    print(f"Будет сгенерировано изображений: {info['images_planned']}")
    print("----------------------")


def start_generation_with_process(
    settings: dict,
    coordinates: dict,
    relative_movements: dict,
) -> None:
    if settings.get("CURRENT_SITE") != "aistudio":
        print("Запуск генерации поддерживается только для сайта aistudio.")
        return

    mode = settings.get("CURRENT_MODE")
    if mode not in ("standard", "multiformat", "multiformat_with_refs"):
        print(
            "Запуск генерации поддерживается только для режимов "
            "standard, multiformat и multiformat_with_refs."
        )
        return

    from utils import process_control

    generation_method = settings.get("GENERATION_METHOD", "browser")
    if generation_method == "api":
        from utils.generation_runner import (
            can_start_generation_api,
            run_multiformat_with_refs_worker_api,
            run_multiformat_worker_api,
            run_standard_worker_api,
        )

        ok, err = can_start_generation_api(settings)
    else:
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
        from sites.aistudio import mode_standard as mode_module

        tasks = mode_module.load_tasks_from_file(path)
        if end_card is None and tasks:
            end_card = max(task["card_number"] for task in tasks)
        filtered = [task for task in tasks if start_card <= task["card_number"] <= end_card]
        info = mode_module.get_plan_info(filtered)
        print(
            f"Сводка: карточек: {info['cards_count']}, "
            f"промптов: {info['generations_count']}, "
            f"изображений: {info['images_planned']}"
        )
        worker = run_standard_worker_api if generation_method == "api" else run_standard_worker
    elif mode == "multiformat":
        from sites.aistudio import mode_multiformat as mode_module

        tasks = mode_module.load_tasks_from_file(path)
        if end_card is None and tasks:
            end_card = max(task["card_number"] for task in tasks)
        filtered = [task for task in tasks if start_card <= task["card_number"] <= end_card]
        info = mode_module.get_plan_info(filtered)
        print(
            f"Сводка: карточек: {info['cards_count']}, "
            f"пар: {info['pairs_count']}, "
            f"изображений: {info['images_planned']}"
        )
        worker = run_multiformat_worker_api if generation_method == "api" else run_multiformat_worker
    else:
        from sites.aistudio import mode_multiformat_with_refs as mode_module

        tasks = mode_module.load_tasks_from_file(path)
        if end_card is None and tasks:
            end_card = max(task["card_number"] for task in tasks)
        filtered = [task for task in tasks if start_card <= task["card_number"] <= end_card]
        info = mode_module.get_plan_info(filtered)
        print(
            f"Сводка: карточек: {info['cards_count']}, "
            f"пар: {info['pairs_count']}, "
            f"изображений: {info['images_planned']}"
        )
        worker = run_multiformat_with_refs_worker_api if generation_method == "api" else run_multiformat_with_refs_worker

    if generation_method == "api":
        worker_args = (settings,)
        worker_type = "api"
    else:
        worker_args = (settings, coordinates, relative_movements)
        worker_type = "browser"

    process = process_control.start_worker(worker, worker_args, worker_type=worker_type)
    if process is None:
        return

    print("Генерация запущена. Меню продолжит работу после завершения воркера.")
    print("Для остановки по Esc запускайте программу без --menu.")
    process_control.wait_worker(process)
    print("Воркер завершён.")


def show_generation_menu(settings: dict, coordinates: dict, relative_movements: dict) -> None:
    while True:
        _show_section_header("Раздел: Генерация")
        print(f"1. Сайт: {settings.get('CURRENT_SITE')}")
        print(f"2. Режим: {settings.get('CURRENT_MODE')}")
        print(f"3. Метод генерации: {settings.get('GENERATION_METHOD')}")
        print("4. Показать план генерации")
        print("5. Запустить генерацию")
        print("0. Назад")
        choice = _read_choice()

        if choice == "0":
            return
        if choice == "1":
            select_site(settings)
        elif choice == "2":
            select_mode_for_site(settings)
        elif choice == "3":
            select_generation_method(settings)
        elif choice == "4":
            show_generation_plan(settings)
        elif choice == "5":
            start_generation_with_process(settings, coordinates, relative_movements)
        else:
            print("Ошибка: неверный номер.")


def show_files_menu(settings: dict) -> None:
    while True:
        _show_section_header("Раздел: Файлы и диапазон")
        print(f"1. Файл промптов: {settings.get('PROMPTS_FILE') or 'не выбран'}")
        print(f"2. START_FROM_CARD: {settings.get('START_FROM_CARD')}")
        print(f"3. END_CARD: {settings.get('END_CARD')}")
        print("0. Назад")
        choice = _read_choice()

        if choice == "0":
            return
        if choice == "1":
            select_prompts_file(settings)
        elif choice == "2":
            configure_start_card(settings)
        elif choice == "3":
            configure_end_card(settings)
        else:
            print("Ошибка: неверный номер.")


def show_api_menu(settings: dict) -> None:
    while True:
        _show_section_header("Раздел: API")
        print(
            "1. Provider без refs: "
            f"{settings.get('API_PROVIDER', api_client.PROVIDER_NANOBANANA)}"
        )
        print(
            "2. Provider с refs: "
            f"{settings.get('API_PROVIDER_WITH_REFS', api_client.PROVIDER_NANOBANANA)}"
        )
        print(
            "3. Ключ nanobanana: "
            f"{'задан' if settings.get('API_KEY_NANOBANANA') or settings.get('API_KEY') else 'не задан'}"
        )
        print(
            "4. Ключ chatgpt: "
            f"{'задан' if settings.get('API_KEY_CHATGPT') else 'не задан'}"
        )
        print("5. Модели, качество и timeout")
        print("6. Параллельный ChatGPT API")
        print("0. Назад")
        choice = _read_choice()

        if choice == "0":
            return
        if choice == "1":
            configure_api_provider(settings, with_refs=False)
        elif choice == "2":
            configure_api_provider(settings, with_refs=True)
        elif choice == "3":
            configure_api_key(settings, api_client.PROVIDER_NANOBANANA)
        elif choice == "4":
            configure_api_key(settings, api_client.PROVIDER_CHATGPT)
        elif choice == "5":
            configure_api_models(settings)
        elif choice == "6":
            configure_chatgpt_parallel(settings)
        else:
            print("Ошибка: неверный номер.")


def show_browser_menu(settings: dict) -> None:
    while True:
        _show_section_header("Раздел: Browser")
        print(f"1. GENERATION_WAIT: {settings.get('GENERATION_WAIT')}")
        print(f"2. IMAGE_WAIT_INTERVAL: {settings.get('IMAGE_WAIT_INTERVAL')}")
        print(
            "3. CHECK_IMAGE_GENERATED: "
            f"{_show_bool(bool(settings.get('CHECK_IMAGE_GENERATED', True)))}"
        )
        print(f"4. FACE_ASPECT_RATIO: {settings.get('FACE_ASPECT_RATIO')}")
        print(f"5. BACK_ASPECT_RATIO: {settings.get('BACK_ASPECT_RATIO')}")
        print("0. Назад")
        choice = _read_choice()

        if choice == "0":
            return
        if choice == "1":
            configure_generation_wait(settings)
        elif choice == "2":
            configure_image_wait_interval(settings)
        elif choice == "3":
            configure_check_image_generated(settings)
        elif choice == "4":
            configure_aspect_ratio(settings, "FACE_ASPECT_RATIO", "FACE_ASPECT_RATIO")
        elif choice == "5":
            configure_aspect_ratio(settings, "BACK_ASPECT_RATIO", "BACK_ASPECT_RATIO")
        else:
            print("Ошибка: неверный номер.")


def show_coordinates_menu_hint() -> None:
    from utils.coordinates_store import load_coordinates

    coordinates, relative_movements = load_coordinates()
    configured_absolute = sum(1 for value in coordinates.values() if value != (0, 0))
    configured_relative = sum(1 for value in relative_movements.values() if value != (0, 0))

    _show_section_header("Раздел: Координаты")
    print("Координаты пока настраиваются отдельно от CLI-меню.")
    print("Используйте runtime-режим программы:")
    print("  1. Ctrl+0 — выбрать координату")
    print("  2. Ctrl+Shift+P — захватить позицию курсора")
    print()
    print(
        "Сейчас настроено: "
        f"{configured_absolute}/{len(coordinates)} абсолютных, "
        f"{configured_relative}/{len(relative_movements)} относительных."
    )
    _read_choice("Enter — назад: ")


def show_main_menu(
    settings: dict,
    coordinates: dict,
    relative_movements: dict,
) -> None:
    from utils import process_control
    from utils import settings_store

    disable_quick_edit_mode()

    while True:
        _show_section_header("CLI-меню настроек v2")
        show_current_config(settings)
        print()
        print("1. Генерация")
        print("2. Файлы и диапазон")
        print("3. API")
        print("4. Browser")
        print("5. Координаты")
        print("0. Выход")
        choice = _read_choice()

        if choice == "0":
            current_worker = process_control.get_current_worker()
            if current_worker is not None and current_worker.is_alive():
                print("Перед выходом останавливаем активный воркер.")
                process_control.stop_worker(current_worker)
            settings_store.save_settings(settings)
            print("Выход.")
            break
        if choice == "1":
            show_generation_menu(settings, coordinates, relative_movements)
        elif choice == "2":
            show_files_menu(settings)
        elif choice == "3":
            show_api_menu(settings)
        elif choice == "4":
            show_browser_menu(settings)
        elif choice == "5":
            show_coordinates_menu_hint()
        else:
            print("Ошибка: неверный номер.")


if __name__ == "__main__":
    from utils.coordinates_store import load_coordinates
    from utils.settings_store import load_settings

    loaded_settings = load_settings()
    loaded_coordinates, loaded_relative_movements = load_coordinates()
    show_main_menu(loaded_settings, loaded_coordinates, loaded_relative_movements)
