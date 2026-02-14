"""
Стандартный режим генерации (v2).
Парсинг файла промптов, план, run_mode с логированием по LOGGING.md.
"""
import os
import re
import time
from collections import defaultdict
from datetime import datetime

from sites.aistudio import helpers
from utils.log_writer import write_log_line

# Regex по PROMPTS_standard_format: Карточка N - Промпт M: текст
LINE_PATTERN = re.compile(r"^Карточка (\d+) - Промпт (\d+): (.+)$")

# Задержки по ALGO_standard раздел 10 (секунды)
BETWEEN_CLICKS = 0.5
AFTER_PASTE = 1.0
NEW_CHAT_WAIT = 2.0
CHAT_RENAME_WAIT = 1.0
BETWEEN_GENERATIONS = 1.0
BETWEEN_CARDS = 2.0

# Обязательные координаты для режима standard (COORDINATES_KEYS)
REQUIRED_COORDS = ["PROMPT_INPUT", "IMAGE_LOCATION", "NEW_CHAT_BUTTON", "CHAT_NAME_INPUT"]
REQUIRED_RELATIVE = ["TO_SAVE_OPTION"]


def _point(val):
    """Приведение значения координаты из JSON (list) или tuple к паре (x, y)."""
    if val is None:
        return (0, 0)
    return (int(val[0]), int(val[1]))


def _is_zero_point(val):
    """Проверка, что координата не задана (0, 0)."""
    x, y = _point(val)
    return x == 0 and y == 0


def load_tasks_from_file(path: str) -> list[dict]:
    """
    Разбирает файл промптов стандартного формата, возвращает список задач.
    Каждая задача: card_number, generation_number, prompt_text.
    Порядок: по карточкам, внутри карточки по номеру промпта.
    При отсутствии файла или ошибке чтения возвращает пустой список.
    """
    # Временное хранилище: card_num -> { prompt_num -> prompt_text } (дубликаты перезаписываются)
    temp_data = defaultdict(dict)

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                match = LINE_PATTERN.match(line)
                if match:
                    card_num = int(match.group(1))
                    prompt_num = int(match.group(2))
                    prompt_text = match.group(3).strip()
                    temp_data[card_num][prompt_num] = prompt_text
                # невалидные строки пропускаем (логирование по LOGGING.md позже)
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return []

    # Разворачиваем в плоский список Task в нужном порядке
    tasks = []
    for card_num in sorted(temp_data.keys()):
        prompts_dict = temp_data[card_num]
        for gen_num in sorted(prompts_dict.keys()):
            tasks.append({
                "card_number": card_num,
                "generation_number": gen_num,
                "prompt_text": prompts_dict[gen_num],
            })
    return tasks


def get_plan_info(tasks: list[dict]) -> dict:
    """
    Подсчёт сводки по списку задач для вывода плана.
    Возвращает: cards_count, generations_count, images_planned.
    """
    if not tasks:
        return {"cards_count": 0, "generations_count": 0, "images_planned": 0}
    cards_count = len(set(t["card_number"] for t in tasks))
    n = len(tasks)
    return {
        "cards_count": cards_count,
        "generations_count": n,
        "images_planned": n,
    }


def _filter_tasks_by_range(tasks: list[dict], start_card: int, end_card: int | None) -> list[dict]:
    """Оставить только задачи с start_card <= card_number <= end_card. Если end_card None — макс. номер из tasks."""
    if not tasks:
        return []
    if end_card is None:
        end_card = max(t["card_number"] for t in tasks)
    return [t for t in tasks if start_card <= t["card_number"] <= end_card]


def _check_required_coordinates(coordinates: dict, relative_movements: dict) -> list[str]:
    """Проверка обязательных координат. Возвращает список отсутствующих (пустой = всё ОК)."""
    missing = []
    for key in REQUIRED_COORDS:
        if _is_zero_point(coordinates.get(key)):
            missing.append(key)
    for key in REQUIRED_RELATIVE:
        if _is_zero_point(relative_movements.get(key)):
            missing.append(key)
    return missing


def _get_log_filepath() -> str:
    """Путь к файлу лога: logs/auto-gen_YYYY-MM-DD_HH-MM-SS.log (LOGGING.md)."""
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join("logs", f"auto-gen_{timestamp}.log")


def _make_chat_name(card_number: int, gen_num: int) -> str:
    """Имя чата для standard: Карточка N - генерация G (NAMING_RULES)."""
    return f"Карточка {card_number} - генерация {gen_num}"


def _make_filename(card_number: int, gen_num: int) -> str:
    """Имя файла для standard: Карточка_N_лицевая_промпт_G.png (NAMING_RULES)."""
    return f"Карточка_{card_number}_лицевая_промпт_{gen_num}.png"


