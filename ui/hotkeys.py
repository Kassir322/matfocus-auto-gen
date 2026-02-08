"""
Управление горячими клавишами v2.
Зависимости: keyboard, pyautogui, utils.settings_store, utils.coordinates_store, utils.process_control.
Без config.* и без ProcessManager/SettingsManager.
"""
import os
import signal

import keyboard
import pyautogui

from utils import process_control
from utils import settings_store
from utils.coordinates_store import (
    DEFAULT_COORDINATES,
    DEFAULT_RELATIVE_MOVEMENTS,
    load_coordinates,
    set_coordinate,
)

# Режимы по сайту для Ctrl+7 (как в console_menu)
MODES_BY_SITE = {"aistudio": ["standard", "multiformat", "multiformat_with_refs"]}

# Описания координат для меню (COORDINATES_KEYS §9)
COORD_DESCRIPTIONS = {
    "PROMPT_INPUT": "Поле ввода промпта",
    "IMAGE_LOCATION": "Место клика на сгенерированное изображение",
    "NEW_CHAT_BUTTON": "Кнопка создания нового чата",
    "CHAT_NAME_INPUT": "Поле ввода названия чата",
    "CHAT_NAME_POPUP": "Поле ввода в попапе (если есть)",
    "CHAT_NAME_CONFIRM": "Кнопка подтверждения в попапе (если есть)",
    "ASPECT_RATIO_SELECTOR": "Выпадающий список соотношения сторон [ДЛЯ МУЛЬТИФОРМАТНОГО РЕЖИМА]",
    "PROMPT_INPUT_AFTER_IMAGE": "Поле ввода после вставки изображения [ДЛЯ РЕЖИМА С РЕФЕРЕНСАМИ]",
    "TO_SAVE_OPTION": "Смещение к пункту «Сохранить изображение»",
}


def _validate_aspect_ratio(ratio: str) -> bool:
    """Проверка формата X:Y для соотношения сторон."""
    try:
        if ":" not in ratio:
            return False
        parts = ratio.split(":")
        if len(parts) != 2:
            return False
        float(parts[0])
        float(parts[1])
        return True
    except (ValueError, AttributeError):
        return False


