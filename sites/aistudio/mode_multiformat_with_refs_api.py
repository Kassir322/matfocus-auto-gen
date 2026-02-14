"""
Мультиформатный режим с референсами через Gemini API (лицо/оборот, aspect ratio, референсные изображения).
Использует utils/api_client.py для генерации изображений через API с поддержкой двух моделей:
- API_MODEL — для промптов без референсов
- API_MODEL_WITH_REFS — для промптов с референсными изображениями
"""
import os
import time
from datetime import datetime

from utils import api_client
from utils.prompt_parsers import (
    parse_multiformat_prompts,
    get_plan_info_multiformat,
    filter_tasks_by_range,
)
from utils.log_writer import write_log_line


# Задержка между запросами к API (для соблюдения rate limits)
API_REQUEST_DELAY = 1.0


def safe_filename(name: str) -> str:
    """Преобразует название карточки в безопасное имя файла (REFERENCES_format п.4)."""
    safe = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    for char in [":", "*", "?", '"', "<", ">", "|"]:
        safe = safe.replace(char, "")
    return safe


def get_reference_path(side: str, card_number: int, card_name: str):
    """
    Ищет файл референса для указанной стороны и карточки (REFERENCES_format п.6).
    Поддерживает два формата:
    1. Простой: {номер}_{сторона}.{ext}  (приоритет)
    2. Полный: {сторона}_{номер}_{название}.{ext}  (запасной, для обратной совместимости)
    
    Возвращает путь (str) или None.
    """
    base_folder = os.path.join("data", "images", side)
    
    # Сначала ищем простой формат: {номер}_{сторона}.{ext}
    for ext in ["png", "jpg"]:
        filename = f"{card_number}_{side}.{ext}"
        full_path = os.path.join(base_folder, filename)
        if os.path.exists(full_path):
            return full_path
    
    # Запасной вариант: полный формат с названием (для обратной совместимости)
    safe_name = safe_filename(card_name)
    for ext in ["png", "jpg"]:
        filename = f"{side}_{card_number}_{safe_name}.{ext}"
        full_path = os.path.join(base_folder, filename)
        if os.path.exists(full_path):
            return full_path
    
    return None


def load_tasks_from_file(path: str) -> list[dict]:
    """
    Загрузка задач из файла промптов мультиформатного формата.
    Переиспользует парсер из utils.prompt_parsers.
    
    Args:
        path: путь к файлу промптов
        
    Returns:
        Список задач (dict): card_number, card_name, pair_number, side, prompt_text
    """
    return parse_multiformat_prompts(path)


def get_plan_info(tasks: list[dict]) -> dict:
    """
    Подсчёт сводки по списку задач для вывода плана.
    
    Args:
        tasks: список задач из load_tasks_from_file
        
    Returns:
        dict: cards_count, pairs_count, images_planned
    """
    return get_plan_info_multiformat(tasks)


def _get_log_filepath() -> str:
    """Путь к файлу лога: logs/auto-gen_YYYY-MM-DD_HH-MM-SS.log (LOGGING.md)."""
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join("logs", f"auto-gen_{timestamp}.log")


def _make_filename(card_number: int, card_name: str, side: str, pair_num: int, model_name: str) -> str:
    """
    Имя файла для multiformat_with_refs с указанием модели:
    Карточка_{N}_{safe_name}_{side}_промпт_{P}_{model}.png (NAMING_RULES + model).
    
    Args:
        card_number: номер карточки
        card_name: название карточки
        side: "лицо" или "оборот"
        pair_num: номер пары промптов
        model_name: полное имя модели (например, "imagen-4.0-generate-001" или "gemini-2.5-flash-image")
        
    Returns:
        Имя файла
    """
    safe_name = safe_filename(card_name)
    return f"Карточка_{card_number}_{safe_name}_{side}_промпт_{pair_num}_{model_name}.png"