def _generate_single_image(
    task: dict,
    coordinates: dict,
    relative_movements: dict,
    settings: dict,
    log_file,
) -> bool:
    """
    Генерация одного изображения по задаче (ALGO_standard п.5).
    Возвращает True при успешном сохранении, False при ошибке или пропуске.
    """
    card_number = task["card_number"]
    gen_num = task["generation_number"]
    prompt_text = task.get("prompt_text", "").strip()

    if not prompt_text:
        write_log_line(log_file, f"[WARN] Пропуск: пустой промпт карточка {card_number} генерация {gen_num}")
        return False

    chat_name = _make_chat_name(card_number, gen_num)
    file_name = _make_filename(card_number, gen_num)

    write_log_line(log_file, f"[GEN] Генерация: {chat_name}")

    try:
        # 1. Новый чат
        helpers.click_new_chat(coordinates)
        time.sleep(NEW_CHAT_WAIT)

        # 2. Ввод промпта
        helpers.click_prompt_input(coordinates)
        time.sleep(BETWEEN_CLICKS)
        helpers.paste_prompt_text(prompt_text, delay=AFTER_PASTE)

        # 3. Переименование чата
        helpers.rename_chat(coordinates, chat_name)
        time.sleep(CHAT_RENAME_WAIT)

        # 4. Вернуться к полю промпта и запустить генерацию
        helpers.click_prompt_input(coordinates)
        time.sleep(BETWEEN_CLICKS)
        helpers.start_generation()
        time.sleep(BETWEEN_CLICKS)

        # 5. Ожидание генерации
        generation_wait = float(settings.get("GENERATION_WAIT", 20.0))
        if settings.get("CHECK_IMAGE_GENERATED", True):
            check_interval = float(settings.get("IMAGE_WAIT_INTERVAL", 2.0))
            box_size = settings.get("IMAGE_CHECK_BOX_SIZE", (100, 100))
            if isinstance(box_size, (list, tuple)) and len(box_size) >= 2:
                box_size = (int(box_size[0]), int(box_size[1]))
            else:
                box_size = (100, 100)
            diff_threshold = float(settings.get("IMAGE_CHECK_THRESHOLD", 0.1))
            helpers.wait_until_image_ready(
                coordinates,
                timeout_seconds=generation_wait,
                check_interval=check_interval,
                box_size=box_size,
                diff_threshold=diff_threshold,
            )
        else:
            time.sleep(generation_wait)

        # 6. Сохранение изображения
        helpers.save_image(coordinates, relative_movements, file_name)
        time.sleep(2.0)  # AFTER_SAVE

        write_log_line(log_file, f"[OK] Файл сохранён: {file_name}")
        return True

    except Exception as e:
        write_log_line(log_file, f"[ERROR] Ошибка при генерации/сохранении {file_name}: {e}")
        return False


def run_mode(
    tasks: list[dict],
    settings: dict,
    coordinates: dict,
    relative_movements: dict,
) -> None:
    """
    Выполнение генерации для стандартного режима.
    Координаты передаются двумя словарями (не объединять).
    Логи в файл с тегами [PLAN], [CARD], [GEN], [OK], [ERROR], [SUMMARY]; консоль — только основные шаги.
    """
    # Фильтрация по диапазону карточек
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    tasks = _filter_tasks_by_range(tasks, start_card, end_card)

    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return

    # Проверка обязательных координат
    missing = _check_required_coordinates(coordinates, relative_movements)
    if missing:
        print("Отсутствуют обязательные координаты:", ", ".join(missing))
        return

    # Лог-файл на сессию генерации (LOGGING.md)
    log_path = _get_log_filepath()
    log_file = open(log_path, "w", encoding="utf-8")

    try:
        info = get_plan_info(tasks)
        plan_msg = (
            f"[PLAN] Режим: standard. Карточек: {info['cards_count']}, "
            f"генераций: {info['generations_count']}"
        )
        write_log_line(log_file, plan_msg)

        prompts_file = settings.get("PROMPTS_FILE", "")
        if prompts_file:
            write_log_line(log_file, f"[PLAN] Файл промптов: {prompts_file}")

        print("Генерация запущена. Esc — остановка.")
        total_generations = len(tasks)
        done_generations = 0
        cards_seen = set()
        last_card = None

        for idx, task in enumerate(tasks):
            card_number = task["card_number"]
            if card_number != last_card:
                if last_card is not None:
                    time.sleep(BETWEEN_CARDS)
                write_log_line(log_file, f"[CARD] Карточка {card_number}")
                cards_seen.add(card_number)
                last_card = card_number
            else:
                time.sleep(BETWEEN_GENERATIONS)

            ok = _generate_single_image(task, coordinates, relative_movements, settings, log_file)
            if ok:
                done_generations += 1
            # Прогресс в консоль (только основные шаги)
            print(f"Генерация {done_generations} из {total_generations}")
            
            # Проверка: последний ли это промпт для текущей карточки
            is_last_prompt_for_card = (idx == len(tasks) - 1) or (tasks[idx + 1]["card_number"] != card_number)
            if is_last_prompt_for_card:
                # Сохранить следующий номер карточки в настройках для продолжения при следующем запуске
                from utils.settings_store import update_start_card
                update_start_card(card_number + 1)

        summary_msg = f"[SUMMARY] Карточек: {len(cards_seen)}, генераций: {done_generations}/{total_generations}"
        write_log_line(log_file, summary_msg)
        print(f"Готово. Обработано карточек: {len(cards_seen)}, генераций: {done_generations}/{total_generations}")

    finally:
        log_file.close()
