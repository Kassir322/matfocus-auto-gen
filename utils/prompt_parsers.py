"""
Парсеры файлов промптов для разных режимов (standard, multiformat).
Переиспользуются в браузерных и API режимах генерации.
"""
import re
from collections import defaultdict


# Regex для стандартного формата: Карточка N - Промпт M: текст
STANDARD_LINE_PATTERN = re.compile(r"^Карточка (\d+) - Промпт (\d+): (.+)$")

# Regex для мультиформатного формата: Карточка N лицо|оборот название - Промпт M: текст (название может содержать дефисы, напр. Русско-японская война)
MULTIFORMAT_LINE_PATTERN = re.compile(r"^Карточка (\d+) (лицо|оборот) (.+?) - Промпт (\d+): (.+)$")


def parse_standard_prompts(path: str) -> list[dict]:
    """
    Разбирает файл промптов стандартного формата.
    
    Формат строки: Карточка N - Промпт M: текст
    
    Args:
        path: путь к файлу промптов
        
    Returns:
        Список задач (dict), каждая задача:
        - card_number: int — номер карточки
        - generation_number: int — номер промпта/генерации
        - prompt_text: str — текст промпта
        
        Порядок: по карточкам, внутри карточки по номеру промпта.
        При ошибке чтения возвращает пустой список.
    """
    # Временное хранилище: card_num -> { prompt_num -> prompt_text }
    temp_data = defaultdict(dict)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                match = STANDARD_LINE_PATTERN.match(line)
                if match:
                    card_num = int(match.group(1))
                    prompt_num = int(match.group(2))
                    prompt_text = match.group(3).strip()
                    temp_data[card_num][prompt_num] = prompt_text
                # невалидные строки пропускаем
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


def _parse_multiformat_to_cards(path: str) -> dict:
    """
    Внутренняя функция: парсит файл мультиформатного формата в структуру карточек.
    
    Возвращает:
        {card_number: {"name": str, "pairs": [{"лицо": str|None, "оборот": str|None}, ...]}}
    """
    temp_data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                match = MULTIFORMAT_LINE_PATTERN.match(line)
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
                    # используем первое название карточки при конфликте
                    if temp_data[card_num]["name"] != card_name:
                        pass
                    temp_data[card_num]["pairs_dict"][pair_num][side] = prompt_text
                # невалидные строки пропускаем
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return {}
    
    # Преобразуем словарь пар в список
    result = {}
    for card_num in sorted(temp_data.keys()):
        card_data = temp_data[card_num]
        pairs_dict = card_data["pairs_dict"]
        sorted_pairs = [pairs_dict[k] for k in sorted(pairs_dict.keys())]
        result[card_num] = {"name": card_data["name"], "pairs": sorted_pairs}
    return result


def parse_multiformat_prompts(path: str) -> list[dict]:
    """
    Разбирает файл промптов мультиформатного формата (лицо/оборот).
    
    Формат строки: Карточка N лицо|оборот название - Промпт M: текст
    
    Args:
        path: путь к файлу промптов
        
    Returns:
        Список задач (dict), каждая задача:
        - card_number: int — номер карточки
        - card_name: str — название карточки
        - pair_number: int — номер пары промптов
        - side: str — сторона ("лицо" или "оборот")
        - prompt_text: str — текст промпта
        
        Порядок: по карточкам, по парам, внутри пары сначала лицо, потом оборот.
        Неполные пары включаются (если только одна сторона имеет промпт).
        При ошибке чтения возвращает пустой список.
    """
    cards = _parse_multiformat_to_cards(path)
    if not cards:
        return []
    
    tasks = []
    for card_num in sorted(cards.keys()):
        card_data = cards[card_num]
        card_name = card_data["name"]
        pairs = card_data["pairs"]
        
        for pair_idx, pair in enumerate(pairs, start=1):
            # Порядок: сначала лицо, потом оборот
            for side in ["лицо", "оборот"]:
                prompt_text = pair.get(side)
                # Добавляем задачу только если есть промпт для этой стороны
                if prompt_text:
                    tasks.append({
                        "card_number": card_num,
                        "card_name": card_name,
                        "pair_number": pair_idx,
                        "side": side,
                        "prompt_text": prompt_text,
                    })
    
    return tasks


def get_plan_info_standard(tasks: list[dict]) -> dict:
    """
    Подсчёт сводки по списку задач стандартного формата.
    
    Args:
        tasks: список задач из parse_standard_prompts
        
    Returns:
        dict с ключами:
        - cards_count: количество уникальных карточек
        - generations_count: количество генераций (= длина tasks)
        - images_planned: количество планируемых изображений (= длина tasks)
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


def get_plan_info_multiformat(tasks: list[dict]) -> dict:
    """
    Подсчёт сводки по списку задач мультиформатного формата.
    
    Args:
        tasks: список задач из parse_multiformat_prompts
        
    Returns:
        dict с ключами:
        - cards_count: количество уникальных карточек
        - pairs_count: количество пар промптов
        - images_planned: количество планируемых изображений (= длина tasks)
    """
    if not tasks:
        return {"cards_count": 0, "pairs_count": 0, "images_planned": 0}
    
    cards_count = len(set(t["card_number"] for t in tasks))
    
    # Подсчёт пар: уникальные комбинации (card_number, pair_number)
    pairs = set((t["card_number"], t["pair_number"]) for t in tasks)
    pairs_count = len(pairs)
    
    return {
        "cards_count": cards_count,
        "pairs_count": pairs_count,
        "images_planned": len(tasks),
    }


def filter_tasks_by_range(tasks: list[dict], start_card: int, end_card: int | None) -> list[dict]:
    """
    Фильтрация задач по диапазону карточек.
    
    Args:
        tasks: список задач (любой формат с полем card_number)
        start_card: начальная карточка (включительно)
        end_card: конечная карточка (включительно), None = до конца
        
    Returns:
        Отфильтрованный список задач
    """
    if not tasks:
        return []
    
    if end_card is None:
        end_card = max(t["card_number"] for t in tasks)
    
    return [t for t in tasks if start_card <= t["card_number"] <= end_card]
