"""
Мультиформатный режим (v2): лицо + оборот с разными aspect ratio.
Парсер файла промптов «лицо/оборот», план, run_mode по ALGO_multiformat.md.
"""
import os
import re
import time
from collections import defaultdict
from datetime import datetime

from sites.aistudio import helpers
from utils import generation_stats
from utils.log_writer import write_log_line

# Regex по PROMPTS_multiformat_format: Карточка N лицо|оборот название - Промпт M: текст (название может содержать дефисы, напр. Русско-японская война)
LINE_PATTERN = re.compile(r"^Карточка (\d+) (лицо|оборот) (.+?) - Промпт (\d+): (.+)$")

# Задержки как в mode_standard (ALGO_multiformat п.12)
BETWEEN_CLICKS = 0.5
AFTER_PASTE = 1.0
NEW_CHAT_WAIT = 2.0
CHAT_RENAME_WAIT = 1.0
BETWEEN_GENERATIONS = 1.0
BETWEEN_CARDS = 2.0

# Обязательные координаты: standard + ASPECT_RATIO_SELECTOR (COORDINATES_KEYS п.4.2)
REQUIRED_COORDS = [
    "PROMPT_INPUT",
    "IMAGE_LOCATION",
    "NEW_CHAT_BUTTON",
    "CHAT_NAME_INPUT",
    "ASPECT_RATIO_SELECTOR",
]
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


def _parse_file_to_cards(path: str) -> dict:
    """
    Парсит файл мультиформатного формата.
    Возвращает {card_number: {"name": str, "pairs": [{"лицо": str|None, "оборот": str|None}, ...]}}.
    """
    temp_data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                match = LINE_PATTERN.match(line)
                if match:
                    card_num = int(match.group(1))
                    side = match.group(2)
                    card_name = match.group(3).strip()
                    pair_num = int(match.group(4))
                    prompt_text = match.group(5).strip()
                    if card_num not in temp_data:
                        temp_data[card_num] = {
                            "name": card_name,
                            "pairs_dict": defaultdict(lambda: {"лицо": None, "оборот": None}),
                        }
                    if temp_data[card_num]["name"] != card_name:
                        print(
                            f"[WARN] Строка {line_num}: название '{card_name}' отличается "
                            f"от '{temp_data[card_num]['name']}'"
                        )
                    temp_data[card_num]["pairs_dict"][pair_num][side] = prompt_text
                else:
                    preview = line[:80]
                    print(f"[WARN] Строка {line_num} не распознана: {preview}")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return {}

    result = {}
    for card_num in sorted(temp_data.keys()):
        card_data = temp_data[card_num]
        pairs_dict = card_data["pairs_dict"]
        sorted_pairs = [pairs_dict[k] for k in sorted(pairs_dict.keys())]
        for pair_idx, pair in enumerate(sorted_pairs, start=1):
            if pair["лицо"] is None:
                print(f"[WARN] Карточка {card_num}, пара {pair_idx}: отсутствует лицевая сторона")
            if pair["оборот"] is None:
                print(f"[WARN] Карточка {card_num}, пара {pair_idx}: отсутствует оборотная сторона")
        result[card_num] = {"name": card_data["name"], "pairs": sorted_pairs}
    return result


def load_tasks_from_file(path: str) -> list[dict]:
    """
    Разбирает файл промптов мультиформатного формата, возвращает плоский список задач.
    Каждая задача: card_number, card_name, pair_number, side ("лицо"|"оборот"), prompt_text.
    Порядок: по карточкам, по парам, внутри пары сначала лицо, потом оборот.
    Неполные пары включаются (одна запись на сторону с промптом; сторона без промпта — задача с prompt_text=None не добавляется, только сторона с текстом).
    """
    cards = _parse_file_to_cards(path)
    if not cards:
        return []

    tasks = []
    for card_num in sorted(cards.keys()):
        card_name = cards[card_num]["name"]
        for pair_idx, pair in enumerate(cards[card_num]["pairs"]):
            pair_number = pair_idx + 1
            if pair["лицо"] is not None:
                tasks.append({
                    "card_number": card_num,
                    "card_name": card_name,
                    "pair_number": pair_number,
                    "side": "лицо",
                    "prompt_text": pair["лицо"],
                })
            if pair["оборот"] is not None:
                tasks.append({
                    "card_number": card_num,
                    "card_name": card_name,
                    "pair_number": pair_number,
                    "side": "оборот",
                    "prompt_text": pair["оборот"],
                })
    return tasks


