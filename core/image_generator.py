"""
Основная логика генерации изображений
"""
import time
import pyautogui
import multiprocessing
from config.coordinates import COORDINATES, DELAYS, RELATIVE_MOVEMENTS
from utils.clipboard import ClipboardManager
from utils.logger import Logger
from .chat_manager import ChatManager

class ImageGenerator:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.clipboard = ClipboardManager()
        self.logger = Logger()
        self.chat_manager = ChatManager()
    
    def check_image_generated(self):
        """Проверяет, сгенерировалось ли изображение по цвету пикселя"""
        try:
            x, y = COORDINATES['IMAGE_LOCATION']
            pixel_color = pyautogui.pixel(x, y)
            
            background_rgb = (25, 25, 25)
            tolerance = self.settings_manager.get('BACKGROUND_COLOR_TOLERANCE')
            
            r, g, b = pixel_color
            bg_r, bg_g, bg_b = background_rgb
            
            is_background = (abs(r - bg_r) <= tolerance and 
                            abs(g - bg_g) <= tolerance and 
                            abs(b - bg_b) <= tolerance)
            
            self.logger.log_action(f"Цвет пикселя в точке изображения: RGB{pixel_color}")
            self.logger.log_action(f"Фоновый цвет (с допуском {tolerance}): RGB{background_rgb}")
            
            if is_background:
                self.logger.log_action("⚠️ Возможно, изображение не сгенерировалось (фоновый цвет)")
                return False
            else:
                self.logger.log_action("✓ Обнаружено изображение (не фоновый цвет)")
                return True
                
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при проверке цвета пикселя: {e}")
            return True
    
    def save_image_as(self, filename):
        """Сохранение изображения через контекстное меню браузера"""
        try:
            original_clipboard = self.clipboard.get_clipboard_content()
            
            if not self.clipboard.copy_to_clipboard(filename):
                return False
            
            # Наводим на изображение и делаем ПКМ
            x, y = COORDINATES['IMAGE_LOCATION']
            self.logger.log_action(f"Клик ПКМ на изображении: ({x}, {y})")
            pyautogui.rightClick(x, y)
            time.sleep(DELAYS['CONTEXT_MENU_WAIT'])
            
            # Переходим к пункту "Сохранить изображение"
            rel_x, rel_y = RELATIVE_MOVEMENTS['TO_SAVE_OPTION']
            if rel_x == 0 and rel_y == 0:
                self.logger.log_action("ВНИМАНИЕ: Относительное движение TO_SAVE_OPTION не задано!")
                self.clipboard.restore_clipboard(original_clipboard)
                return False
            
            self.logger.log_action(f"Движение к пункту меню: относительно ({rel_x}, {rel_y})")
            pyautogui.move(rel_x, rel_y)
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # Кликаем на "Сохранить изображение"
            pyautogui.click()
            time.sleep(DELAYS['SAVE_DIALOG_WAIT'])
            
            # Вводим имя файла
            self.logger.log_action("Вставка имени файла из буфера")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # Подтверждаем сохранение
            self.logger.log_action("Подтверждение сохранения (Enter)")
            pyautogui.press('enter')
            time.sleep(DELAYS['AFTER_SAVE'])
            
            # Восстанавливаем буфер обмена
            self.clipboard.restore_clipboard(original_clipboard)
            
            self.logger.log_action(f"✓ Файл сохранён: {filename}")
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при сохранении файла: {e}")
            try:
                self.clipboard.restore_clipboard(original_clipboard)
            except:
                pass
            return False

    def generate_single_image(self, prompt, chat_name, filename, check_image_enabled, generation_wait, stop_event):
        """Генерация одного изображения в отдельном чате"""
        try:
            self.logger.log_action(f"--- Генерация: {chat_name} ---")
            
            # 1. Создаем новый чат (без переименования)
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
            
            # 4. Возвращаемся к полю ввода промпта
            if not self.chat_manager.click_coordinate('PROMPT_INPUT', "возврат к полю ввода промпта"):
                return False
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            # 5. Запускаем генерацию
            self.logger.log_action("Запуск генерации (Ctrl+Enter)")
            pyautogui.hotkey('ctrl', 'enter')
            time.sleep(DELAYS['BETWEEN_CLICKS'])
            
            self.logger.log_action(f"Ожидание генерации {generation_wait} сек...")
            
            for i in range(int(generation_wait)):
                if stop_event.is_set():
                    return False
                time.sleep(1)
            
            if check_image_enabled:
                try:
                    for check_attempt in range(self.settings_manager.get('IMAGE_CHECK_ATTEMPTS')):
                        if self.check_image_generated():
                            break
                        
                        if check_attempt < self.settings_manager.get('IMAGE_CHECK_ATTEMPTS') - 1:
                            self.logger.log_action(f"Ждем еще {self.settings_manager.get('IMAGE_CHECK_DELAY')} сек и проверяем снова...")
                            time.sleep(self.settings_manager.get('IMAGE_CHECK_DELAY'))
                        else:
                            self.logger.log_action("❌ Изображение не сгенерировалось, но продолжаем сохранение")
                except Exception as e:
                    self.logger.log_action(f"⚠️ Ошибка проверки изображения (продолжаем): {e}")
            
            if not self.save_image_as(filename):
                return False
            
            self.logger.log_action(f"✓ Генерация {chat_name} завершена успешно")
            return True
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА в генерации {chat_name}: {e}")
            return False
    
    def process_card(self, card_number, card_name, prompts_for_card, generations_per_card, check_image_enabled, generation_wait, stop_event):
        """Обработка одной карточки - N генераций с разными промптами в отдельных чатах"""
        try:
            self.logger.log_action(f"======= ОБРАБОТКА КАРТОЧКИ #{card_number} ({card_name}) =======")
            
            success_count = 0
            
            for gen_num in range(1, generations_per_card + 1):
                if stop_event.is_set():
                    break
                
                prompt_index = (gen_num - 1) % len(prompts_for_card)
                prompt = prompts_for_card[prompt_index]
                
                if not prompt:
                    self.logger.log_action(f"⚠️ Промпт {prompt_index + 1} для карточки {card_number} ({card_name}) пустой, пропускаем генерацию {gen_num}")
                    continue
                
                # Используем название карточки для имени чата и файла
                chat_name = f"{card_name} - генерация {gen_num}"
                # Очищаем название от спецсимволов для имени файла
                safe_card_name = card_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                filename = f"{safe_card_name}_генерация_{gen_num}.png"
                
                self.logger.log_action(f"Используем промпт {prompt_index + 1}: {prompt[:100]}...")
                
                success = self.generate_single_image(prompt, chat_name, filename, check_image_enabled, generation_wait, stop_event)
                if success:
                    success_count += 1
                
                # Создаем новый чат для следующей генерации (кроме последней)
                if gen_num < generations_per_card and not stop_event.is_set():
                    self.logger.log_action("Подготовка к следующей генерации...")
                    time.sleep(DELAYS['BETWEEN_GENERATIONS'])
            
            self.logger.log_action(f"✓ Карточка #{card_number} завершена: {success_count}/{generations_per_card} генераций")
            return success_count
            
        except Exception as e:
            self.logger.log_action(f"✗ ОШИБКА при обработке карточки #{card_number}: {e}")
            return 0
    
    def automation_worker(self, stop_event, start_card, generations_per_card, check_image_enabled, generation_wait, cards_to_process):
        """Рабочий процесс автоматизации"""
        # Ленивый импорт для избежания циклических зависимостей
        from core.file_handler import FileHandler
        
        self.logger.log_action(f"Процесс запущен (PID: {multiprocessing.current_process().pid})")
        self.logger.log_action(f"Настройки: старт={start_card}, генераций={generations_per_card}, лимит={cards_to_process}, проверка={check_image_enabled}")
        
        file_handler = FileHandler(self.settings_manager)
        cards_to_process_list = file_handler.get_cards_to_process()
        
        if not cards_to_process_list:
            self.logger.log_action(f"КРИТИЧЕСКАЯ ОШИБКА: Нет карточек для обработки начиная с №{start_card}!")
            return
        
        total_generations = len(cards_to_process_list) * generations_per_card
        self.logger.log_action(f"Начинаем с карточки #{start_card}")
        self.logger.log_action(f"Будет обработано {len(cards_to_process_list)} карточек ({total_generations} генераций)")
        
        processed_cards = 0
        total_generations_done = 0
        
        for card_number, card_name, prompts_for_card in cards_to_process_list:
            if stop_event.is_set():
                self.logger.log_action("Получен сигнал остановки")
                break
            
            generations_done = self.process_card(card_number, card_name, prompts_for_card, generations_per_card, check_image_enabled, generation_wait, stop_event)
            if generations_done > 0:
                processed_cards += 1
                total_generations_done += generations_done
            
            if (card_number, card_name, prompts_for_card) != cards_to_process_list[-1] and not stop_event.is_set():
                time.sleep(DELAYS['BETWEEN_CARDS'])
        
        self.logger.log_action(f"========== ОТЧЁТ ==========")
        self.logger.log_action(f"Обработано карточек: {processed_cards}/{len(cards_to_process_list)}")
        self.logger.log_action(f"Выполнено генераций: {total_generations_done}/{total_generations}")
        self.logger.log_action(f"===========================")