def _generate_single_image_api(
    task: dict,
    client,
    settings: dict,
    log_file,
) -> bool:
    """
    Генерация одного изображения через API с автоматическим выбором модели.
    Определяет наличие референса и выбирает соответствующую модель:
    - Если референс найден → API_MODEL_WITH_REFS (мультимодальная модель)
    - Если референс не найден → API_MODEL (генеративная модель)
    
    Args:
        task: задача с полями card_number, card_name, pair_number, side, prompt_text
        client: экземпляр genai.Client
        settings: настройки (API_MODEL, API_MODEL_WITH_REFS, API_IMAGE_SIZE, FACE_ASPECT_RATIO, BACK_ASPECT_RATIO)
        log_file: файл для логирования
        
    Returns:
        True при успешном сохранении, False при ошибке
    """
    card_number = task["card_number"]
    card_name = task["card_name"]
    pair_num = task["pair_number"]
    side = task["side"]
    prompt_text = task.get("prompt_text", "").strip()
    
    if not prompt_text:
        write_log_line(log_file, f"[WARN] Пропуск: пустой промпт карточка {card_number} пара {pair_num} {side}")
        return False
    
    # Определение наличия референса
    ref_path = get_reference_path(side, card_number, card_name)
    
    # Выбор модели в зависимости от наличия референса
    if ref_path:
        model = settings.get("API_MODEL_WITH_REFS", "gemini-2.5-flash-image")
        write_log_line(log_file, f"[REF] Найден референс: {ref_path}")
        write_log_line(log_file, f"[MODEL] Используется модель с референсами: {model}")
    else:
        model = settings.get("API_MODEL", "imagen-4.0-generate-001")
        write_log_line(log_file, f"[INFO] Референс не найден, генерация без референса")
        write_log_line(log_file, f"[MODEL] Используется модель без референсов: {model}")
    
    # Формирование имени файла с моделью
    file_name = _make_filename(card_number, card_name, side, pair_num, model)
    write_log_line(log_file, f"[GEN] Генерация: {file_name}")
    
    try:
        # Параметры API из настроек
        image_size = settings.get("API_IMAGE_SIZE", "1K")
        timeout = float(settings.get("API_TIMEOUT", 60.0))
        
        # Aspect ratio из настроек в зависимости от стороны
        if side == "лицо":
            aspect_ratio = settings.get("FACE_ASPECT_RATIO", "4:3")
        else:  # оборот
            aspect_ratio = settings.get("BACK_ASPECT_RATIO", "16:9")
        
        write_log_line(
            log_file, 
            f"[API_REQUEST] model={model}, size={image_size}, aspect={aspect_ratio}, prompt_length={len(prompt_text)}, with_ref={ref_path is not None}"
        )
        
        # Генерация изображения через API (с референсом или без)
        if ref_path:
            # Генерация с референсным изображением
            image_bytes, error_msg = api_client.generate_image_with_reference(
                client=client,
                prompt=prompt_text,
                reference_image_path=ref_path,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                timeout=timeout,
            )
        else:
            # Генерация без референса
            image_bytes, error_msg = api_client.generate_image(
                client=client,
                prompt=prompt_text,
                model=model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                timeout=timeout,
            )
        
        if not image_bytes:
            if error_msg:
                write_log_line(log_file, f"[ERROR] API ошибка для {file_name}:")
                # Разбить длинное сообщение об ошибке на строки
                for line in error_msg.split('\n'):
                    if line.strip():
                        write_log_line(log_file, f"[ERROR]   {line}")
            else:
                write_log_line(log_file, f"[ERROR] API вернул пустой результат для {file_name}")
            return False
        
        write_log_line(log_file, f"[API_RESPONSE] Получено изображение, размер: {len(image_bytes)} байт")
        
        # Сохранение изображения
        success = api_client.save_image_bytes(image_bytes, file_name)
        
        if success:
            write_log_line(log_file, f"[OK] Файл сохранён: {file_name}")
            return True
        else:
            write_log_line(log_file, f"[ERROR] Не удалось сохранить файл: {file_name}")
            return False
        
    except Exception as e:
        write_log_line(log_file, f"[ERROR] Ошибка при генерации/сохранении {file_name}: {e}")
        return False