def get_plan_info(tasks: list[dict]) -> dict:
    """
    Подсчёт сводки по списку задач multiformat.
    Возвращает: cards_count, pairs_count, images_planned.
    """
    if not tasks:
        return {"cards_count": 0, "pairs_count": 0, "images_planned": 0}
    cards_count = len(set(t["card_number"] for t in tasks))
    pairs_set = set((t["card_number"], t["pair_number"]) for t in tasks)
    pairs_count = len(pairs_set)
    images_planned = len(tasks)
    return {
        "cards_count": cards_count,
        "pairs_count": pairs_count,
        "images_planned": images_planned,
    }


def _filter_tasks_by_range(tasks: list[dict], start_card: int, end_card: int | None) -> list[dict]:
    """Оставить только задачи с start_card <= card_number <= end_card."""
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


def _make_chat_name(card_number: int, card_name: str, side: str, pair_number: int) -> str:
    """Имя чата для multiformat: Карточка N - name - side - Промпт P (NAMING_RULES)."""
    return f"Карточка {card_number} - {card_name} - {side} - Промпт {pair_number}"


def _make_filename(card_number: int, side: str, pair_number: int) -> str:
    """Имя файла для multiformat: Карточка_N_side_промпт_P.png (NAMING_RULES)."""
    return f"Карточка_{card_number}_{side}_промпт_{pair_number}.png"


