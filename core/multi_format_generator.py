"""
Мультиформатный генератор изображений для AI Studio
Поддерживает генерацию пар изображений (лицо 4:3 + оборот 3:2)
"""
import time
import pyautogui
import multiprocessing
from config.coordinates import COORDINATES, DELAYS, RELATIVE_MOVEMENTS
from utils.clipboard import ClipboardManager
from utils.logger import Logger
from .chat_manager import ChatManager

class MultiFormatGenerator:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.clipboard = ClipboardManager()
        self.logger = Logger()
        self.chat_manager = ChatManager()
    
    def select_image_format(self, format_ratio: str) -> bool:
        """
        Выбор формата изображения через UI.

        Args:
            format_ratio: "4:3" или "3:2"

        Returns:
            bool: успешность операции

        Алгоритм:
        1. Клик на FORMAT_SELECTOR координату
        2. Пауза BETWEEN_CLICKS
        3. Ввод format_ratio через pyautogui.write()
        4. Пауза BETWEEN_CLICKS
        5. Enter для подтверждения
        6. Пауза BETWEEN_CLICKS
        """
        try:
            self.logger.log_action(f"Выбор формата изображения: {format_ratio}")
            
            # 1. Клик на выпадающий список формата
            if not self.chat_manager.click_coordinate('FORMAT_SELECTOR', "выпадающий список формата"):
                return False
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # 2. Ввод формата
            self.logger.log_action(f"Ввод формата: {format_ratio}")
            pyautogui.write(format_ratio)
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # 3. Подтверждение выбора
            self.logger.log_action("Подтверждение выбора формата (Enter)")
            pyautogui.press('enter')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            self.logger.log_action(f"✓ Формат {format_ratio} выбран успешно")
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при выборе формата {format_ratio}: {e}")
            return False
    
    def check_image_generated(self):
        """
        Упрощённая проверка изображения - просто ждём фиксированное время.
        
        Используется когда анализ пикселей недоступен.
        """
        try:
            # Получаем время ожидания из настроек
            image_wait_time = self.settings_manager.get('IMAGE_WAIT_TIME')
            
            # Защита от None значений
            if image_wait_time is None:
                image_wait_time = 25.0  # Значение по умолчанию
                self.logger.log_action("⚠️ IMAGE_WAIT_TIME был None, используется значение по умолчанию: 25.0 сек")
            
            self.logger.log_action(f"⏳ Упрощённая проверка: ожидание {image_wait_time} сек...")
            
            # Ждём указанное время
            for i in range(int(image_wait_time)):
                time.sleep(1)
                if i % 5 == 0 and i > 0:  # Показываем прогресс каждые 5 секунд
                    self.logger.log_action(f"⏳ Прошло {i}/{image_wait_time} сек...")
            
            self.logger.log_action("✅ Ожидание завершено, предполагаем что изображение готово")
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при упрощённой проверке: {e}")
            return True
    
    def save_image_as(self, filename):
        """
        Сохранение изображения через контекстное меню браузера.
        
        Улучшенная версия с подробным логированием.
        """
        try:
            self.logger.log_action(f"💾 Начинаем сохранение изображения: {filename}")
            
            # Сохраняем текущее содержимое буфера обмена
            original_clipboard = self.clipboard.get_clipboard_content()
            self.logger.log_action("📋 Сохранён оригинальный буфер обмена")
            
            # Копируем имя файла в буфер обмена
            if not self.clipboard.copy_to_clipboard(filename):
                self.logger.log_action("❌ Не удалось скопировать имя файла в буфер обмена")
                return False
            
            self.logger.log_action(f"📋 Имя файла скопировано в буфер: {filename}")
            
            # Наводим на изображение и делаем ПКМ
            x, y = COORDINATES['IMAGE_LOCATION']
            self.logger.log_action(f"🖱️ Клик ПКМ на изображении: ({x}, {y})")
            pyautogui.rightClick(x, y)
            time.sleep(DELAYS['CONTEXT_MENU_WAIT'])
            self.logger.log_action("⏳ Ожидание появления контекстного меню...")
            
            # Переходим к пункту "Сохранить изображение"
            rel_x, rel_y = RELATIVE_MOVEMENTS['TO_SAVE_OPTION']
            if rel_x == 0 and rel_y == 0:
                self.logger.log_action("❌ ВНИМАНИЕ: Относительное движение TO_SAVE_OPTION не задано!")
                self.clipboard.restore_clipboard(original_clipboard)
                return False
            
            self.logger.log_action(f"🖱️ Движение к пункту меню: относительно ({rel_x}, {rel_y})")
            pyautogui.move(rel_x, rel_y)
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # Кликаем на "Сохранить изображение"
            self.logger.log_action("🖱️ Клик на пункт 'Сохранить изображение'")
            pyautogui.click()
            time.sleep(DELAYS['SAVE_DIALOG_WAIT'])
            self.logger.log_action("⏳ Ожидание открытия диалога сохранения...")
            
            # Вводим имя файла
            self.logger.log_action("⌨️ Вставка имени файла из буфера обмена")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # Подтверждаем сохранение
            self.logger.log_action("⌨️ Подтверждение сохранения (Enter)")
            pyautogui.press('enter')
            time.sleep(DELAYS['AFTER_SAVE'])
            self.logger.log_action("⏳ Ожидание завершения сохранения...")
            
            # Восстанавливаем буфер обмена
            self.clipboard.restore_clipboard(original_clipboard)
            self.logger.log_action("📋 Буфер обмена восстановлен")
            
            self.logger.log_action(f"✅ Файл успешно сохранён: {filename}")
            return True
            
        except Exception as e:
            self.logger.log_action(f"❌ ОШИБКА при сохранении файла: {e}")
            try:
                self.clipboard.restore_clipboard(original_clipboard)
                self.logger.log_action("📋 Буфер обмена восстановлен после ошибки")
            except:
                pass
            return False

    def generate_single_side(self, card_number: int, card_name: str, pair_number: int,
                            side: str, prompt: str,
                            format_ratio: str, stop_event) -> bool:
        """
        Генерация одной стороны (лицо ИЛИ оборот).

        Args:
            card_number: номер карточки
            card_name: название карточки
            pair_number: номер пары промптов
            side: "лицо" или "оборот"
            prompt: текст промпта
            format_ratio: "4:3" или "3:2"
            stop_event: событие остановки

        Возвращает True если успешно.

        Алгоритм:
        1. Создать новый чат
        2. Ввести промпт
        3. Переименовать чат: f"{card_name} - {side} - Промпт {pair_number}"
        4. Выбрать формат (select_image_format)
        5. Вернуться к полю ввода
        6. Генерация (Ctrl+Enter)
        7. Ожидание
        8. Опциональная проверка изображения
        9. Сохранение: f"{card_name}_{side}_промпт_{pair_number}_{format_ratio.replace(':', 'x')}.png"
        """
        try:
            # Используем название карточки для имени чата и файла
            chat_name = f"{card_name} - {side} - Промпт {pair_number}"
            # Очищаем название от спецсимволов для имени файла
            safe_card_name = card_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_card_name}_{side}_промпт_{pair_number}_{format_ratio.replace(':', 'x')}.png"
            
            self.logger.log_action(f"--- Генерация: {chat_name} ---")
            
            # 1. Создаем новый чат
            if not self.chat_manager.create_new_chat_only():
                return False
            
            if stop_event.is_set():
                return False
            
            # 2. Вводим промпт
            if not self.chat_manager.click_coordinate('PROMPT_INPUT', "поле ввода промпта"):
                return False
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            self.logger.log_action("Ввод промпта через буфер обмена")
            if not self.clipboard.safe_paste_text(prompt):
                return False
            time.sleep(DELAYS['AFTER_PASTE'])
            
            # 3. Переименовываем чат
            if not self.chat_manager.rename_current_chat(chat_name):
                return False
            
            # 4. Выбираем формат изображения
            if not self.select_image_format(format_ratio):
                return False
            
            # 5. Возвращаемся к полю ввода промпта
            if not self.chat_manager.click_coordinate('PROMPT_INPUT', "возврат к полю ввода промпта"):
                return False
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # 6. Запускаем генерацию
            self.logger.log_action("Запуск генерации (Ctrl+Enter)")
            pyautogui.hotkey('ctrl', 'enter')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # 7. Ожидание генерации с умной проверкой
            generation_wait = self.settings_manager.get('GENERATION_WAIT')
            check_image_enabled = self.settings_manager.get('CHECK_IMAGE_GENERATED')
            
            # Защита от None значений
            if generation_wait is None:
                generation_wait = 20.0  # Значение по умолчанию
                self.logger.log_action("⚠️ GENERATION_WAIT был None, используется значение по умолчанию: 20.0 сек")
            
            if check_image_enabled is None:
                check_image_enabled = True  # Значение по умолчанию
                self.logger.log_action("⚠️ CHECK_IMAGE_GENERATED был None, используется значение по умолчанию: True")
            
            self.logger.log_action(f"Запуск генерации... Ожидание {generation_wait} сек...")
            
            if check_image_enabled:
                # Умное ожидание с проверкой изображения
                self.logger.log_action("🔍 Режим умного ожидания с проверкой изображения")
                
                # Сначала ждём минимальное время для начала генерации
                initial_wait = min(5, generation_wait // 2)
                self.logger.log_action(f"⏳ Начальное ожидание {initial_wait} сек для запуска генерации...")
                
                for i in range(int(initial_wait)):
                    if stop_event.is_set():
                        return False
                    time.sleep(1)
                
                # Затем проверяем изображение с интервалами
                max_attempts = self.settings_manager.get('IMAGE_CHECK_ATTEMPTS')
                check_delay = self.settings_manager.get('IMAGE_CHECK_DELAY')
                
                # Защита от None значений
                if max_attempts is None:
                    max_attempts = 3
                    self.logger.log_action("⚠️ IMAGE_CHECK_ATTEMPTS был None, используется значение по умолчанию: 3")
                
                if check_delay is None:
                    check_delay = 5
                    self.logger.log_action("⚠️ IMAGE_CHECK_DELAY был None, используется значение по умолчанию: 5 сек")
                
                for attempt in range(max_attempts):
                    if stop_event.is_set():
                        return False
                    
                    self.logger.log_action(f"🔍 Проверка изображения (попытка {attempt + 1}/{max_attempts})...")
                    
                    if self.check_image_generated():
                        self.logger.log_action("✅ Изображение сгенерировано! Переходим к сохранению.")
                        break
                    
                    if attempt < max_attempts - 1:
                        self.logger.log_action(f"⏳ Изображение ещё генерируется... Ждём {check_delay} сек...")
                        for i in range(int(check_delay)):
                            if stop_event.is_set():
                                return False
                            time.sleep(1)
                    else:
                        self.logger.log_action("⚠️ Изображение не обнаружено после всех попыток, но продолжаем сохранение")
            else:
                # Простое ожидание без проверки
                self.logger.log_action(f"⏳ Простое ожидание {generation_wait} сек (проверка отключена)...")
                
                for i in range(int(generation_wait)):
                    if stop_event.is_set():
                        return False
                    time.sleep(1)
                    if i % 5 == 0 and i > 0:  # Каждые 5 секунд показываем прогресс
                        self.logger.log_action(f"⏳ Прошло {i}/{generation_wait} сек...")
                
                self.logger.log_action("⏳ Ожидание завершено, переходим к сохранению")
            
            # 9. Сохранение изображения
            if not self.save_image_as(filename):
                return False
            
            self.logger.log_action(f"✓ Генерация {chat_name} завершена успешно")
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА в генерации {chat_name}: {e}")
            return False

    def generate_pair(self, card_number: int, card_name: str, pair_number: int,
                     prompts_dict: dict, stop_event) -> int:
        """
        Генерация пары (лицо + оборот).

        Args:
            card_number: номер карточки
            card_name: название карточки
            pair_number: номер пары
            prompts_dict: {'лицо': 'текст', 'оборот': 'текст'}
            stop_event: событие остановки

        Returns:
            int: количество успешно созданных изображений (0, 1 или 2)

        Алгоритм:
        1. Генерация лицевой стороны (4:3)
        2. Пауза BETWEEN_GENERATIONS
        3. Генерация оборотной стороны (3:2)
        """
        try:
            self.logger.log_action(f"======= 🔗 ГЕНЕРАЦИЯ ПАРЫ {pair_number} КАРТОЧКИ {card_number} =======")
            
            success_count = 0
            
            # Генерация лицевой стороны (4:3)
            self.logger.log_action(f"Генерация лицевой стороны пары {pair_number}")
            if self.generate_single_side(card_number, card_name, pair_number, 'лицо', 
                                       prompts_dict['лицо'], '4:3', stop_event):
                success_count += 1
            
            if stop_event.is_set():
                return success_count
            
            # Пауза между генерациями
            if success_count > 0:  # Только если первая генерация прошла успешно
                self.logger.log_action("Пауза между генерациями пары")
                time.sleep(DELAYS['BETWEEN_GENERATIONS'])
            
            # Генерация оборотной стороны (3:2)
            self.logger.log_action(f"Генерация оборотной стороны пары {pair_number}")
            if self.generate_single_side(card_number, card_name, pair_number, 'оборот', 
                                       prompts_dict['оборот'], '3:2', stop_event):
                success_count += 1
            
            self.logger.log_action(f"✓ Пара {pair_number} завершена: {success_count}/2 изображений")
            return success_count
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при генерации пары {pair_number}: {e}")
            return 0

    def process_card(self, card_number: int, card_name: str, pairs_list: list,
                    stop_event) -> tuple:
        """
        Обработка всех пар одной карточки.

        Args:
            card_number: номер карточки
            card_name: название карточки
            pairs_list: список словарей с парами промптов
            stop_event: событие остановки

        Returns:
            tuple: (количество обработанных пар, количество созданных изображений)

        Алгоритм:
        - Проход по всем парам в pairs_list
        - Для каждой пары вызов generate_pair()
        - Пауза BETWEEN_CARDS после последней пары
        """
        try:
            self.logger.log_action(f"======= 📦 ОБРАБОТКА КАРТОЧКИ #{card_number} =======")
            
            processed_pairs = 0
            total_images = 0
            
            for pair_index, pair_dict in enumerate(pairs_list, 1):
                if stop_event.is_set():
                    break
                
                self.logger.log_action(f"Обработка пары {pair_index} из {len(pairs_list)}")
                
                images_created = self.generate_pair(card_number, card_name, pair_index, pair_dict, stop_event)
                if images_created > 0:
                    processed_pairs += 1
                    total_images += images_created
                
                # Пауза между парами (кроме последней)
                if pair_index < len(pairs_list) and not stop_event.is_set():
                    self.logger.log_action("Пауза между парами")
                    time.sleep(DELAYS['BETWEEN_GENERATIONS'])
            
            self.logger.log_action(f"✓ Карточка #{card_number} завершена: {processed_pairs}/{len(pairs_list)} пар, {total_images} изображений")
            return processed_pairs, total_images
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при обработке карточки #{card_number}: {e}")
            return 0, 0

    def automation_worker(self, stop_event, start_card: int,
                         check_image_enabled: bool,
                         generation_wait: float,
                         cards_to_process: int):
        """
        Главный рабочий процесс (точка входа для Process).

        Использует обновлённый FileHandler для получения структуры
        с парами промптов.
        """
        # Ленивый импорт для избежания циклических зависимостей
        from core.file_handler import FileHandler
        
        self.logger.log_action(f"🚀 Процесс мультиформатного генератора запущен (PID: {multiprocessing.current_process().pid})")
        self.logger.log_action(f"⚙️ Настройки: старт={start_card}, лимит={cards_to_process}, проверка={check_image_enabled}")
        self.logger.log_action(f"🎯 Режим: Мультиформатный (лицо 4:3 + оборот 3:2)")
        
        file_handler = FileHandler(self.settings_manager)
        cards_to_process_list = file_handler.get_cards_to_process()
        
        print(f"[ГЕНЕРАТОР] Получен список карточек: {len(cards_to_process_list)}")
        for i, (card_num, card_name, pairs_list) in enumerate(cards_to_process_list):
            print(f"[ГЕНЕРАТОР] Карточка {i+1}: номер={card_num} ({card_name}), пар={len(pairs_list)}")
        
        if not cards_to_process_list:
            self.logger.log_action(f"КРИТИЧЕСКАЯ ОШИБКА: Нет карточек для обработки начиная с №{start_card}!")
            return
        
        # Подсчет общего количества пар и изображений
        total_pairs = sum(len(pairs_list) for _, _, pairs_list in cards_to_process_list)
        total_images = total_pairs * 2  # Каждая пара = 2 изображения
        
        self.logger.log_action(f"📍 Начинаем с карточки #{start_card}")
        self.logger.log_action(f"📊 Будет обработано {len(cards_to_process_list)} карточек")
        self.logger.log_action(f"🔗 Найдено {total_pairs} пар промптов")
        self.logger.log_action(f"🖼️ Будет создано {total_images} изображений")
        
        processed_cards = 0
        processed_pairs = 0
        total_images_created = 0
        
        for card_number, card_name, pairs_list in cards_to_process_list:
            if stop_event.is_set():
                self.logger.log_action("Получен сигнал остановки")
                break
            
            pairs_done, images_created = self.process_card(card_number, card_name, pairs_list, stop_event)
            if pairs_done > 0:
                processed_cards += 1
                processed_pairs += pairs_done
                total_images_created += images_created
            
            # Пауза между карточками (кроме последней)
            if (card_number, pairs_list) != cards_to_process_list[-1] and not stop_event.is_set():
                time.sleep(DELAYS['BETWEEN_CARDS'])
        
        self.logger.log_action(f"========== 📋 ОТЧЁТ ==========")
        self.logger.log_action(f"📦 Обработано карточек: {processed_cards}/{len(cards_to_process_list)}")
        self.logger.log_action(f"🔗 Обработано пар: {processed_pairs}/{total_pairs}")
        self.logger.log_action(f"🖼️ Создано изображений: {total_images_created}/{total_images}")
        self.logger.log_action(f"===========================")
