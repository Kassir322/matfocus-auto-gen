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
        print("  Ctrl+6 - настроить КОНЕЧНУЮ КАРТОЧКУ (до какой)")
        print("  Ctrl+7 - ВЫБРАТЬ РЕЖИМ ГЕНЕРАЦИИ ⭐")
        print("  Ctrl+8 - НАСТРОИТЬ ВРЕМЯ ОЖИДАНИЯ ИЗОБРАЖЕНИЯ ⏰")
        print("  Ctrl+9 - НАСТРОИТЬ СООТНОШЕНИЯ СТОРОН (для мультиформатного режима) 📐")
        print("  Ctrl+Shift+V - НАСТРОИТЬ РАБОЧЕЕ ОКНО 🪟")
        print("  Ctrl+Shift+S - ЗАПУСТИТЬ автоматизацию")
        print("  Ctrl+Shift+Q - ОСТАНОВИТЬ автоматизацию")
        print("  Ctrl+Esc - убить консоль (аналог Ctrl+C)")
        print("  Esc - выход из программы")
        print("-" * 80)
        print(f"Настройки загружены из data/settings.json")
        print("-" * 80)
        print("ИНСТРУКЦИЯ:")
        print("  1. Настройте рабочее окно (Ctrl+Shift+V) 🪟")
        print("  2. Настройте координаты интерфейса (Ctrl+0)")
        print("  3. Настройте параметры (Ctrl+1-4)")
        print("  4. Проверьте настройки (Ctrl+5)")
        print("  5. Запустите автоматизацию (Ctrl+Shift+S)")
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
        start_card = settings_manager.get('START_FROM_CARD')
        end_card = settings_manager.get('END_CARD')
        print(f"  Стартовая карточка: {start_card}")
        print(f"  Конечная карточка: {end_card}")
        print(f"  → Будет обработано карточек: {settings_manager.get('CARDS_TO_PROCESS')}")
        
        # Отображение режима генерации
        generation_mode = settings_manager.get('GENERATION_MODE')
        mode_names = {
            'standard': 'Стандартный (множественные генерации)',
            'multi_format': 'Мультиформатный без референсов',
            'multi_format_with_refs': 'Мультиформатный с референсами'
        }
        
        print(f"  🎯 РЕЖИМ: {mode_names.get(generation_mode, generation_mode)}")
        
        if generation_mode in ['multi_format', 'multi_format_with_refs']:
            face_ratio = settings_manager.get('FACE_ASPECT_RATIO', '4:3')
            back_ratio = settings_manager.get('BACK_ASPECT_RATIO', '3:2')
            print(f"  Соотношение сторон (лицо): {face_ratio}")
            print(f"  Соотношение сторон (оборот): {back_ratio}")
            print(f"  Пар промптов на карточку: зависит от файла")
            print(f"  Изображений на пару: 2 (лицо + оборот)")
            if generation_mode == 'multi_format_with_refs':
                print(f"  ⚠️ Референсы требуются в папке data/images")
        else:
            print(f"  Генераций на карточку: {settings_manager.get('GENERATIONS_PER_CARD')}")
        
        print(f"  Время ожидания генерации: {DELAYS['GENERATION_WAIT']} сек")
        print(f"  Время ожидания изображения: {settings_manager.get('IMAGE_WAIT_TIME')} сек")
        print(f"  Проверка изображений: {'Включена' if settings_manager.get('CHECK_IMAGE_GENERATED') else 'Выключена'}")
        print("-" * 30)
        print("Координаты:")
        missing_coords = [name for name, coord in COORDINATES.items() if coord == (0, 0)]
        
        # Проверка ASPECT_RATIO_SELECTOR для multi_format режимов
        if generation_mode in ['multi_format', 'multi_format_with_refs']:
            if COORDINATES.get('ASPECT_RATIO_SELECTOR', (0, 0)) == (0, 0):
                print("  ❌ ASPECT_RATIO_SELECTOR не задан! Обязателен для этого режима!")
                missing_coords = [name for name in missing_coords if name != 'ASPECT_RATIO_SELECTOR']
        
        # Проверка PROMPT_INPUT_AFTER_IMAGE для режима с референсами
        if generation_mode == 'multi_format_with_refs':
            if COORDINATES.get('PROMPT_INPUT_AFTER_IMAGE', (0, 0)) == (0, 0):
                print("  ❌ PROMPT_INPUT_AFTER_IMAGE не задан! Обязателен для режима с референсами!")
                missing_coords = [name for name in missing_coords if name != 'PROMPT_INPUT_AFTER_IMAGE']
        
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
            
            if generation_mode in ['multi_format', 'multi_format_with_refs']:
                # Для мультиформатного режима считаем пары и изображения
                total_pairs = sum(len(pairs) for card_num, pairs in all_prompts.items() 
                                if card_num >= settings_manager.get('START_FROM_CARD') 
                                and card_num < settings_manager.get('START_FROM_CARD') + actual_cards)
                total_images = total_pairs * 2
                print(f"  Найдено пар промптов: {total_pairs}")
                print(f"  Всего изображений: {total_images}")
                estimated_time = total_images * (DELAYS['GENERATION_WAIT'] + 10) / 60
                print(f"  Примерное время выполнения: {estimated_time:.1f} минут")
                if generation_mode == 'multi_format_with_refs':
                    # Проверяем наличие папок с референсами
                    import os
                    face_dir = os.path.join('data', 'images', 'лицо')
                    back_dir = os.path.join('data', 'images', 'оборот')
                    
                    if not os.path.exists(face_dir) or not os.path.exists(back_dir):
                        print(f"  ⚠️ Папки с референсами не найдены: {face_dir}, {back_dir}")
                    else:
                        print(f"  ✓ Папки с референсами найдены")
            else:
                # Стандартный режим
                total_generations = actual_cards * settings_manager.get('GENERATIONS_PER_CARD')
                print(f"  Всего генераций: {total_generations}")
                estimated_time = total_generations * (DELAYS['GENERATION_WAIT'] + 10) / 60
                print(f"  Примерное время выполнения: {estimated_time:.1f} минут")
        else:
            print(f"  ⚠️ ВНИМАНИЕ: Стартовая карточка {settings_manager.get('START_FROM_CARD')} не найдена в файле!")
        print("-" * 60)