def _generate_single_side(
    task: dict,
    aspect_ratio: str,
    coordinates: dict,
    relative_movements: dict,
    settings: dict,
    log_file,
) -> bool:
    """
    Генерация одной стороны (лицо или оборот) по задаче (ALGO_multiformat п.5).
    Возвращает True при успешном сохранении, False при ошибке.
    """
    card_number = task["card_number"]
    card_name = task["card_name"]
    pair_number = task["pair_number"]
    side = task["side"]
    prompt_text = task.get("prompt_text") or ""

    if not prompt_text.strip():
        write_log_line(log_file, f"[WARN] Пропуск {side} пары {pair_number} (промпт отсутствует)")
        return False

    chat_name = _make_chat_name(card_number, card_name, side, pair_number)
    file_name = _make_filename(card_number, side, pair_number)

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

        # 4. Выбор соотношения сторон
        helpers.select_aspect_ratio(coordinates, aspect_ratio)
        time.sleep(BETWEEN_CLICKS)

        # 5. Вернуться к полю промпта и запустить генерацию
        helpers.click_prompt_input(coordinates)
        time.sleep(BETWEEN_CLICKS)
        helpers.start_generation()
        time.sleep(BETWEEN_CLICKS)

        # 6. Ожидание генерации
        generation_wait = float(settings.get("GENERATION_WAIT", 20.0))
        if settings.get("CHECK_IMAGE_GENERATED", True):
            check_interval = float(settings.get("IMAGE_WAIT_INTERVAL", 2.0))
            box_size = settings.get("IMAGE_CHECK_BOX_SIZE", (100, 100))
            if isinstance(box_size, (list, tuple)) and len(box_size) >= 2:
                box_size = (int(box_size[0]), int(box_size[1]))
            else:
                box_size = (100, 100)
            diff_threshold = float(settings.get("IMAGE_CHECK_THRESHOLD", 0.1))
            image_ready = helpers.wait_until_image_ready(
                coordinates,
                timeout_seconds=generation_wait,
                check_interval=check_interval,
                box_size=box_size,
                diff_threshold=diff_threshold,
            )
            if not image_ready:
                write_log_line(
                    log_file,
                    f"[WARN] Таймаут ожидания изображения: карточка {card_number}, "
                    f"пара {pair_number}, сторона {side}",
                )
        else:
            time.sleep(generation_wait)

        # 7. Сохранение изображения
        helpers.save_image(coordinates, relative_movements, file_name)
        time.sleep(2.0)

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
    Выполнение генерации для мультиформатного режима (лицо + оборот, разные aspect ratio).
    Координаты передаются двумя словарями. Логи в файл: [PLAN], [CARD], [PAIR], [SIDE], [GEN], [OK], [WARN], [SUMMARY].
    """
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    tasks = _filter_tasks_by_range(tasks, start_card, end_card)

    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return

    missing = _check_required_coordinates(coordinates, relative_movements)
    if missing:
        print("Отсутствуют обязательные координаты:", ", ".join(missing))
        return

    face_ratio = settings.get("FACE_ASPECT_RATIO", "4:3")
    back_ratio = settings.get("BACK_ASPECT_RATIO", "3:2")

    log_path = _get_log_filepath()
    log_file = open(log_path, "w", encoding="utf-8")

    try:
        info = get_plan_info(tasks)
        write_log_line(
            log_file,
            f"[PLAN] Режим: multiformat (лицо {face_ratio} + оборот {back_ratio}). "
            f"Карточек: {info['cards_count']}, пар: {info['pairs_count']}, изображений: {info['images_planned']}",
        )
        prompts_file = settings.get("PROMPTS_FILE", "")
        if prompts_file:
            write_log_line(log_file, f"[PLAN] Файл промптов: {prompts_file}")

        print("Генерация запущена. Esc — остановка.")
        total_images = len(tasks)
        done_images = 0
        attempted_images = 0
        cards_seen = set()
        pairs_seen = set()
        last_card = None
        last_pair = None

        for idx, task in enumerate(tasks):
            card_number = task["card_number"]
            pair_number = task["pair_number"]
            side = task["side"]

            if card_number != last_card:
                if last_card is not None:
                    time.sleep(BETWEEN_CARDS)
                write_log_line(log_file, f"[CARD] Карточка {card_number}")
                cards_seen.add(card_number)
                last_card = card_number
                last_pair = None

            if (card_number, pair_number) != last_pair and last_pair is not None:
                time.sleep(BETWEEN_GENERATIONS)
            if (card_number, pair_number) != last_pair:
                write_log_line(log_file, f"[PAIR] Карточка {card_number}, пара {pair_number}")
                pairs_seen.add((card_number, pair_number))
                last_pair = (card_number, pair_number)
            else:
                time.sleep(BETWEEN_GENERATIONS)

            write_log_line(log_file, f"[SIDE] {side}, промпт {pair_number}")

            if task.get("prompt_text") is None or (isinstance(task.get("prompt_text"), str) and not task["prompt_text"].strip()):
                write_log_line(log_file, f"[WARN] Пропуск {side} пары {pair_number} (промпт отсутствует)")
                continue

            aspect_ratio = face_ratio if side == "лицо" else back_ratio
            ok = _generate_single_side(
                task, aspect_ratio, coordinates, relative_movements, settings, log_file
            )
            attempted_images += 1
            if ok:
                done_images += 1
            print(f"Генерация {done_images}/{attempted_images} из {total_images}")
            
            # Проверка: последний ли это промпт для текущей карточки
            is_last_prompt_for_card = (idx == len(tasks) - 1) or (tasks[idx + 1]["card_number"] != card_number)
            if is_last_prompt_for_card:
                # Сохранить следующий номер карточки в настройках для продолжения при следующем запуске
                from utils.settings_store import update_start_card
                update_start_card(card_number + 1)

        summary_msg = (
            f"[SUMMARY] Карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, "
            f"изображений: {done_images}/{total_images}"
        )
        write_log_line(log_file, summary_msg)
        print(f"Готово. Обработано карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, изображений: {done_images}/{total_images}")

    finally:
        log_file.close()


def _generate_single_side(
    task: dict,
    aspect_ratio: str,
    coordinates: dict,
    relative_movements: dict,
    settings: dict,
    log_file,
) -> bool:
    card_number = task["card_number"]
    card_name = task["card_name"]
    pair_number = task["pair_number"]
    side = task["side"]
    prompt_text = task.get("prompt_text") or ""
    task.pop("_last_failure_reason", None)

    if not prompt_text.strip():
        task["_last_failure_reason"] = "пустой промпт"
        write_log_line(log_file, f"[WARN] Пропуск {side} пары {pair_number} (промпт отсутствует)")
        return False

    chat_name = _make_chat_name(card_number, card_name, side, pair_number)
    file_name = _make_filename(card_number, side, pair_number)
    write_log_line(log_file, f"[GEN] Генерация: {chat_name}")

    try:
        helpers.click_new_chat(coordinates)
        time.sleep(NEW_CHAT_WAIT)

        helpers.click_prompt_input(coordinates)
        time.sleep(BETWEEN_CLICKS)
        helpers.paste_prompt_text(prompt_text, delay=AFTER_PASTE)

        helpers.rename_chat(coordinates, chat_name)
        time.sleep(CHAT_RENAME_WAIT)

        helpers.select_aspect_ratio(coordinates, aspect_ratio)
        time.sleep(BETWEEN_CLICKS)

        helpers.click_prompt_input(coordinates)
        time.sleep(BETWEEN_CLICKS)
        helpers.start_generation()
        time.sleep(BETWEEN_CLICKS)

        generation_wait = float(settings.get("GENERATION_WAIT", 20.0))
        if settings.get("CHECK_IMAGE_GENERATED", True):
            check_interval = float(settings.get("IMAGE_WAIT_INTERVAL", 2.0))
            box_size = settings.get("IMAGE_CHECK_BOX_SIZE", (100, 100))
            if isinstance(box_size, (list, tuple)) and len(box_size) >= 2:
                box_size = (int(box_size[0]), int(box_size[1]))
            else:
                box_size = (100, 100)
            diff_threshold = float(settings.get("IMAGE_CHECK_THRESHOLD", 0.1))
            image_ready = helpers.wait_until_image_ready(
                coordinates,
                timeout_seconds=generation_wait,
                check_interval=check_interval,
                box_size=box_size,
                diff_threshold=diff_threshold,
            )
            if not image_ready:
                write_log_line(
                    log_file,
                    f"[WARN] Таймаут ожидания изображения: карточка {card_number}, пара {pair_number}, сторона {side}",
                )
        else:
            time.sleep(generation_wait)

        helpers.save_image(coordinates, relative_movements, file_name)
        time.sleep(2.0)

        task.pop("_last_failure_reason", None)
        write_log_line(log_file, f"[OK] Файл сохранён: {file_name}")
        return True

    except Exception as e:
        task["_last_failure_reason"] = str(e)
        write_log_line(log_file, f"[ERROR] Ошибка при генерации/сохранении {file_name}: {e}")
        return False


def run_mode(
    tasks: list[dict],
    settings: dict,
    coordinates: dict,
    relative_movements: dict,
) -> None:
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    tasks = _filter_tasks_by_range(tasks, start_card, end_card)
    actual_end = end_card if end_card is not None else (max(t["card_number"] for t in tasks) if tasks else start_card)

    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return

    missing = _check_required_coordinates(coordinates, relative_movements)
    if missing:
        print("Отсутствуют обязательные координаты:", ", ".join(missing))
        return

    face_ratio = settings.get("FACE_ASPECT_RATIO", "4:3")
    back_ratio = settings.get("BACK_ASPECT_RATIO", "3:2")
    prompts_file = settings.get("PROMPTS_FILE", "")

    log_path = _get_log_filepath()
    log_file = open(log_path, "w", encoding="utf-8")

    try:
        info = get_plan_info(tasks)
        stats = generation_stats.GenerationRunStats(
            planned_total=len(tasks),
            generation_method="browser",
            mode_name="multiformat",
            estimated_total_seconds=generation_stats.estimate_total_seconds(
                planned_total=len(tasks),
                generation_method="browser",
                mode_name="multiformat",
                settings=settings,
            ),
        )

        write_log_line(
            log_file,
            f"[PLAN] Режим: multiformat (лицо {face_ratio} + оборот {back_ratio}). Карточек: {info['cards_count']}, пар: {info['pairs_count']}, изображений: {info['images_planned']}",
        )
        if prompts_file:
            write_log_line(log_file, f"[PLAN] Файл промптов: {prompts_file}")

        for line in stats.start_summary_lines(
            [
                "Режим: multiformat (browser)",
                f"Aspect ratio: лицо={face_ratio}, оборот={back_ratio}",
                f"Диапазон карточек: {start_card}–{actual_end}",
                f"Файл промптов: {prompts_file or 'не указан'}",
            ]
        ):
            print(line)
            write_log_line(log_file, f"[PLAN] {line}")

        print("Генерация запущена. Esc — остановка.")
        total_images = len(tasks)
        cards_seen = set()
        pairs_seen = set()
        last_card = None
        last_pair = None

        for idx, task in enumerate(tasks):
            card_number = task["card_number"]
            pair_number = task["pair_number"]
            side = task["side"]

            if card_number != last_card:
                if last_card is not None:
                    time.sleep(BETWEEN_CARDS)
                write_log_line(log_file, f"[CARD] Карточка {card_number}")
                cards_seen.add(card_number)
                last_card = card_number
                last_pair = None

            if (card_number, pair_number) != last_pair and last_pair is not None:
                time.sleep(BETWEEN_GENERATIONS)
            if (card_number, pair_number) != last_pair:
                write_log_line(log_file, f"[PAIR] Карточка {card_number}, пара {pair_number}")
                pairs_seen.add((card_number, pair_number))
                last_pair = (card_number, pair_number)
            else:
                time.sleep(BETWEEN_GENERATIONS)

            write_log_line(log_file, f"[SIDE] {side}, промпт {pair_number}")

            aspect_ratio = face_ratio if side == "лицо" else back_ratio
            label = f"карточка {card_number} {side} пара {pair_number}"
            attempt_started = time.monotonic()
            result = _generate_single_side(task, aspect_ratio, coordinates, relative_movements, settings, log_file)
            duration_seconds = time.monotonic() - attempt_started
            ok, reason = generation_stats.normalize_attempt_result(task, result)
            stats.register_attempt(label, ok, duration_seconds, reason)

            print(stats.progress_line(duration_seconds))
            write_log_line(log_file, stats.progress_log_line(label, duration_seconds, ok, reason))

            is_last_prompt_for_card = (idx == len(tasks) - 1) or (tasks[idx + 1]["card_number"] != card_number)
            if is_last_prompt_for_card:
                from utils.settings_store import update_start_card

                update_start_card(card_number + 1)

        write_log_line(log_file, f"[SUMMARY] Карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, изображений: {stats.succeeded}/{total_images}")
        for line in stats.summary_lines():
            print(line)
            if line.startswith("- "):
                write_log_line(log_file, f"[FAILED] {line[2:]}")
            else:
                write_log_line(log_file, f"[SUMMARY] {line}")
        print(f"Готово. Обработано карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, изображений: {stats.succeeded}/{total_images}")

    finally:
        log_file.close()
