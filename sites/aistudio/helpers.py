"""
Общие функции UI для AI Studio (v2).
Клики, ввод текста через буфер, выбор формата, генерация, сохранение, ожидание готовности изображения.
Режимы (standard, multiformat, multiformat_with_refs) используют только этот модуль; прямых вызовов pyautogui в режимах нет.
"""
import io
import time
import pyautogui
import pyperclip
from PIL import ImageChops, ImageStat

try:
    import win32clipboard
    import win32con
except ImportError:
    win32clipboard = None
    win32con = None

# Паузы для сохранения изображения (контекстное меню и диалог)
_CONTEXT_MENU_WAIT = 0.4
_SAVE_DIALOG_WAIT = 0.8


def _point(coords_or_list):
    """Приведение значения координаты из JSON (list) или coords (tuple) к паре (x, y)."""
    p = coords_or_list
    return (int(p[0]), int(p[1])) if p is not None else (0, 0)


# --- Низкоуровневые функции ---


def move_and_click(x: int, y: int, delay: float = 0.1) -> None:
    """Переместить курсор в (x, y) и выполнить клик. Пауза после клика — delay сек."""
    pyautogui.moveTo(x, y)
    time.sleep(0.05)
    pyautogui.click()
    time.sleep(delay)


def press_keys(*keys: str, delay: float = 0.05) -> None:
    """Нажать комбинацию клавиш (например 'ctrl', 'v'). После нажатия — пауза delay сек."""
    pyautogui.hotkey(*keys)
    time.sleep(delay)


# --- UI-функции AI Studio ---


def click_prompt_input(coords: dict) -> None:
    """Клик по полю ввода промпта. coords должен содержать ключ PROMPT_INPUT."""
    x, y = _point(coords["PROMPT_INPUT"])
    move_and_click(x, y)


def paste_prompt_text(prompt_text: str, delay: float = 0.05) -> None:
    """Вставить текст промпта через буфер обмена и Ctrl+V. Фокус должен быть в поле ввода."""
    pyperclip.copy(prompt_text)
    press_keys("ctrl", "v", delay=delay)


def click_new_chat(coords: dict) -> None:
    """Клик по кнопке «Новый чат». coords — ключ NEW_CHAT_BUTTON."""
    x, y = _point(coords["NEW_CHAT_BUTTON"])
    move_and_click(x, y)


def rename_chat(coords: dict, new_name: str) -> None:
    """Переименовать текущий чат: клик по названию, вставка new_name, Enter."""
    x, y = _point(coords["CHAT_NAME_INPUT"])
    move_and_click(x, y)
    time.sleep(0.1)
    paste_prompt_text(new_name)
    press_keys("enter")


def select_aspect_ratio(coords: dict, ratio_text: str) -> None:
    """Выбрать соотношение сторон: клик по селектору, ввод ratio_text, Enter."""
    x, y = _point(coords["ASPECT_RATIO_SELECTOR"])
    move_and_click(x, y)
    time.sleep(0.1)
    paste_prompt_text(ratio_text)
    press_keys("enter")


def click_prompt_input_after_image(coords: dict) -> None:
    """Клик по полю ввода промпта после вставки изображения (PROMPT_INPUT_AFTER_IMAGE). Для режима с референсами."""
    x, y = _point(coords["PROMPT_INPUT_AFTER_IMAGE"])
    move_and_click(x, y)


def copy_image_to_clipboard(image_path: str) -> bool:
    """
    Копирует изображение (PNG/JPG) в буфер обмена Windows (PIL -> BMP -> CF_DIB).
    При ошибке возвращает False; логирование выполняет вызывающий режим.
    """
    if win32clipboard is None or win32con is None:
        return False
    try:
        from PIL import Image
        image = Image.open(image_path)
        # Конвертируем в RGB для BMP (без альфа-канала)
        if image.mode != "RGB":
            image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, "BMP")
        data = output.getvalue()
        output.close()
        # Убираем BMP header (14 байт) для CF_DIB
        data = data[14:]
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        return False


def start_generation() -> None:
    """Запустить генерацию изображения (Ctrl+Enter). Фокус — в поле промпта."""
    press_keys("ctrl", "enter")


def save_image(coords: dict, relative_movements: dict, file_name: str) -> None:
    """
    Сохранить сгенерированное изображение: ПКМ по IMAGE_LOCATION, смещение к пункту
    «Сохранить», клик, ввод имени файла из буфера, Enter.
    При отсутствии TO_SAVE_OPTION или (0,0) выбрасывает ValueError.
    """
    x, y = _point(coords["IMAGE_LOCATION"])
    to_save = relative_movements.get("TO_SAVE_OPTION")
    if to_save is None:
        raise ValueError("TO_SAVE_OPTION не задан в relative_movements")
    dx, dy = _point(to_save)
    if dx == 0 and dy == 0:
        raise ValueError("TO_SAVE_OPTION равен (0, 0)")

    pyautogui.rightClick(x, y)
    time.sleep(_CONTEXT_MENU_WAIT)
    pyautogui.move(dx, dy)
    time.sleep(0.1)
    pyautogui.click()
    time.sleep(_SAVE_DIALOG_WAIT)

    pyperclip.copy(file_name)
    press_keys("ctrl", "v")
    time.sleep(0.05)
    press_keys("enter")


# --- Проверка готовности изображения по скриншоту ---


def grab_result_area(coords: dict, box_size: tuple[int, int]):
    """
    Скриншот прямоугольной области вокруг IMAGE_LOCATION.
    box_size — (width, height). Центр области — coords['IMAGE_LOCATION'].
    Возвращает PIL-совместимое изображение.
    """
    x, y = _point(coords["IMAGE_LOCATION"])
    width, height = box_size
    left = x - width // 2
    top = y - height // 2
    return pyautogui.screenshot(region=(left, top, width, height))


def compute_difference_score(img1, img2) -> float:
    """
    Оценка отличия двух изображений одного размера.
    Чем больше значение — тем сильнее отличие. Нормализация к 0..1 (среднее разности / 255).
    """
    diff_img = ImageChops.difference(img1, img2)
    stat = ImageStat.Stat(diff_img)
    # stat.mean — список средних по каналам (R, G, B)
    mean_all = sum(stat.mean) / len(stat.mean) if stat.mean else 0.0
    return mean_all / 255.0


def wait_until_image_ready(
    coords: dict,
    timeout_seconds: float,
    check_interval: float,
    box_size: tuple[int, int],
    diff_threshold: float,
) -> bool:
    """
    Ждать до таймаута или пока область результата заметно изменится (появление изображения).
    Возвращает True, если разница с baseline достигла порога; False — таймаут.
    Флаги остановки не проверяются (остановка только через завершение процесса).
    """
    baseline = grab_result_area(coords, box_size)
    start_time = time.time()

    while (time.time() - start_time) < timeout_seconds:
        time.sleep(check_interval)
        current = grab_result_area(coords, box_size)
        score = compute_difference_score(baseline, current)
        if score >= diff_threshold:
            return True
    return False
