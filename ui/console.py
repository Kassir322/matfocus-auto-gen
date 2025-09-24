"""
Консольный интерфейс программы
"""
from config.coordinates import COORDINATES, RELATIVE_MOVEMENTS, DELAYS

class ConsoleInterface:
    def show_welcome_screen(self):
        """Отображение приветственного экрана"""
        print("=" * 80)
        print("АВТОМАТИЗАЦИЯ AI STUDIO - ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ (Windows)")
        print("=" * 80)
    
    def show_instructions(self):
        """Отображение инструкций"""
        print("Горячие клавиши:")
        print("  Ctrl+Shift+P - получить координаты курсора")
        print("  Ctrl+0 - МЕНЮ НАСТРОЙКИ КООРДИНАТ")
        print("  Ctrl+1 - настроить СТАРТОВУЮ КАРТОЧКУ")
        print("  Ctrl+2 - настроить КОЛ-ВО ГЕНЕРАЦИЙ на карточку")
        print("  Ctrl+3 - настроить ВРЕМЯ ОЖИДАНИЯ генерации")
        print("  Ctrl+4 - переключить ПРОВЕРКУ ИЗОБРАЖЕНИЙ")
        print("  Ctrl+5 - показать ТЕКУЩИЕ НАСТРОЙКИ")
        print("  Ctrl+6 - настроить ЛИМИТ КАРТОЧЕК")
        print("  Ctrl+Shift+S - ЗАПУСТИТЬ автоматизацию")
        print("  Ctrl+Shift+Q - ОСТАНОВИТЬ автоматизацию")
        print("  Esc - выход из программы")
        print("-" * 80)
        print(f"Настройки загружены из data/settings.json")
        print("-" * 80)
        print("ИНСТРУКЦИЯ:")
        print("  1. Настройте координаты интерфейса (Ctrl+0)")
        print("  2. Настройте параметры (Ctrl+1-4)")
        print("  3. Проверьте настройки (Ctrl+5)")
        print("  4. Запустите автоматизацию (Ctrl+Shift+S)")
        print("=" * 80)
    
    def show_current_settings(self, settings_manager):
        """Показать текущие настройки"""
        # Ленивый импорт для избежания циклических зависимостей
        from core.file_handler import FileHandler
        
        file_handler = FileHandler(settings_manager)
        all_prompts = file_handler.load_prompts()
        available_cards = sorted(all_prompts.keys()) if all_prompts else []
        
        print("-" * 60)
        print("ТЕКУЩИЕ НАСТРОЙКИ (сохранены в data/settings.json):")
        print(f"  Лимит карточек: {settings_manager.get('CARDS_TO_PROCESS')}")
        print(f"  Стартовая карточка: {settings_manager.get('START_FROM_CARD')}")
        print(f"  Генераций на карточку: {settings_manager.get('GENERATIONS_PER_CARD')}")
        print(f"  Время ожидания генерации: {DELAYS['GENERATION_WAIT']} сек")
        print(f"  Проверка изображений: {'Включена' if settings_manager.get('CHECK_IMAGE_GENERATED') else 'Выключена'}")
        print("-" * 30)
        print("Координаты:")
        missing_coords = [name for name, coord in COORDINATES.items() if coord == (0, 0)]
        if missing_coords:
            print(f"  ⚠️ Не заданы: {', '.join(missing_coords)}")
        else:
            print("  ✓ Все координаты заданы")
        print("  ✓ Генерация: Ctrl+Enter (координаты кнопки не нужны)")
        print("-" * 30)
        print("Информация о файле промптов:")
        print(f"  Доступные карточки: {len(available_cards)} шт.")
        if available_cards:
            print(f"  Диапазон карточек: {min(available_cards)} - {max(available_cards)}")
            print(f"  Первые карточки: {available_cards[:5]}")
        print("-" * 30)
        print("Расчетные значения:")
        if available_cards and settings_manager.get('START_FROM_CARD') in available_cards:
            cards_from_start = len([c for c in available_cards if c >= settings_manager.get('START_FROM_CARD')])
            actual_cards = min(cards_from_start, settings_manager.get('CARDS_TO_PROCESS'))
            print(f"  Будет обработано карточек: {actual_cards}")
            print(f"  Всего генераций: {actual_cards * settings_manager.get('GENERATIONS_PER_CARD')}")
            estimated_time = actual_cards * settings_manager.get('GENERATIONS_PER_CARD') * (DELAYS['GENERATION_WAIT'] + 10) / 60
            print(f"  Примерное время выполнения: {estimated_time:.1f} минут")
        else:
            print(f"  ⚠️ ВНИМАНИЕ: Стартовая карточка {settings_manager.get('START_FROM_CARD')} не найдена в файле!")
        print("-" * 60)