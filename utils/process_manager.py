"""
Управление процессами автоматизации
"""
import multiprocessing
from multiprocessing import Process, Event
from config.coordinates import COORDINATES, RELATIVE_MOVEMENTS, DELAYS

class ProcessManager:
    def __init__(self):
        self.automation_process = None
        self.stop_event = None
    
    def start_automation(self, settings_manager):
        """Запуск процесса автоматизации"""
        if self.automation_process and self.automation_process.is_alive():
            print("[ГЛАВНЫЙ] Автоматизация уже запущена!")
            return
        
        # Получение настроек
        start_card = settings_manager.get('START_FROM_CARD')
        generations_per_card = settings_manager.get('GENERATIONS_PER_CARD')
        check_image_enabled = settings_manager.get('CHECK_IMAGE_GENERATED')
        generation_wait = DELAYS['GENERATION_WAIT']
        cards_to_process = settings_manager.get('CARDS_TO_PROCESS')
        
        print(f"[ГЛАВНЫЙ] Запуск с настройками:")
        print(f"  Лимит карточек: {cards_to_process}")
        print(f"  Стартовая карточка: {start_card}")
        print(f"  Генераций на карточку: {generations_per_card}")
        print(f"  Проверка изображений: {check_image_enabled}")
        
        # Проверка критичных координат
        critical_coords = ['PROMPT_INPUT', 'IMAGE_LOCATION', 'NEW_CHAT_BUTTON', 'CHAT_NAME_INPUT']
        empty_critical = [name for name in critical_coords if COORDINATES[name] == (0, 0)]
        empty_movements = [name for name, movement in RELATIVE_MOVEMENTS.items() if movement == (0, 0)]

        if empty_critical or empty_movements:
            error_msg = []
            if empty_critical:
                error_msg.append(f"Критичные координаты: {', '.join(empty_critical)}")
            if empty_movements:
                error_msg.append(f"Относительные движения: {', '.join(empty_movements)}")
            print(f"[ГЛАВНЫЙ] ОШИБКА: Не заданы {' и '.join(error_msg)}")
            return
        
        # Запуск процесса
        print("[ГЛАВНЫЙ] Запуск автоматизации...")
        self.stop_event = Event()
        
        # Импортируем ImageGenerator только при необходимости (ленивый импорт)
        from core.image_generator import ImageGenerator
        image_generator = ImageGenerator(settings_manager)
        
        self.automation_process = Process(
            target=image_generator.automation_worker,
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