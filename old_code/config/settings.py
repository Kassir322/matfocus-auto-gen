"""
Управление настройками программы
"""
import json
import os
from .coordinates import DELAYS

class SettingsManager:
    def __init__(self):
        self.settings_file = 'data/settings.json'
        
        # Настройки по умолчанию
        self.settings = {
            'PROMPTS_FILE': 'data/all_card_prompts.txt',  # Файл с промптами
            'CARDS_TO_PROCESS': 50,                       # Максимальное количество карточек для обработки (вычисляется автоматически)
            'GENERATIONS_PER_CARD': 3,                    # Количество генераций на карточку
            'START_FROM_CARD': 1,                         # Номер карточки для начала работы
            'END_CARD': 50,                              # До какой карточки обрабатывать
            'SAVE_FOLDER': '',                            # Папка для сохранения
            'LOG_ENABLED': True,                          # Включить подробное логирование
            'CHECK_IMAGE_GENERATED': False,               # Проверять наличие изображения перед сохранением (по умолчанию отключено)
            'IMAGE_CHECK_ATTEMPTS': 3,                    # Количество попыток проверки
            'IMAGE_CHECK_DELAY': 5,                       # Секунд между проверками
            'BACKGROUND_COLOR_TOLERANCE': 30,             # Допуск для определения фонового цвета
            'GENERATION_MODE': 'standard',                # Режим генерации: 'standard', 'multi_format' или 'multi_format_with_refs'
            'GENERATION_WAIT': 20.0,                      # Время ожидания генерации изображения
            'IMAGE_WAIT_TIME': 25.0,                      # Время ожидания изображения при упрощённой проверке
            'FACE_ASPECT_RATIO': '4:3',                  # Соотношение сторон для лицевой стороны (например, "4:3", "16:9", "3:4")
            'BACK_ASPECT_RATIO': '3:2',                  # Соотношение сторон для оборотной стороны (например, "3:2", "16:9", "5:4")
        }
    
    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            # Создаем папку data если её нет
            os.makedirs('data', exist_ok=True)
            
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    
                # Обновляем только те настройки, которые есть в файле
                for key, value in saved_settings.items():
                    if key in self.settings:
                        self.settings[key] = value
                        # Специальная обработка для GENERATION_WAIT - синхронизация с DELAYS
                        if key == 'GENERATION_WAIT':
                            DELAYS['GENERATION_WAIT'] = value
                
                # Пересчитываем CARDS_TO_PROCESS из диапазона start-end
                if 'START_FROM_CARD' in saved_settings and 'END_CARD' in saved_settings:
                    start_card = saved_settings['START_FROM_CARD']
                    end_card = saved_settings['END_CARD']
                    self.settings['CARDS_TO_PROCESS'] = end_card - start_card + 1
                
                print(f"[НАСТРОЙКИ] Загружены из {self.settings_file}")
                print(f"[НАСТРОЙКИ] PROMPTS_FILE: {self.settings.get('PROMPTS_FILE')}")
            else:
                print(f"[НАСТРОЙКИ] Файл {self.settings_file} не найден, используются настройки по умолчанию")
                self.save_settings()
                
        except Exception as e:
            print(f"[ОШИБКА] При загрузке настроек: {e}")
            print("[НАСТРОЙКИ] Используются настройки по умолчанию")
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            os.makedirs('data', exist_ok=True)
            
            settings_to_save = {
                'CARDS_TO_PROCESS': self.settings['CARDS_TO_PROCESS'],
                'START_FROM_CARD': self.settings['START_FROM_CARD'],
                'END_CARD': self.settings['END_CARD'],
                'GENERATIONS_PER_CARD': self.settings['GENERATIONS_PER_CARD'],
                'CHECK_IMAGE_GENERATED': self.settings['CHECK_IMAGE_GENERATED'],
                'BACKGROUND_COLOR_TOLERANCE': self.settings['BACKGROUND_COLOR_TOLERANCE'],
                'GENERATION_MODE': self.settings['GENERATION_MODE'],
                'GENERATION_WAIT': self.settings['GENERATION_WAIT'],
                'IMAGE_WAIT_TIME': self.settings['IMAGE_WAIT_TIME'],
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, indent=2, ensure_ascii=False)
                
            print(f"[НАСТРОЙКИ] Сохранены в {self.settings_file}")
            
        except Exception as e:
            print(f"[ОШИБКА] При сохранении настроек: {e}")
    
    def get(self, key):
        """Получение значения настройки"""
        return self.settings.get(key)
    
    def set(self, key, value):
        """Установка значения настройки"""
        if key in self.settings:
            self.settings[key] = value
            self.save_settings()
            return True
        return False
    
    def configure_start_card(self):
        """Интерактивная настройка стартовой карточки"""
        while True:
            try:
                print("-" * 50)
                print(f"Текущая стартовая карточка: {self.settings['START_FROM_CARD']}")
                print(f"Конечная карточка: {self.settings['END_CARD']}")
                print(f"Диапазон: карточки {self.settings['START_FROM_CARD']}-{self.settings['END_CARD']}")
                start_card = input(f"Новая стартовая карточка (>=1): ").strip()
                
                if not start_card:
                    print("Настройка отменена")
                    break
                
                start_card = int(start_card)
                
                if start_card >= 1:
                    # Проверка, что стартовая карточка не больше конечной
                    end_card = self.settings['END_CARD']
                    if start_card > end_card:
                        print(f"⚠️ Стартовая карточка ({start_card}) больше конечной ({end_card})!")
                        print(f"⚠️ Автоматически увеличиваем конечную карточку до {start_card}")
                        self.set('END_CARD', start_card)
                    
                    self.set('START_FROM_CARD', start_card)
                    
                    # Пересчитываем CARDS_TO_PROCESS
                    cards_count = self.settings['END_CARD'] - start_card + 1
                    self.settings['CARDS_TO_PROCESS'] = cards_count
                    
                    print(f"✓ Стартовая карточка установлена: {start_card}")
                    print(f"✓ Диапазон: карточки {start_card}-{self.settings['END_CARD']} (всего {cards_count} карточек)")
                    break
                else:
                    print("Ошибка: Номер должен быть >= 1")
                    
            except ValueError:
                print("Ошибка: Введите число")
            except KeyboardInterrupt:
                print("\nНастройка отменена")
                break
    
    def configure_cards_limit(self):
        """Устаревший метод - используйте configure_end_card"""
        print("⚠️ Этот метод устарел. Используйте Ctrl+6 для настройки конечной карточки.")
        return
    
    def configure_end_card(self):
        """Интерактивная настройка конечной карточки"""
        while True:
            try:
                print("-" * 50)
                start_card = self.settings['START_FROM_CARD']
                end_card = self.settings['END_CARD']
                cards_count = end_card - start_card + 1
                
                print(f"Стартовая карточка: {start_card}")
                print(f"Текущая конечная карточка: {end_card}")
                print(f"Диапазон: карточки {start_card}-{end_card} (всего {cards_count} карточек)")
                print(f"До какой карточки обрабатывать (>= {start_card}):")
                
                new_end_card = input("> ").strip()
                
                if not new_end_card:
                    print("Настройка отменена")
                    break
                
                new_end_card = int(new_end_card)
                
                if new_end_card >= start_card:
                    self.set('END_CARD', new_end_card)
                    
                    # Пересчитываем CARDS_TO_PROCESS
                    cards_count = new_end_card - start_card + 1
                    self.settings['CARDS_TO_PROCESS'] = cards_count
                    self.save_settings()
                    
                    print(f"✓ Конечная карточка установлена: {new_end_card}")
                    print(f"✓ Диапазон: карточки {start_card}-{new_end_card} (всего {cards_count} карточек)")
                    break
                else:
                    print(f"Ошибка: Конечная карточка должна быть >= {start_card}")
                    
            except ValueError:
                print("Ошибка: Введите число")
            except KeyboardInterrupt:
                print("\nНастройка отменена")
                break
    
    def configure_generations_per_card(self):
        """Интерактивная настройка количества генераций на карточку"""
        if self.settings['GENERATION_MODE'] in ['multi_format', 'multi_format_with_refs']:
            print("⚠️ Недоступно в мультиформатном режиме")
            print("   Количество изображений = количество пар * 2")
            return
            
        while True:
            try:
                print("-" * 50)
                print(f"Текущее количество генераций на карточку: {self.settings['GENERATIONS_PER_CARD']}")
                gens = input("Новое количество генераций на карточку (1-10): ").strip()
                
                if not gens:
                    print("Настройка отменена")
                    break
                
                gens = int(gens)
                
                if 1 <= gens <= 10:
                    self.set('GENERATIONS_PER_CARD', gens)
                    print(f"✓ Количество генераций установлено и сохранено: {gens}")
                    break
                else:
                    print("Ошибка: Количество должно быть от 1 до 10")
                    
            except ValueError:
                print("Ошибка: Введите число")
            except KeyboardInterrupt:
                print("\nНастройка отменена")
                break
    
    def configure_image_wait_time(self):
        """Настройка времени ожидания изображения"""
        try:
            current_value = self.settings['IMAGE_WAIT_TIME']
            print(f"[НАСТРОЙКИ] Текущее время ожидания изображения: {current_value} сек")
            print("Введите новое значение (10-60 секунд):")
            
            new_value = input("> ").strip()
            if not new_value:
                print("Настройка отменена")
                return
            
            new_value = float(new_value)
            if new_value < 10 or new_value > 60:
                print("Ошибка: значение должно быть от 10 до 60 секунд")
                return
            
            self.settings['IMAGE_WAIT_TIME'] = new_value
            self.save_settings()
            print(f"[НАСТРОЙКИ] Время ожидания изображения установлено: {new_value} сек")
            
        except ValueError:
            print("Ошибка: введите число")
        except Exception as e:
            print(f"Ошибка при настройке времени ожидания: {e}")

    def configure_generation_wait(self):
        """Интерактивная настройка времени ожидания генерации"""
        while True:
            try:
                print("-" * 50)
                print(f"Текущее время ожидания генерации: {DELAYS['GENERATION_WAIT']} сек")
                wait_time = input("Новое время ожидания (10-120 сек): ").strip()
                
                if not wait_time:
                    print("Настройка отменена")
                    break
                
                wait_time = float(wait_time)
                
                if 10 <= wait_time <= 120:
                    # Обновляем и в DELAYS и в settings для синхронизации
                    DELAYS['GENERATION_WAIT'] = wait_time
                    self.settings['GENERATION_WAIT'] = wait_time
                    self.save_settings()
                    print(f"✓ Время ожидания установлено и сохранено: {wait_time} сек")
                    break
                else:
                    print("Ошибка: Время должно быть от 10 до 120 секунд")
                    
            except ValueError:
                print("Ошибка: Введите число")
            except KeyboardInterrupt:
                print("\nНастройка отменена")
                break
    
    def toggle_image_check(self):
        """Переключение проверки изображений"""
        current = self.settings['CHECK_IMAGE_GENERATED']
        self.set('CHECK_IMAGE_GENERATED', not current)
        status = "Включена" if self.settings['CHECK_IMAGE_GENERATED'] else "Выключена"
        print(f"✓ Проверка изображений: {status}")
    
    def change_generation_mode(self):
        """Меню выбора режима генерации"""
        current_mode = self.settings['GENERATION_MODE']
        
        # Определение режимов с их описаниями
        modes = {
            '1': {
                'code': 'standard',
                'name': 'Стандартный (множественные генерации)',
                'description': 'Многократные генерации на карточку'
            },
            '2': {
                'code': 'multi_format',
                'name': 'Мультиформатный без референсов',
                'description': 'Пары изображений без использования референсов (соотношения сторон настраиваются)'
            },
            '3': {
                'code': 'multi_format_with_refs',
                'name': 'Мультиформатный с референсами',
                'description': 'Пары изображений с использованием референсов (соотношения сторон настраиваются)'
            }
        }
        
        try:
            # Получаем текущие соотношения сторон для отображения
            face_ratio = self.settings.get('FACE_ASPECT_RATIO', '4:3')
            back_ratio = self.settings.get('BACK_ASPECT_RATIO', '3:2')
            
            print("-" * 60)
            print("МЕНЮ ВЫБОРА РЕЖИМА ГЕНЕРАЦИИ")
            print("-" * 60)
            print(f"Текущие соотношения сторон: лицо {face_ratio}, оборот {back_ratio}")
            print(f"(Настройка: Ctrl+9)")
            print("-" * 60)
            
            # Отображаем текущий режим
            current_marker = ""
            for key, mode in modes.items():
                if mode['code'] == current_mode:
                    current_marker = " ← текущий"
                    break
            
            # Показываем все режимы с примерами промптов
            for key, mode in modes.items():
                marker = current_marker if mode['code'] == current_mode else ""
                print(f"  {key}. {mode['name']}{marker}")
                print(f"     {mode['description']}")
                
                # Примеры промптов для каждого режима
                if mode['code'] == 'standard':
                    print("     Примеры промптов:")
                    print("       Карточка 1 - Промпт 1: ТЕКСТ ПРОМПТА.")
                    print("       Карточка 1 - Промпт 2: ТЕКСТ ПРОМПТА.")
                    print("       Карточка 1 - Промпт 3: ТЕКСТ ПРОМПТА.")
                    print("       Карточка 2 - Промпт 1: ТЕКСТ ПРОМПТА.")
                    print("       Карточка 2 - Промпт 2: ТЕКСТ ПРОМПТА.")
                
                elif mode['code'] == 'multi_format':
                    print("     Примеры промптов:")
                    print("       Карточка 63 лицо Нефть - Промпт 1: ТЕКСТ ПРОМПТА")
                    print("       Карточка 63 оборот Нефть - Промпт 1: ТЕКСТ ПРОМПТА")
                    print("       Карточка 63 лицо Нефть - Промпт 2: ТЕКСТ ПРОМПТА")
                    print("       Карточка 63 оборот Нефть - Промпт 2: ТЕКСТ ПРОМПТА")
                
                elif mode['code'] == 'multi_format_with_refs':
                    print("     Требуются референсы в папке data/images:")
                    print("       - лицо_№_название.png или .jpg")
                    print("       - оборот_№_название.png или .jpg")
                    print("     Формат промптов такой же, как в мультиформатном без референсов:")
                    print("       Карточка 63 лицо Нефть - Промпт 1: ТЕКСТ ПРОМПТА")
                    print("       Карточка 63 оборот Нефть - Промпт 1: ТЕКСТ ПРОМПТА")
                
                print()
            
            print("  0. Отмена")
            print("-" * 60)
            
            choice = input("Выберите режим (1-3): ").strip()
            
            if not choice or choice == '0':
                print("Выбор режима отменён")
                return
            
            if choice not in modes:
                print("Ошибка: Неверный номер режима!")
                return
            
            selected_mode = modes[choice]
            
            if selected_mode['code'] == current_mode:
                print(f"✓ Режим уже установлен: {selected_mode['name']}")
                return
            
            # Устанавливаем новый режим
            self.set('GENERATION_MODE', selected_mode['code'])
            print(f"✓ Режим изменён: {selected_mode['name']}")
            
        except ValueError:
            print("Ошибка: Введите число!")
        except KeyboardInterrupt:
            print("\nВыбор режима отменён")
        except Exception as e:
            print(f"Ошибка при выборе режима: {e}")
    
    def configure_aspect_ratios(self):
        """Настройка соотношений сторон для мультиформатного режима"""
        try:
            print("-" * 60)
            print("НАСТРОЙКА СООТНОШЕНИЙ СТОРОН")
            print("-" * 60)
            
            current_face = self.settings.get('FACE_ASPECT_RATIO', '4:3')
            current_back = self.settings.get('BACK_ASPECT_RATIO', '3:2')
            
            print(f"Текущее соотношение для лицевой стороны: {current_face}")
            print(f"Текущее соотношение для оборотной стороны: {current_back}")
            print()
            print("Формат ввода: X:Y (например, 16:9, 3:4, 5:4)")
            print("Оставьте пустым, чтобы не изменять")
            print()
            
            # Настройка лицевой стороны
            new_face = input(f"Новое соотношение для лицевой стороны [{current_face}]: ").strip()
            if new_face:
                if self._validate_aspect_ratio(new_face):
                    self.set('FACE_ASPECT_RATIO', new_face)
                    print(f"✓ Соотношение для лицевой стороны установлено: {new_face}")
                else:
                    print("❌ Ошибка: неверный формат. Используйте формат X:Y (например, 16:9)")
                    return
            else:
                print(f"Соотношение для лицевой стороны не изменено: {current_face}")
            
            print()
            
            # Настройка оборотной стороны
            new_back = input(f"Новое соотношение для оборотной стороны [{current_back}]: ").strip()
            if new_back:
                if self._validate_aspect_ratio(new_back):
                    self.set('BACK_ASPECT_RATIO', new_back)
                    print(f"✓ Соотношение для оборотной стороны установлено: {new_back}")
                else:
                    print("❌ Ошибка: неверный формат. Используйте формат X:Y (например, 16:9)")
                    return
            else:
                print(f"Соотношение для оборотной стороны не изменено: {current_back}")
            
            print()
            print(f"Текущие настройки:")
            print(f"  Лицевая сторона: {self.settings.get('FACE_ASPECT_RATIO', '4:3')}")
            print(f"  Оборотная сторона: {self.settings.get('BACK_ASPECT_RATIO', '3:2')}")
            
        except KeyboardInterrupt:
            print("\nНастройка отменена")
        except Exception as e:
            print(f"Ошибка при настройке соотношений сторон: {e}")
    
    def _validate_aspect_ratio(self, ratio: str) -> bool:
        """
        Валидация формата соотношения сторон
        
        Args:
            ratio: строка в формате "X:Y"
            
        Returns:
            bool: True если формат корректный
        """
        try:
            if ':' not in ratio:
                return False
            
            parts = ratio.split(':')
            if len(parts) != 2:
                return False
            
            # Проверяем, что обе части - числа
            float(parts[0])
            float(parts[1])
            
            return True
        except (ValueError, AttributeError):
            return False
