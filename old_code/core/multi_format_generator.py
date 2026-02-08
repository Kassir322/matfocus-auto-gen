"""
Мультиформатный генератор изображений для AI Studio
Поддерживает генерацию пар изображений с настраиваемыми соотношениями сторон
"""
import time
import pyautogui
import multiprocessing
import os
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
        """Выбор формата изображения через UI."""
        try:
            self.logger.log_action(f"Выбор формата изображения: {format_ratio}")
            if not self.chat_manager.click_coordinate('ASPECT_RATIO_SELECTOR', "выпадающий список соотношения сторон"):
                return False
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            self.logger.log_action(f"Ввод формата: {format_ratio}")
            pyautogui.write(format_ratio)
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            self.logger.log_action("Подтверждение выбора формата (Enter)")
            pyautogui.press('enter')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            self.logger.log_action(f"Формат {format_ratio} выбран успешно")
            return True
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при выборе формата {format_ratio}: {e}")
            return False
    
    def check_image_generated(self):
        """Упрощённая проверка изображения - просто ждём фиксированное время."""
        try:
            image_wait_time = self.settings_manager.get('IMAGE_WAIT_TIME')
            if image_wait_time is None:
                image_wait_time = 25.0
                self.logger.log_action("IMAGE_WAIT_TIME был None, используется 25.0 сек")
            self.logger.log_action(f"Упрощённая проверка: ожидание {image_wait_time} сек...")
            for i in range(int(image_wait_time)):
                time.sleep(1)
                if i % 5 == 0 and i > 0:
                    self.logger.log_action(f"Прошло {i}/{image_wait_time} сек...")
            self.logger.log_action("Ожидание завершено, предполагаем что изображение готово")
            return True
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при упрощённой проверке: {e}")
            return True
    
    def save_image_as(self, filename):
        """Сохранение изображения через контекстное меню браузера."""
        try:
            self.logger.log_action(f"Начинаем сохранение изображения: {filename}")
            original_clipboard = self.clipboard.get_clipboard_content()
            if not self.clipboard.copy_to_clipboard(filename):
                self.logger.log_action("Не удалось скопировать имя файла в буфер обмена")
                return False
            x, y = COORDINATES['IMAGE_LOCATION']
            pyautogui.rightClick(x, y)
            time.sleep(DELAYS['CONTEXT_MENU_WAIT'])
            rel_x, rel_y = RELATIVE_MOVEMENTS['TO_SAVE_OPTION']
            if rel_x == 0 and rel_y == 0:
                self.clipboard.restore_clipboard(original_clipboard)
                return False
            pyautogui.move(rel_x, rel_y)
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            pyautogui.click()
            time.sleep(DELAYS['SAVE_DIALOG_WAIT'])
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            pyautogui.press('enter')
            time.sleep(DELAYS['AFTER_SAVE'])
            self.clipboard.restore_clipboard(original_clipboard)
            self.logger.log_action(f"Файл успешно сохранён: {filename}")
            return True
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при сохранении файла: {e}")
            try:
                self.clipboard.restore_clipboard(original_clipboard)
            except:
                pass
            return False

    def get_reference_path(self, card_number: int, card_name: str, side: str) -> str:
        """Поиск пути к файлу референса для карточки."""
        try:
            safe_card_name = card_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            ref_dir = os.path.join('data', 'images', side)
            if not os.path.exists(ref_dir):
                self.logger.log_action(f"Папка с референсами не найдена: {ref_dir}")
                return None
            for ext in ['png', 'jpg']:
                ref_filename = f"{side}_{card_number}_{safe_card_name}.{ext}"
                ref_path = os.path.join(ref_dir, ref_filename)
                if os.path.exists(ref_path):
                    self.logger.log_action(f"Найден референс: {ref_path}")
                    return ref_path
            self.logger.log_action(f"Референс не найден для карточки {card_number} ({card_name}), сторона {side}")
            return None
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при поиске референса: {e}")
            return None

    def generate_single_side(self, card_number: int, card_name: str, pair_number: int,
                            side: str, prompt: str,
                            format_ratio: str, stop_event) -> bool:
        """Генерация одной стороны (лицо ИЛИ оборот)."""
        try:
            chat_name = f"Карточка {card_number} - {card_name} - {side} - Промпт {pair_number}"
            safe_card_name = card_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"Карточка_{card_number}_{safe_card_name}_{side}_промпт_{pair_number}_{format_ratio.replace(':', 'x')}.png"
            self.logger.log_action(f"--- Генерация: {chat_name} ---")
            if not self.chat_manager.create_new_chat_only():
                return False
            if stop_event.is_set():
                return False
            if not self.chat_manager.click_coordinate('PROMPT_INPUT', "поле ввода промпта"):
                return False
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            generation_mode = self.settings_manager.get('GENERATION_MODE')
            if generation_mode == 'multi_format_with_refs':
                ref_path = self.get_reference_path(card_number, card_name, side)
                if ref_path:
                    self.logger.log_action(f"Вставка референса: {ref_path}")
                    original_clipboard = self.clipboard.get_clipboard_content()
                    if self.clipboard.copy_image_to_clipboard(ref_path):
                        if self.clipboard.paste_image_from_clipboard():
                            self.logger.log_action("Референс вставлен успешно")
                            time.sleep(DELAYS['BETWEEN_CLICKS'])
                    self.clipboard.restore_clipboard(original_clipboard)
            self.logger.log_action("Ввод промпта через буфер обмена")
            if not self.clipboard.safe_paste_text(prompt):
                return False
            time.sleep(DELAYS['AFTER_PASTE'])
            if not self.chat_manager.rename_current_chat(chat_name):
                return False
            if not self.select_image_format(format_ratio):
                return False
            coord_name = 'PROMPT_INPUT_AFTER_IMAGE' if generation_mode == 'multi_format_with_refs' else 'PROMPT_INPUT'
            description = "возврат к полю ввода промпта после вставки изображения" if generation_mode == 'multi_format_with_refs' else "возврат к полю ввода промпта"
            if not self.chat_manager.click_coordinate(coord_name, description):
                return False
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            self.logger.log_action("Запуск генерации (Ctrl+Enter)")
            pyautogui.hotkey('ctrl', 'enter')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            generation_wait = self.settings_manager.get('GENERATION_WAIT') or 20.0
            check_image_enabled = self.settings_manager.get('CHECK_IMAGE_GENERATED')
            if check_image_enabled is None:
                check_image_enabled = True
            self.logger.log_action(f"Запуск генерации... Ожидание {generation_wait} сек...")
            if check_image_enabled:
                initial_wait = min(5, int(generation_wait) // 2)
                for i in range(initial_wait):
                    if stop_event.is_set():
                        return False
                    time.sleep(1)
                max_attempts = self.settings_manager.get('IMAGE_CHECK_ATTEMPTS') or 3
                check_delay = self.settings_manager.get('IMAGE_CHECK_DELAY') or 5
                for attempt in range(max_attempts):
                    if stop_event.is_set():
                        return False
                    if self.check_image_generated():
                        break
                    if attempt < max_attempts - 1:
                        for i in range(int(check_delay)):
                            if stop_event.is_set():
                                return False
                            time.sleep(1)
            else:
                for i in range(int(generation_wait)):
                    if stop_event.is_set():
                        return False
                    time.sleep(1)
                    if i % 5 == 0 and i > 0:
                        self.logger.log_action(f"Прошло {i}/{generation_wait} сек...")
            if not self.save_image_as(filename):
                return False
            self.logger.log_action(f"Генерация {chat_name} завершена успешно")
            return True
        except Exception as e:
            self.logger.log_action(f"ОШИБКА в генерации {chat_name}: {e}")
            return False

    def generate_pair(self, card_number: int, card_name: str, pair_number: int,
                     prompts_dict: dict, stop_event) -> int:
        """Генерация пары (лицо + оборот)."""
        try:
            face_ratio = self.settings_manager.get('FACE_ASPECT_RATIO')
            back_ratio = self.settings_manager.get('BACK_ASPECT_RATIO')
            success_count = 0
            face_prompt = prompts_dict.get('лицо')
            if face_prompt is not None:
                if self.generate_single_side(card_number, card_name, pair_number, 'лицо', face_prompt, face_ratio, stop_event):
                    success_count += 1
            if stop_event.is_set():
                return success_count
            if success_count > 0:
                time.sleep(DELAYS['BETWEEN_GENERATIONS'])
            back_prompt = prompts_dict.get('оборот')
            if back_prompt is not None:
                if self.generate_single_side(card_number, card_name, pair_number, 'оборот', back_prompt, back_ratio, stop_event):
                    success_count += 1
            expected_count = (1 if face_prompt is not None else 0) + (1 if back_prompt is not None else 0)
            self.logger.log_action(f"Пара {pair_number} завершена: {success_count}/{expected_count} изображений")
            return success_count
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при генерации пары {pair_number}: {e}")
            return 0

    def process_card(self, card_number: int, card_name: str, pairs_list: list,
                    stop_event) -> tuple:
        """Обработка всех пар одной карточки."""
        try:
            processed_pairs = 0
            total_images = 0
            for pair_index, pair_dict in enumerate(pairs_list, 1):
                if stop_event.is_set():
                    break
                images_created = self.generate_pair(card_number, card_name, pair_index, pair_dict, stop_event)
                if images_created > 0:
                    processed_pairs += 1
                    total_images += images_created
                if pair_index < len(pairs_list) and not stop_event.is_set():
                    time.sleep(DELAYS['BETWEEN_GENERATIONS'])
            self.logger.log_action(f"Карточка #{card_number} завершена: {processed_pairs}/{len(pairs_list)} пар, {total_images} изображений")
            return processed_pairs, total_images
        except Exception as e:
            self.logger.log_action(f"ОШИБКА при обработке карточки #{card_number}: {e}")
            return 0, 0

    def automation_worker(self, stop_event, start_card: int,
                         check_image_enabled: bool,
                         generation_wait: float,
                         cards_to_process: int):
        """Главный рабочий процесс (точка входа для Process)."""
        from core.file_handler import FileHandler
        generation_mode = self.settings_manager.get('GENERATION_MODE')
        face_ratio = self.settings_manager.get('FACE_ASPECT_RATIO')
        back_ratio = self.settings_manager.get('BACK_ASPECT_RATIO')
        self.logger.log_action(f"Процесс мультиформатного генератора запущен (PID: {multiprocessing.current_process().pid})")
        self.logger.log_action(f"Настройки: старт={start_card}, лимит={cards_to_process}, проверка={check_image_enabled}")
        file_handler = FileHandler(self.settings_manager)
        cards_to_process_list = file_handler.get_cards_to_process()
        print(f"[ГЕНЕРАТОР] Получен список карточек: {len(cards_to_process_list)}")
        if not cards_to_process_list:
            self.logger.log_action(f"КРИТИЧЕСКАЯ ОШИБКА: Нет карточек для обработки начиная с №{start_card}!")
            return
        if generation_mode == 'multi_format_with_refs':
            missing_refs = []
            for card_number, card_name, pairs_list in cards_to_process_list:
                if not self.get_reference_path(card_number, card_name, 'лицо'):
                    missing_refs.append(f"Карточка {card_number} ({card_name}) - лицо")
                if not self.get_reference_path(card_number, card_name, 'оборот'):
                    missing_refs.append(f"Карточка {card_number} ({card_name}) - оборот")
            if missing_refs:
                self.logger.log_action("НЕ НАЙДЕНЫ РЕФЕРЕНСЫ: " + "; ".join(missing_refs))
        total_pairs = sum(len(pairs_list) for _, _, pairs_list in cards_to_process_list)
        total_images = total_pairs * 2
        processed_cards = 0
        processed_pairs = 0
        total_images_created = 0
        for card_number, card_name, pairs_list in cards_to_process_list:
            if stop_event.is_set():
                break
            pairs_done, images_created = self.process_card(card_number, card_name, pairs_list, stop_event)
            if pairs_done > 0:
                processed_cards += 1
                processed_pairs += pairs_done
                total_images_created += images_created
            if (card_number, pairs_list) != cards_to_process_list[-1] and not stop_event.is_set():
                time.sleep(DELAYS['BETWEEN_CARDS'])
        self.logger.log_action(f"ОТЧЁТ: карточек {processed_cards}/{len(cards_to_process_list)}, пар {processed_pairs}/{total_pairs}, изображений {total_images_created}/{total_images}")
