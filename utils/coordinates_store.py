"""
Хранилище координат v2: чтение/запись data/coordinates.json.
Два словаря: coordinates (точки клика) и relative_movements (смещения).
Без UI и без pyautogui — только JSON.
"""
import json
import os

# Путь к файлу координат (относительно рабочей директории)
COORDINATES_PATH = "data/coordinates.json"

# Дефолты по COORDINATES_KEYS, раздел 5. (0, 0) = не задана.
DEFAULT_COORDINATES = {
    "PROMPT_INPUT": (0, 0),
    "IMAGE_LOCATION": (0, 0),
    "NEW_CHAT_BUTTON": (0, 0),
    "CHAT_NAME_INPUT": (0, 0),
    "CHAT_NAME_POPUP": (0, 0),
    "CHAT_NAME_CONFIRM": (0, 0),
    "ASPECT_RATIO_SELECTOR": (0, 0),
    "PROMPT_INPUT_AFTER_IMAGE": (0, 0),
}

DEFAULT_RELATIVE_MOVEMENTS = {
    "TO_SAVE_OPTION": (0, 0),
}


def _list_to_tuple(value):
    """Преобразует список [x, y] в кортеж (x, y) для единообразия в коде."""
    if isinstance(value, list) and len(value) >= 2:
        return (int(value[0]), int(value[1]))
    return (0, 0)


def _merge_with_defaults(coords: dict, defaults: dict) -> dict:
    """Мержит загруженные координаты с дефолтами: все ключи из defaults есть в результате."""
    result = dict(defaults)
    for key, value in coords.items():
        if key in result:
            result[key] = _list_to_tuple(value) if isinstance(value, list) else (0, 0)
    return result


def load_coordinates() -> tuple[dict, dict]:
    """
    Читает data/coordinates.json.
    Возвращает (coordinates, relative_movements); значения — кортежи (x, y).
    Если файла нет или ошибка — возвращает дефолтные словари.
    """
    try:
        if not os.path.isfile(COORDINATES_PATH):
            coords = dict(DEFAULT_COORDINATES)
            moves = dict(DEFAULT_RELATIVE_MOVEMENTS)
            return (coords, moves)
        with open(COORDINATES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_coords = data.get("coordinates") or {}
        raw_moves = data.get("relative_movements") or {}
        coordinates = _merge_with_defaults(raw_coords, DEFAULT_COORDINATES)
        relative_movements = _merge_with_defaults(raw_moves, DEFAULT_RELATIVE_MOVEMENTS)
        return (coordinates, relative_movements)
    except (OSError, json.JSONDecodeError):
        return (dict(DEFAULT_COORDINATES), dict(DEFAULT_RELATIVE_MOVEMENTS))


def save_coordinates(coordinates: dict, relative_movements: dict) -> None:
    """
    Записывает координаты в data/coordinates.json.
    В JSON сохраняются списки [x, y]. Создаёт папку data/ при необходимости.
    """
    dir_path = os.path.dirname(COORDINATES_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    data = {
        "coordinates": {k: list(v) if isinstance(v, (list, tuple)) else [0, 0] for k, v in coordinates.items()},
        "relative_movements": {k: list(v) if isinstance(v, (list, tuple)) else [0, 0] for k, v in relative_movements.items()},
    }
    with open(COORDINATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def set_coordinate(
    name: str,
    x: int,
    y: int,
    coordinates: dict,
    relative_movements: dict,
) -> None:
    """
    Записывает (x, y) в координату или относительное движение с именем name.
    Если name в coordinates — обновляет coordinates[name]; иначе если в relative_movements — relative_movements[name].
    После изменения вызывает save_coordinates.
    """
    if name in coordinates:
        coordinates[name] = (x, y)
    elif name in relative_movements:
        relative_movements[name] = (x, y)
    save_coordinates(coordinates, relative_movements)
