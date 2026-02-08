"""
Режим multiformat_with_refs (v2): лицо + оборот с референсными изображениями.
По ALGO_multiformat_with_refs.md, REFERENCES_format.md. Парсер задач — как в multiformat.
"""
import os
import time
from datetime import datetime

from sites.aistudio import helpers
from sites.aistudio.mode_multiformat import load_tasks_from_file, get_plan_info
from utils.log_writer import write_log_line

# Задержки (ALGO_multiformat_with_refs п.9)
BETWEEN_CLICKS = 0.5
AFTER_PASTE = 1.0
NEW_CHAT_WAIT = 2.0
CHAT_RENAME_WAIT = 1.0
AFTER_IMAGE_PASTE = 2.0
BETWEEN_GENERATIONS = 1.0
BETWEEN_CARDS = 2.0

# Обязательные координаты: multiformat + PROMPT_INPUT_AFTER_IMAGE (COORDINATES_KEYS п.4.3)
REQUIRED_COORDS = [
    "PROMPT_INPUT",
    "IMAGE_LOCATION",
    "NEW_CHAT_BUTTON",
    "CHAT_NAME_INPUT",
    "ASPECT_RATIO_SELECTOR",
    "PROMPT_INPUT_AFTER_IMAGE",
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


def safe_filename(name: str) -> str:
    """Преобразует название карточки в безопасное имя файла (REFERENCES_format п.4)."""
    safe = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    for char in [":", "*", "?", '"', "<", ">", "|"]:
        safe = safe.replace(char, "")
    return safe


def get_reference_path(side: str, card_number: int, card_name: str):
    """
    Ищет файл референса для указанной стороны и карточки (REFERENCES_format п.6).
    Возвращает путь (str) или None.
    """
    safe_name = safe_filename(card_name)
    base_folder = os.path.join("data", "images", side)
    for ext in ["png", "jpg"]:
        filename = f"{side}_{card_number}_{safe_name}.{ext}"
        full_path = os.path.join(base_folder, filename)
        if os.path.exists(full_path):
            return full_path
    return None


def check_all_references(tasks: list[dict]) -> dict:
    """
    Проверяет наличие референсов для всех задач (REFERENCES_format п.7, ALGO п.8).
    Возвращает: {"found_count": int, "missing": [(side, card_num, card_name, expected_name), ...]}.
    """
    found_count = 0
    missing = []
    for t in tasks:
        side = t["side"]
        card_number = t["card_number"]
        card_name = t["card_name"]
        path = get_reference_path(side, card_number, card_name)
        if path:
            found_count += 1
        else:
            safe = safe_filename(card_name)
            expected = f"{side}_{card_number}_{safe}.png/.jpg"
            missing.append((side, card_number, card_name, expected))
    return {"found_count": found_count, "missing": missing}


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
    """Имя чата: Карточка N - name - side - Промпт P (NAMING_RULES)."""
    return f"Карточка {card_number} - {card_name} - {side} - Промпт {pair_number}"


def _make_filename(card_number: int, side: str, pair_number: int) -> str:
    """Имя файла: Карточка_N_side_промпт_P.png (NAMING_RULES)."""
    return f"Карточка_{card_number}_{side}_промпт_{pair_number}.png"


def _generate_single_side_with_ref(
    task: dict,
    aspect_ratio: str,
    coordinates: dict,
    relative_movements: dict,
    settings: dict,
    log_file,
) -> bool:
    """
    Генерация одной стороны с референсом (ALGO_multiformat_with_refs п.9).
    Если референс не найден — продолжаем без него (как multiformat). Возвращает True при успехе.
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

    ref_path = get_reference_path(side, card_number, card_name)
    with_ref = ref_path is not None
    write_log_line(log_file, f"[GEN] Генерация: {chat_name} (с референсом)" if with_ref else f"[GEN] Генерация: {chat_name}")

    try:
        # 1. Новый чат
        helpers.click_new_chat(coordinates)
        time.sleep(NEW_CHAT_WAIT)

        if with_ref:
            # 2a. Вставка референса: клик PROMPT_INPUT, копировать картинку в буфер, Ctrl+V
            helpers.click_prompt_input(coordinates)
            time.sleep(BETWEEN_CLICKS)
            if helpers.copy_image_to_clipboard(ref_path):
                helpers.press_keys("ctrl", "v", delay=AFTER_IMAGE_PASTE)
                write_log_line(log_file, f"[REF] Вставлен референс: {ref_path}")
            else:
                write_log_line(log_file, f"[WARN] Не удалось скопировать референс в буфер: {ref_path}")
            # 2b. Клик в поле промпта после изображения
            helpers.click_prompt_input_after_image(coordinates)
            time.sleep(BETWEEN_CLICKS)
        else:
            write_log_line(log_file, f"[WARN] Референс не найден для {side} карточки {card_number} ({card_name})")
            helpers.click_prompt_input(coordinates)
            time.sleep(BETWEEN_CLICKS)

        # 3. Ввод промпта
        helpers.paste_prompt_text(prompt_text, delay=AFTER_PASTE)

        # 4. Переименование чата
        helpers.rename_chat(coordinates, chat_name)
        time.sleep(CHAT_RENAME_WAIT)

        # 5. Выбор соотношения сторон
        helpers.select_aspect_ratio(coordinates, aspect_ratio)
        time.sleep(BETWEEN_CLICKS)

        # 6. Вернуться к полю промпта и запустить генерацию (с референсом — PROMPT_INPUT_AFTER_IMAGE, без — PROMPT_INPUT)
        if with_ref:
            helpers.click_prompt_input_after_image(coordinates)
        else:
            helpers.click_prompt_input(coordinates)
        time.sleep(BETWEEN_CLICKS)
        helpers.start_generation()
        time.sleep(BETWEEN_CLICKS)

        # 7. Ожидание генерации
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

        # 8. Сохранение изображения
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
    Выполнение генерации для режима multiformat_with_refs (лицо + оборот с референсами).
    Проверка референсов перед стартом; при отсутствующих — вопрос «Продолжить без них? (y/n)».
    """
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    tasks = _filter_tasks_by_range(tasks, start_card, end_card)

    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return

    missing_coords = _check_required_coordinates(coordinates, relative_movements)
    if missing_coords:
        print("Отсутствуют обязательные координаты:", ", ".join(missing_coords))
        return

    # Проверка референсов (ALGO п.8)
    ref_result = check_all_references(tasks)
    total_refs = len(tasks)
    found_refs = ref_result["found_count"]
    missing_refs = ref_result["missing"]

    if missing_refs:
        print("[WARN] Отсутствуют референсы:")
        for side, card_num, card_name, expected in missing_refs:
            print(f"  - {side} карточки {card_num} ({card_name})")
        answer = input("Продолжить без них? (y/n): ").strip().lower()
        if answer != "y":
            print("Запуск отменён.")
            return

    face_ratio = settings.get("FACE_ASPECT_RATIO", "4:3")
    back_ratio = settings.get("BACK_ASPECT_RATIO", "3:2")

    log_path = _get_log_filepath()
    log_file = open(log_path, "w", encoding="utf-8")

    try:
        info = get_plan_info(tasks)
        write_log_line(
            log_file,
            f"[PLAN] Режим: multiformat_with_refs. Формат лицо: {face_ratio}, оборот: {back_ratio}. "
            f"Карточек: {info['cards_count']}, пар: {info['pairs_count']}, изображений: {info['images_planned']}",
        )
        if not missing_refs:
            write_log_line(log_file, f"[CHECK] Референсы: {found_refs}/{total_refs} найдено")
        prompts_file = settings.get("PROMPTS_FILE", "")
        if prompts_file:
            write_log_line(log_file, f"[PLAN] Файл промптов: {prompts_file}")

        print("Генерация запущена. Esc — остановка.")
        total_images = len(tasks)
        done_images = 0
        cards_seen = set()
        pairs_seen = set()
        last_card = None
        last_pair = None

        for task in tasks:
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
            ok = _generate_single_side_with_ref(
                task, aspect_ratio, coordinates, relative_movements, settings, log_file
            )
            if ok:
                done_images += 1
            print(f"Генерация {done_images} из {total_images}")

        summary_msg = (
            f"[SUMMARY] Карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, "
            f"изображений: {done_images}/{total_images}"
        )
        write_log_line(log_file, summary_msg)
        print(f"Готово. Обработано карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, изображений: {done_images}/{total_images}")

    finally:
        log_file.close()