def run_mode(
    tasks: list[dict],
    settings: dict,
    coordinates: dict = None,  # не используется в API режиме
    relative_movements: dict = None,  # не используется в API режиме
) -> None:
    """
    Выполнение генерации для мультиформатного режима с референсами через API.
    Автоматически выбирает модель в зависимости от наличия референсного изображения.
    
    Args:
        tasks: список задач из load_tasks_from_file
        settings: настройки (API_KEY, API_MODEL, API_MODEL_WITH_REFS, FACE_ASPECT_RATIO, BACK_ASPECT_RATIO и т.д.)
        coordinates: не используется (совместимость сигнатуры с браузерным режимом)
        relative_movements: не используется (совместимость сигнатуры)
    """
    # Фильтрация по диапазону карточек
    start_card = int(settings.get("START_FROM_CARD", 1))
    end_card = settings.get("END_CARD")
    if end_card is not None:
        end_card = int(end_card)
    
    tasks = filter_tasks_by_range(tasks, start_card, end_card)
    # Фактическая конечная карточка для лога (если END_CARD не задан — до конца списка)
    actual_end = end_card if end_card is not None else (max(t["card_number"] for t in tasks) if tasks else start_card)
    
    if not tasks:
        print("Нет задач в выбранном диапазоне карточек.")
        return
    
    # Проверка API ключа
    api_key = settings.get("API_KEY", "").strip()
    if not api_key:
        print("Ошибка: API_KEY не задан. Настройте API ключ в меню.")
        return
    
    # Валидация API ключа
    key_valid, key_error = api_client.check_api_key_format(api_key)
    if not key_valid:
        print(f"Ошибка: {key_error}")
        return
    
    # Инициализация API клиента
    try:
        client = api_client.init_client(api_key)
    except ImportError as e:
        print(f"Ошибка: {e}")
        print("Установите зависимость: pip install google-genai")
        return
    except Exception as e:
        print(f"Ошибка инициализации API клиента: {e}")
        return
    
    # Лог-файл на сессию генерации (LOGGING.md)
    log_path = _get_log_filepath()
    log_file = open(log_path, "w", encoding="utf-8")
    
    try:
        info = get_plan_info(tasks)
        plan_msg = (
            f"[PLAN] Режим: multiformat_with_refs (API). Карточек: {info['cards_count']}, "
            f"пар: {info['pairs_count']}, изображений: {info['images_planned']}"
        )
        write_log_line(log_file, plan_msg)
        write_log_line(log_file, f"[PLAN] Диапазон карточек: {start_card}–{actual_end}")
        
        prompts_file = settings.get("PROMPTS_FILE", "")
        if prompts_file:
            write_log_line(log_file, f"[PLAN] Файл промптов: {prompts_file}")
        
        model_no_ref = settings.get("API_MODEL", "imagen-4.0-generate-001")
        model_with_ref = settings.get("API_MODEL_WITH_REFS", "gemini-2.5-flash-image")
        face_aspect = settings.get("FACE_ASPECT_RATIO", "4:3")
        back_aspect = settings.get("BACK_ASPECT_RATIO", "16:9")
        write_log_line(log_file, f"[PLAN] Модель без референсов: {model_no_ref}")
        write_log_line(log_file, f"[PLAN] Модель с референсами: {model_with_ref}")
        write_log_line(log_file, f"[PLAN] Aspect ratio: лицо={face_aspect}, оборот={back_aspect}")
        
        # Логирование папки для сохранения изображений
        session_folder = api_client.get_session_output_folder()
        write_log_line(log_file, f"[PLAN] Папка для сохранения изображений: {session_folder}")
        print(f"Изображения будут сохранены в: {session_folder}")
        
        print("Генерация через API запущена. Esc — остановка.")
        total_images = len(tasks)
        done_images = 0
        cards_seen = set()
        pairs_seen = set()
        last_card = None
        last_pair = None
        
        for idx, task in enumerate(tasks):
            card_number = task["card_number"]
            pair_number = task["pair_number"]
            side = task["side"]
            
            # Логирование карточки
            if card_number != last_card:
                if last_card is not None:
                    time.sleep(0.5)
                write_log_line(log_file, f"[CARD] Карточка {card_number}")
                cards_seen.add(card_number)
                last_card = card_number
            
            # Логирование пары
            pair_key = (card_number, pair_number)
            if pair_key != last_pair:
                write_log_line(log_file, f"[PAIR] Пара {pair_number}")
                pairs_seen.add(pair_key)
                last_pair = pair_key
            
            # Генерация через API (с автоматическим выбором модели)
            ok = _generate_single_image_api(task, client, settings, log_file)
            if ok:
                done_images += 1
            
            # Прогресс в консоль (только основные шаги)
            print(f"Изображение {done_images}/{total_images} ({side})")
            
            # Проверка: последний ли это промпт для текущей карточки
            is_last_prompt_for_card = (idx == len(tasks) - 1) or (tasks[idx + 1]["card_number"] != card_number)
            if is_last_prompt_for_card:
                # Сохранить следующий номер карточки в настройках для продолжения при следующем запуске
                from utils.settings_store import update_start_card
                update_start_card(card_number + 1)
            
            # Задержка между запросами (для соблюдения rate limits)
            if done_images < total_images:
                time.sleep(API_REQUEST_DELAY)
        
        summary_msg = (
            f"[SUMMARY] Карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, "
            f"изображений: {done_images}/{total_images}"
        )
        write_log_line(log_file, summary_msg)
        print(
            f"Готово. Обработано карточек: {len(cards_seen)}, пар: {len(pairs_seen)}, "
            f"изображений: {done_images}/{total_images}"
        )
        print(f"Лог сохранён: {log_path}")
    
    finally:
        log_file.close()
