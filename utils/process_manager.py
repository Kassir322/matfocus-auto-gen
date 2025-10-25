"""
Управление процессами автоматизации
"""
import multiprocessing
from multiprocessing import Process, Event
from config.coordinates import COORDINATES, RELATIVE_MOVEMENTS, DELAYS
from utils.window_manager import WindowManager

class ProcessManager:
    def __init__(self):
        self.automation_process = None
        self.stop_event = None
        self.window_manager = WindowManager()
    
    def start_automation(self, settings_manager):
        """Запуск процесса автоматизации"""
        if self.automation_process and self.automation_process.is_alive():
            print("[ГЛАВНЫЙ] Автоматизация уже запущена!")
            return
        
        # Настройка рабочего окна
        print("[ГЛАВНЫЙ] Настройка рабочего окна...")
        if not self.window_manager.setup_automation_window():
            print("[ГЛАВНЫЙ] ⚠️ Не удалось настроить рабочее окно, но продолжаем...")
        
        # Получение настроек
        generation_mode = settings_manager.get('GENERATION_MODE')
        start_card = settings_manager.get('START_FROM_CARD')
        generations_per_card = settings_manager.get('GENERATIONS_PER_CARD')
        check_image_enabled = settings_manager.get('CHECK_IMAGE_GENERATED')
        generation_wait = DELAYS['GENERATION_WAIT']
        cards_to_process = settings_manager.get('CARDS_TO_PROCESS')
        
        print(f"[ГЛАВНЫЙ] Запуск с настройками:")
        print(f"  Режим генерации: {generation_mode}")
        print(f"  Лимит карточек: {cards_to_process}")
        print(f"  Стартовая карточка: {start_card}")
        print(f"  Генераций на карточку: {generations_per_card}")
        print(f"  Проверка изображений: {check_image_enabled}")
        
        # Проверка критичных координат в зависимости от режима
        critical_coords = ['PROMPT_INPUT', 'IMAGE_LOCATION', 'NEW_CHAT_BUTTON', 'CHAT_NAME_INPUT']
        
        if generation_mode == 'multi_format':
            critical_coords.append('FORMAT_SELECTOR')
        
        empty_critical = [name for name in critical_coords if COORDINATES[name] == (0, 0)]
        empty_movements = [name for name, movement in RELATIVE_MOVEMENTS.items() if movement == (0, 0)]

        if empty_critical or empty_movements:
            error_msg = []
            if empty_critical:
                error_msg.append(f"Критичные координаты: {', '.join(empty_critical)}")
            if empty_movements:
                error_msg.append(f"Относительные движения: {', '.join(empty_movements)}")
            print(f"[ГЛАВНЫЙ] ОШИБКА: Не заданы {' и '.join(error_msg)}")
            
            if generation_mode == 'multi_format' and 'FORMAT_SELECTOR' in empty_critical:
                print("   Используйте Ctrl+0 для настройки координаты")
                print("   FORMAT_SELECTOR - выпадающий список выбора формата (справа от промпта)")
            return
        
        # Дополнительные проверки для multi_format режима
        if generation_mode == 'multi_format':
            # Проверка файла промптов
            from core.file_handler import FileHandler
            file_handler = FileHandler(settings_manager)
            pairs_data = file_handler.load_prompts()

            if not pairs_data:
                print("[ГЛАВНЫЙ] ОШИБКА: Нет валидных пар промптов в файле!")
                return

            # Показать статистику
            total_pairs = sum(len(pairs) for pairs in pairs_data.values())
            print(f"[ГЛАВНЫЙ] Найдено пар промптов: {total_pairs}")
            print(f"[ГЛАВНЫЙ] Будет создано изображений: {total_pairs * 2}")
        
        # Запуск процесса
        print("[ГЛАВНЫЙ] Запуск автоматизации...")
        self.stop_event = Event()
        
        # Выбор генератора в зависимости от режима
        if generation_mode == 'multi_format':
            from core.multi_format_generator import MultiFormatGenerator
            generator = MultiFormatGenerator(settings_manager)

            self.automation_process = Process(
                target=generator.automation_worker,
                args=(self.stop_event, start_card, check_image_enabled,
                      generation_wait, cards_to_process)
            )
        else:
            # Стандартный режим (ImageGenerator)
            from core.image_generator import ImageGenerator
            generator = ImageGenerator(settings_manager)

            self.automation_process = Process(
                target=generator.automation_worker,
                args=(self.stop_event, start_card, generations_per_card, 
                      check_image_enabled, generation_wait, cards_to_process)
            )
        
        self.automation_process.start()
        print(f"[ГЛАВНЫЙ] Автоматизация запущена в процессе PID: {self.automation_process.pid}")
    
    def stop_automation(self):
        """Остановка процесса автоматизации"""
        if not self.automation_process or not self.automation_process.is_alive():
            print("[ГЛАВНЫЙ] Автоматизация не запущена!")
            return
        
        print("[ГЛАВНЫЙ] Остановка автоматизации...")
        
        if self.stop_event:
            self.stop_event.set()
        
        self.automation_process.join(timeout=5)
        
        if self.automation_process.is_alive():
            print("[ГЛАВНЫЙ] Принудительное завершение процесса...")
            self.automation_process.terminate()
            self.automation_process.join()
        
        print("[ГЛАВНЫЙ] Автоматизация остановлена")
        
        # Очистка ссылок
        self.automation_process = None
        self.stop_event = None
    
    def setup_window(self):
        """Ручная настройка рабочего окна"""
        print("[ГЛАВНЫЙ] Ручная настройка рабочего окна...")
        if self.window_manager.quick_setup_window():
            print("[ГЛАВНЫЙ] ✅ Рабочее окно настроено успешно!")
            return True
        else:
            print("[ГЛАВНЫЙ] ❌ Не удалось настроить рабочее окно")
            return False