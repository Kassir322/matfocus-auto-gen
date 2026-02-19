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
    Конструктор: on_start_generation, on_setup_window, on_show_plan; опционально on_start_api для Ctrl+Shift+A.
    """

    def __init__(self, on_start_generation, on_setup_window, on_show_plan, on_start_api=None):
        self.on_start_generation = on_start_generation
        self.on_setup_window = on_setup_window
        self.on_show_plan = on_show_plan
        self.on_start_api = on_start_api
        self.coordinate_capture_mode = False
        self.coordinate_to_set = None

    def get_mouse_position(self):
        """Ctrl+Shift+P: получить координаты курсора или сохранить в выбранную координату."""
        if self._block_if_api_running():
            return
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
        if self._block_if_api_running():
            return
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
        if self._block_if_api_running():
            return
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
                print(f"Конечная карточка установлена в {start}. Для обработки нескольких карточек настройте её через Ctrl+6.")
            settings["START_FROM_CARD"] = start
            settings_store.apply_defaults(settings)
            settings_store.save_settings(settings)
            print(f"Стартовая карточка установлена: {start}")
        except ValueError:
            print("Введите число.")

    def _configure_end_card(self):
        """Ctrl+6: настроить END_CARD."""
        if self._block_if_api_running():
            return
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
        if self._block_if_api_running():
            return
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
        if self._block_if_api_running():
            return
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
        if self._block_if_api_running():
            return
        settings = settings_store.load_settings()
        cur = settings.get("CHECK_IMAGE_GENERATED", True)
        settings["CHECK_IMAGE_GENERATED"] = not cur
        settings_store.save_settings(settings)
        status = "включена" if settings["CHECK_IMAGE_GENERATED"] else "выключена"
        print(f"Проверка изображений: {status}")

    def _configure_aspect_ratios(self):
        """Ctrl+9: настроить FACE_ASPECT_RATIO и BACK_ASPECT_RATIO (формат X:Y)."""
        if self._block_if_api_running():
            return
        settings = settings_store.load_settings()
        face = settings.get("FACE_ASPECT_RATIO", "4:3")
        back = settings.get("BACK_ASPECT_RATIO", "16:9")
        generation_method = settings.get("GENERATION_METHOD", "browser")
        
        print("\n=== НАСТРОЙКА СООТНОШЕНИЙ СТОРОН ===")
        
        # Показать поддерживаемые значения для API режима
        if generation_method == "api":
            print("\nВАЖНО: Для Imagen 4 поддерживаются только следующие соотношения:")
            print("  - 1:1 (квадрат)")
            print("  - 4:3 (горизонтальная)")
            print("  - 3:4 (вертикальная)")
            print("  - 16:9 (широкая горизонтальная, рекомендуется для оборота)")
            print("  - 9:16 (широкая вертикальная)")
            print("\nДля Gemini моделей поддерживаются все стандартные соотношения.")
        
        print("\nФормат: X:Y (например 16:9, 4:3). Пустая строка — не менять.")
        try:
            raw_face = input(f"Соотношение для лицевой стороны [{face}]: ").strip()
            if raw_face and _validate_aspect_ratio(raw_face):
                # Дополнительная проверка для API режима с Imagen
                if generation_method == "api":
                    api_model = settings.get("API_MODEL", "")
                    if api_model.startswith("imagen-4") and raw_face not in ["1:1", "4:3", "3:4", "16:9", "9:16"]:
                        print("Внимание: соотношение", raw_face, "может не поддерживаться Imagen 4.")
                        print("Рекомендуется использовать: 1:1, 4:3, 3:4, 16:9, 9:16")
                settings["FACE_ASPECT_RATIO"] = raw_face
                print("Лицевая сторона:", raw_face)
            raw_back = input(f"Соотношение для оборотной стороны [{back}]: ").strip()
            if raw_back and _validate_aspect_ratio(raw_back):
                # Дополнительная проверка для API режима с Imagen
                if generation_method == "api":
                    api_model = settings.get("API_MODEL", "")
                    if api_model.startswith("imagen-4") and raw_back not in ["1:1", "4:3", "3:4", "16:9", "9:16"]:
                        print("Внимание: соотношение", raw_back, "может не поддерживаться Imagen 4.")
                        print("Рекомендуется использовать: 1:1, 4:3, 3:4, 16:9, 9:16")
                settings["BACK_ASPECT_RATIO"] = raw_back
                print("Оборотная сторона:", raw_back)
            if raw_face or raw_back:
                settings_store.save_settings(settings)
        except KeyboardInterrupt:
            print("\nНастройка отменена")

    def _configure_api_model(self, settings: dict) -> bool:
        """
        Выбор модели качества и разрешения для API генерации.
        
        Args:
            settings: словарь настроек (будет изменён)
            
        Returns:
            True если настройки сохранены, False если отменено
        """
        print("\n=== НАСТРОЙКА МОДЕЛЕЙ API ===")
        
        current_model = settings.get("API_MODEL", "imagen-4.0-generate-001")
        current_model_refs = settings.get("API_MODEL_WITH_REFS", "gemini-2.5-flash-image")
        current_size = settings.get("API_IMAGE_SIZE", "2K")
        
        # 1. Настройка модели для промптов БЕЗ референсов
        print("\n--- МОДЕЛЬ ДЛЯ ПРОМПТОВ БЕЗ РЕФЕРЕНСОВ ---")
        print("Используется в режимах: standard, multiformat, multiformat_with_refs (если референс отсутствует)")
        
        # Список доступных моделей для промптов без референсов
        models = {
            "1": ("imagen-4.0-fast-generate-001", "Imagen 4 Fast", "быстро, базовое качество"),
            "2": ("imagen-4.0-generate-001", "Imagen 4 Standard", "оптимально, хорошее качество (рекомендуется)"),
            "3": ("imagen-4.0-ultra-generate-001", "Imagen 4 Ultra", "медленно, максимальное качество"),
            "4": ("gemini-2.5-flash-image", "Gemini 2.5 Flash", "устаревшая, быстро, низкое качество"),
        }
        
        print("\nВыберите модель для промптов БЕЗ референсов:")
        for key, (model_id, name, desc) in models.items():
            current_mark = " (текущая)" if model_id == current_model else ""
            print(f"  {key}. {name}{current_mark}")
            print(f"     {desc}")
        
        try:
            model_choice = input("Выбор (Enter — не менять): ").strip()
            
            if model_choice and model_choice in models:
                selected_model = models[model_choice][0]
                settings["API_MODEL"] = selected_model
                print(f"✓ Выбрана модель (без референсов): {models[model_choice][1]}")
            elif model_choice == "":
                selected_model = current_model
            else:
                print("Неверный выбор.")
                return False
            
            # 2. Настройка модели для промптов С референсами
            print("\n--- МОДЕЛЬ ДЛЯ ПРОМПТОВ С РЕФЕРЕНСАМИ ---")
            print("Используется в режиме: multiformat_with_refs (когда референс найден)")
            print("ВАЖНО: Только мультимодальные модели Gemini поддерживают работу с референсными изображениями!")
            
            # Список мультимодальных моделей для промптов с референсами
            models_with_ref = {
                "1": ("gemini-2.5-flash-image", "Gemini 2.5 Flash Image", "быстро, рекомендуется для референсов"),
                "2": ("gemini-3-pro-image-preview", "Gemini 3 Pro Image Preview", "экспериментальная, более высокое качество"),
            }
            
            print("\nВыберите модель для промптов С референсами:")
            for key, (model_id, name, desc) in models_with_ref.items():
                current_mark = " (текущая)" if model_id == current_model_refs else ""
                print(f"  {key}. {name}{current_mark}")
                print(f"     {desc}")
            
            model_refs_choice = input("Выбор (Enter — не менять): ").strip()
            
            if model_refs_choice and model_refs_choice in models_with_ref:
                selected_model_refs = models_with_ref[model_refs_choice][0]
                settings["API_MODEL_WITH_REFS"] = selected_model_refs
                print(f"✓ Выбрана модель (с референсами): {models_with_ref[model_refs_choice][1]}")
            elif model_refs_choice == "":
                selected_model_refs = current_model_refs
            else:
                print("Неверный выбор.")
                return False
            
            # Подсказка: Imagen 4 поддерживает только определённые соотношения сторон
            if selected_model.startswith("imagen-4"):
                print("\nImagen 4 поддерживает только следующие соотношения сторон:")
                print("  1:1, 4:3, 3:4, 16:9, 9:16")
                print("  Настройте через Ctrl+9 если используются другие значения.")
            
            # 3. Выбор разрешения (только для Imagen 4)
            if selected_model.startswith("imagen-4"):
                print("\nВыберите разрешение изображения:")
                print(f"  1. 1K (1024x1024) - быстрее")
                print(f"  2. 2K (2048x2048) - выше качество (рекомендуется){' (текущее)' if current_size == '2K' else ''}")
                
                size_choice = input("Выбор (Enter — не менять): ").strip()
                
                if size_choice == "1":
                    settings["API_IMAGE_SIZE"] = "1K"
                    print("✓ Разрешение: 1K")
                elif size_choice == "2":
                    settings["API_IMAGE_SIZE"] = "2K"
                    print("✓ Разрешение: 2K")
                elif size_choice == "":
                    pass  # Не меняем
                else:
                    print("Неверный выбор.")
                    return False
            else:
                # Для старых моделей оставляем 1K
                settings["API_IMAGE_SIZE"] = "1K"
            
            return True
            
        except KeyboardInterrupt:
            print("\nНастройка отменена.")
            return False

    def _check_and_configure_api_key(self, settings: dict) -> bool:
        """
        Проверка и настройка API ключа.
        Если ключ есть — предлагает обновить или продолжить.
        Если ключа нет — обязательно запрашивает ввод.
        
        Args:
            settings: словарь настроек (будет изменён при вводе нового ключа)
            
        Returns:
            True если ключ задан/введён успешно, False если пользователь отменил
        """
        from utils import api_client
        
        current_key = settings.get("API_KEY", "").strip()
        
        print("\n=== НАСТРОЙКА API ===")
        if current_key:
            # Ключ уже есть - предлагаем обновить или продолжить
            print(f"API ключ: {current_key[:10]}... (первые 10 символов)")
            print("\n1. Ввести новый API ключ")
            print("2. Продолжить с текущим ключом")
            print("0. Отмена")
            print("\nПолучить ключ: https://aistudio.google.com/apikey")
            
            try:
                choice = input("Выбор: ").strip()
                if choice == "0":
                    print("Настройка отменена.")
                    return False
                elif choice == "2":
                    return True
                elif choice != "1":
                    print("Неверный выбор.")
                    return False
                # Продолжаем к вводу нового ключа ниже
            except KeyboardInterrupt:
                print("\nНастройка отменена.")
                return False
        else:
            # Ключа нет - обязательный ввод
            print("API ключ не задан!")
            print("Получите ключ на: https://aistudio.google.com/apikey")
        
        # Запрос ввода ключа
        try:
            new_key = input("Введите API ключ (или 0 для отмены): ").strip()
            if new_key == "0":
                print("Настройка отменена.")
                return False
            
            # Валидация формата ключа
            key_valid, key_error = api_client.check_api_key_format(new_key)
            if not key_valid:
                print(f"Ошибка: {key_error}")
                return False
            
            settings["API_KEY"] = new_key
            print("✓ API ключ сохранён.")
            return True
            
        except KeyboardInterrupt:
            print("\nНастройка отменена.")
            return False

    def _configure_method_and_mode(self):
        """Ctrl+7: выбор метода генерации (browser/api) и режима (standard/multiformat/multiformat_with_refs)."""
        if self._block_if_api_running():
            return
        settings = settings_store.load_settings()
        
        # Шаг 1: Выбор метода генерации
        current_method = settings.get("GENERATION_METHOD", "browser")
        print("\n=== НАСТРОЙКА ГЕНЕРАЦИИ ===")
        print("Выберите метод генерации:")
        print("  1. browser (через браузер, требует координаты)")
        print("  2. api (через Gemini API, быстрее, без координат)")
        print(f"Текущий: {current_method}")
        
        try:
            method_choice = input("Выбор (Enter — не менять): ").strip()
            
            if method_choice == "1":
                settings["GENERATION_METHOD"] = "browser"
            elif method_choice == "2":
                settings["GENERATION_METHOD"] = "api"
                
                # Шаг 2.5: Выбор модели качества и разрешения
                if not self._configure_api_model(settings):
                    print("Отмена настройки.")
                    return
                
                # Шаг 2.6: Проверка и настройка API ключа
                if not self._check_and_configure_api_key(settings):
                    print("Отмена настройки.")
                    return
            elif method_choice == "":
                # Не меняем метод, продолжаем к выбору режима
                pass
            else:
                print("Неверный выбор.")
                return
            
            # Шаг 3: Выбор режима
            site = settings.get("CURRENT_SITE", "aistudio")
            modes = MODES_BY_SITE.get(site, ["standard", "multiformat"])
            current_mode = settings.get("CURRENT_MODE", "standard")
            
            print("\n=== ВЫБОР РЕЖИМА ===")
            print("Выберите режим:")
            for i, m in enumerate(modes, 1):
                mark = " (текущий)" if m == current_mode else ""
                print(f"  {i}. {m}{mark}")
            
            mode_choice = input("Номер (Enter — не менять): ").strip()
            if mode_choice:
                idx = int(mode_choice)
                if 1 <= idx <= len(modes):
                    selected_mode = modes[idx - 1]
                    settings["CURRENT_MODE"] = selected_mode
                else:
                    print("Неверный номер.")
                    return
            
            # Сохранение настроек
            settings_store.save_settings(settings)
            print(f"\n✓ Метод: {settings.get('GENERATION_METHOD')}, Режим: {settings.get('CURRENT_MODE')}")
            
        except ValueError:
            print("Введите число.")
        except KeyboardInterrupt:
            print("\nНастройка отменена.")

    def _show_settings_and_plan(self):
        """Ctrl+5: показать текущие настройки и план (on_show_plan)."""
        if self._block_if_api_running():
            return
        settings = settings_store.load_settings()
        print("-" * 50)
        print("ТЕКУЩИЕ НАСТРОЙКИ (v2)")
        print(f"  Сайт: {settings.get('CURRENT_SITE')}")
        print(f"  Режим: {settings.get('CURRENT_MODE')}")
        
        # Отображение метода генерации и API ключа
        generation_method = settings.get('GENERATION_METHOD', 'browser')
        print(f"  Метод генерации: {generation_method}")
        if generation_method == 'api':
            api_key = settings.get('API_KEY', '').strip()
            if api_key:
                print(f"  API ключ: {api_key[:10]}... (задан)")
            else:
                print(f"  API ключ: не задан")
        
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

    def _block_if_api_running(self) -> bool:
        """Возвращает True, если запущен API-воркер — тогда хоткей нужно игнорировать (пользователь пользуется ПК в фоне)."""
        return process_control.get_current_worker_type() == "api"

    def _wrapped_on_setup_window(self):
        if self._block_if_api_running():
            return
        self.on_setup_window()

    def _wrapped_on_start_generation(self):
        if self._block_if_api_running():
            return
        self.on_start_generation()

    def _wrapped_on_start_api(self):
        if self._block_if_api_running():
            return
        if self.on_start_api is not None:
            self.on_start_api()

    def on_esc_stop_worker(self):
        """Esc: жёсткая остановка только браузерного воркера; при API-режиме Esc не обрабатывается."""
        if self._block_if_api_running():
            return
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
        keyboard.add_hotkey("ctrl+7", self._configure_method_and_mode)
        keyboard.add_hotkey("ctrl+8", self._configure_image_wait_interval)
        keyboard.add_hotkey("ctrl+9", self._configure_aspect_ratios)
        keyboard.add_hotkey("ctrl+shift+v", self._wrapped_on_setup_window)
        keyboard.add_hotkey("ctrl+shift+s", self._wrapped_on_start_generation)
        if self.on_start_api is not None:
            keyboard.add_hotkey("ctrl+shift+a", self._wrapped_on_start_api)
        keyboard.add_hotkey("ctrl+esc", self.kill_console)
        keyboard.add_hotkey("esc", self.on_esc_stop_worker)