class HotkeyManager:
    """
    Менеджер хоткеев v2.
    Конструктор: on_start_generation, on_setup_window, on_show_plan — три callback'а.
    """

    def __init__(self, on_start_generation, on_setup_window, on_show_plan):
        self.on_start_generation = on_start_generation
        self.on_setup_window = on_setup_window
        self.on_show_plan = on_show_plan
        self.coordinate_capture_mode = False
        self.coordinate_to_set = None

    def get_mouse_position(self):
        """Ctrl+Shift+P: получить координаты курсора или сохранить в выбранную координату."""
        x, y = pyautogui.position()

        if self.coordinate_capture_mode and self.coordinate_to_set:
            coordinates, relative_movements = load_coordinates()
            set_coordinate(self.coordinate_to_set, x, y, coordinates, relative_movements)
            self.coordinate_capture_mode = False
            self.coordinate_to_set = None
            print("[КООРДИНАТЫ] Координата установлена и сохранена.")
        else:
            print(f"[КООРДИНАТЫ] Курсор: X={x}, Y={y}")

    def show_coordinates_menu(self):
        """Ctrl+0: меню настройки координат (список ключей по COORDINATES_KEYS §8)."""
        coordinates, relative_movements = load_coordinates()
        all_keys = list(DEFAULT_COORDINATES.keys()) + list(DEFAULT_RELATIVE_MOVEMENTS.keys())

        print("-" * 60)
        print("МЕНЮ НАСТРОЙКИ КООРДИНАТ")
        print("-" * 60)
        print("=== КООРДИНАТЫ ===")
        for i, name in enumerate(DEFAULT_COORDINATES.keys(), 1):
            val = coordinates.get(name, (0, 0))
            status = "задана" if val != (0, 0) else "не задана"
            desc = COORD_DESCRIPTIONS.get(name, "")
            extra = ""
            if name == "ASPECT_RATIO_SELECTOR":
                extra = " [ДЛЯ МУЛЬТИФОРМАТНОГО РЕЖИМА]"
            elif name == "PROMPT_INPUT_AFTER_IMAGE":
                extra = " [ДЛЯ РЕЖИМА С РЕФЕРЕНСАМИ]"
            print(f"  {i}. {name}: {val} - {status} {extra}")
        print("=== ОТНОСИТЕЛЬНЫЕ ДВИЖЕНИЯ ===")
        for i, name in enumerate(DEFAULT_RELATIVE_MOVEMENTS.keys(), len(DEFAULT_COORDINATES) + 1):
            val = relative_movements.get(name, (0, 0))
            status = "задано" if val != (0, 0) else "не задано"
            desc = COORD_DESCRIPTIONS.get(name, "")
            print(f"  {i}. {name}: {val} - {status}")
        print("  0. Отмена")
        print("-" * 60)

        try:
            choice = input("Введите номер координаты: ").strip()
            if not choice or choice == "0":
                print("Настройка отменена")
                return
            idx = int(choice)
            if 1 <= idx <= len(all_keys):
                coord_name = all_keys[idx - 1]
                print(f"\nВыбрана координата: {coord_name}")
                print(COORD_DESCRIPTIONS.get(coord_name, ""))
                if coord_name == "ASPECT_RATIO_SELECTOR":
                    print("Найдите выпадающий список соотношения сторон (обычно справа от поля промпта).")
                elif coord_name == "PROMPT_INPUT_AFTER_IMAGE":
                    print("Наведите на поле ввода промпта ПОСЛЕ вставки изображения-референса.")
                print("Наведите курсор на нужный элемент и нажмите Ctrl+Shift+P")
                self.coordinate_capture_mode = True
                self.coordinate_to_set = coord_name
            else:
                print("Неверный номер.")
        except ValueError:
            print("Введите число.")
        except KeyboardInterrupt:
            print("\nНастройка отменена")

    def _configure_start_card(self):
        """Ctrl+1: настроить START_FROM_CARD."""
        settings = settings_store.load_settings()
        start = settings.get("START_FROM_CARD", 1)
        end = settings.get("END_CARD", 50)
        print(f"Текущая стартовая карточка: {start}, конечная: {end}")
        try:
            raw = input("Новая стартовая карточка (>=1, Enter — отмена): ").strip()
            if not raw:
                return
            start = int(raw)
            if start < 1:
                print("Ошибка: номер должен быть >= 1")
                return
            if start > end:
                settings["END_CARD"] = start
            settings["START_FROM_CARD"] = start
            settings_store.apply_defaults(settings)
            settings_store.save_settings(settings)
            print(f"Стартовая карточка установлена: {start}")
        except ValueError:
            print("Введите число.")

    def _configure_end_card(self):
        """Ctrl+6: настроить END_CARD."""
        settings = settings_store.load_settings()
        start = settings.get("START_FROM_CARD", 1)
        end = settings.get("END_CARD", 50)
        print(f"Стартовая карточка: {start}, текущая конечная: {end}")
        try:
            raw = input(f"До какой карточки обрабатывать (>={start}, Enter — отмена): ").strip()
            if not raw:
                return
            end = int(raw)
            if end < start:
                print(f"Ошибка: конечная должна быть >= {start}")
                return
            settings["END_CARD"] = end
            settings_store.apply_defaults(settings)
            settings_store.save_settings(settings)
            print(f"Конечная карточка установлена: {end}")
        except ValueError:
            print("Введите число.")

    def _configure_generation_wait(self):
        """Ctrl+3: настроить GENERATION_WAIT (10–120 сек)."""
        settings = settings_store.load_settings()
        cur = settings.get("GENERATION_WAIT", 20.0)
        print(f"Текущее время ожидания генерации: {cur} сек")
        try:
            raw = input("Новое значение (10–120 сек, Enter — отмена): ").strip()
            if not raw:
                return
            val = float(raw)
            if val < 10 or val > 120:
                print("Ошибка: значение от 10 до 120")
                return
            settings["GENERATION_WAIT"] = val
            settings_store.save_settings(settings)
            print(f"Время ожидания генерации установлено: {val} сек")
        except ValueError:
            print("Введите число.")

    def _configure_image_wait_interval(self):
        """Ctrl+8: настроить IMAGE_WAIT_INTERVAL (1–60 сек)."""
        settings = settings_store.load_settings()
        cur = settings.get("IMAGE_WAIT_INTERVAL", 2.0)
        print(f"Текущий интервал проверки изображения: {cur} сек")
        try:
            raw = input("Новое значение (1–60 сек, Enter — отмена): ").strip()
            if not raw:
                return
            val = float(raw)
            if val < 1 or val > 60:
                print("Ошибка: значение от 1 до 60")
                return
            settings["IMAGE_WAIT_INTERVAL"] = val
            settings_store.save_settings(settings)
            print(f"Интервал установлен: {val} сек")
        except ValueError:
            print("Введите число.")

    def _toggle_image_check(self):
        """Ctrl+4: переключить CHECK_IMAGE_GENERATED."""
        settings = settings_store.load_settings()
        cur = settings.get("CHECK_IMAGE_GENERATED", True)
        settings["CHECK_IMAGE_GENERATED"] = not cur
        settings_store.save_settings(settings)
        status = "включена" if settings["CHECK_IMAGE_GENERATED"] else "выключена"
        print(f"Проверка изображений: {status}")

    def _configure_aspect_ratios(self):
        """Ctrl+9: настроить FACE_ASPECT_RATIO и BACK_ASPECT_RATIO (формат X:Y)."""
        settings = settings_store.load_settings()
        face = settings.get("FACE_ASPECT_RATIO", "4:3")
        back = settings.get("BACK_ASPECT_RATIO", "3:2")
        print("Формат: X:Y (например 16:9, 3:4). Пустая строка — не менять.")
        try:
            raw_face = input(f"Соотношение для лицевой стороны [{face}]: ").strip()
            if raw_face and _validate_aspect_ratio(raw_face):
                settings["FACE_ASPECT_RATIO"] = raw_face
                print(f"Лицевая сторона: {raw_face}")
            raw_back = input(f"Соотношение для оборотной стороны [{back}]: ").strip()
            if raw_back and _validate_aspect_ratio(raw_back):
                settings["BACK_ASPECT_RATIO"] = raw_back
                print(f"Оборотная сторона: {raw_back}")
            if raw_face or raw_back:
                settings_store.save_settings(settings)
        except KeyboardInterrupt:
            print("\nНастройка отменена")

    def _configure_mode(self):
        """Ctrl+7: выбор режима для текущего сайта (CURRENT_MODE)."""
        settings = settings_store.load_settings()
        site = settings.get("CURRENT_SITE", "aistudio")
        modes = MODES_BY_SITE.get(site, ["standard", "multiformat"])
        current = settings.get("CURRENT_MODE", "standard")
        print("Выберите режим:")
        for i, m in enumerate(modes, 1):
            mark = " (текущий)" if m == current else ""
            print(f"  {i}. {m}{mark}")
        try:
            raw = input("Номер (Enter — отмена): ").strip()
            if not raw:
                return
            idx = int(raw)
            if 1 <= idx <= len(modes):
                settings["CURRENT_MODE"] = modes[idx - 1]
                settings_store.save_settings(settings)
                print(f"Режим установлен: {settings['CURRENT_MODE']}")
            else:
                print("Неверный номер.")
        except ValueError:
            print("Введите число.")

    def _show_settings_and_plan(self):
        """Ctrl+5: показать текущие настройки и план (on_show_plan)."""
        settings = settings_store.load_settings()
        print("-" * 50)
        print("ТЕКУЩИЕ НАСТРОЙКИ (v2)")
        print(f"  Сайт: {settings.get('CURRENT_SITE')}")
        print(f"  Режим: {settings.get('CURRENT_MODE')}")
        print(f"  Файл промптов: {settings.get('PROMPTS_FILE')}")
        print(f"  Стартовая карточка: {settings.get('START_FROM_CARD')}")
        print(f"  Конечная карточка: {settings.get('END_CARD')}")
        print(f"  Карточек к обработке: {settings.get('CARDS_TO_PROCESS')}")
        print(f"  GENERATION_WAIT: {settings.get('GENERATION_WAIT')} сек")
        print(f"  IMAGE_WAIT_INTERVAL: {settings.get('IMAGE_WAIT_INTERVAL')} сек")
        print(f"  CHECK_IMAGE_GENERATED: {settings.get('CHECK_IMAGE_GENERATED')}")
        print(f"  FACE_ASPECT_RATIO: {settings.get('FACE_ASPECT_RATIO')}")
        print(f"  BACK_ASPECT_RATIO: {settings.get('BACK_ASPECT_RATIO')}")
        print("-" * 50)
        self.on_show_plan(settings)

    def kill_console(self):
        """Ctrl+Esc: убить консоль (SIGINT)."""
        os.kill(os.getpid(), signal.SIGINT)

    def on_esc_stop_worker(self):
        """Esc: только жёсткая остановка воркера генерации (v2)."""
        process_control.stop_worker()

    def register_hotkeys(self):
        """Регистрация всех горячих клавиш по HOTKEYS_V2. Без Ctrl+2 и Ctrl+Shift+Q."""
        keyboard.add_hotkey("ctrl+shift+p", self.get_mouse_position)
        keyboard.add_hotkey("ctrl+0", self.show_coordinates_menu)
        keyboard.add_hotkey("ctrl+1", self._configure_start_card)
        keyboard.add_hotkey("ctrl+3", self._configure_generation_wait)
        keyboard.add_hotkey("ctrl+4", self._toggle_image_check)
        keyboard.add_hotkey("ctrl+5", self._show_settings_and_plan)
        keyboard.add_hotkey("ctrl+6", self._configure_end_card)
        keyboard.add_hotkey("ctrl+7", self._configure_mode)
        keyboard.add_hotkey("ctrl+8", self._configure_image_wait_interval)
        keyboard.add_hotkey("ctrl+9", self._configure_aspect_ratios)
        keyboard.add_hotkey("ctrl+shift+v", self.on_setup_window)
        keyboard.add_hotkey("ctrl+shift+s", self.on_start_generation)
        keyboard.add_hotkey("ctrl+esc", self.kill_console)
        keyboard.add_hotkey("esc", self.on_esc_stop_worker)
