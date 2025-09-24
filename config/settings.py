"""
Управление настройками программы
"""
import json
import os
from .coordinates import DELAYS

class SettingsManager:
    def __init__(self, pillow_available=True):
        self.settings_file = 'data/settings.json'
        
        # Настройки по умолчанию
        self.settings = {
            'PROMPTS_FILE': 'data/all_card_prompts.txt',  # Файл с промптами
            'CARDS_TO_PROCESS': 50,                       # Максимальное количество карточек для обработки
            'GENERATIONS_PER_CARD': 3,                    # Количество генераций на карточку
            'START_FROM_CARD': 1,                         # Номер карточки для начала работы
            'SAVE_FOLDER': '',                            # Папка для сохранения
            'LOG_ENABLED': True,                          # Включить подробное логирование
            'CHECK_IMAGE_GENERATED': pillow_available,    # Проверять наличие изображения перед сохранением
            'IMAGE_CHECK_ATTEMPTS': 3,                    # Количество попыток проверки
            'IMAGE_CHECK_DELAY': 5,                       # Секунд между проверками
            'BACKGROUND_COLOR_TOLERANCE': 30,             # Допуск для определения фонового цвета
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
                    elif key == 'GENERATION_WAIT':
                        DELAYS['GENERATION_WAIT'] = value
                        
                print(f"[НАСТРОЙКИ] Загружены из {self.settings_file}")
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
                'GENERATIONS_PER_CARD': self.settings['GENERATIONS_PER_CARD'],
                'CHECK_IMAGE_GENERATED': self.settings['CHECK_IMAGE_GENERATED'],
                'BACKGROUND_COLOR_TOLERANCE': self.settings['BACKGROUND_COLOR_TOLERANCE'],
                'GENERATION_WAIT': DELAYS['GENERATION_WAIT'],
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
                start_card = input(f"Новая стартовая карточка (1-{self.settings['CARDS_TO_PROCESS']}): ").strip()
                
                if not start_card:
                    print("Настройка отменена")
                    break
                
                start_card = int(start_card)
                
                if 1 <= start_card <= self.settings['CARDS_TO_PROCESS']:
                    self.set('START_FROM_CARD', start_card)
                    print(f"✓ Стартовая карточка установлена и сохранена: {start_card}")
                    break
                else:
                    print(f"Ошибка: Номер должен быть от 1 до {self.settings['CARDS_TO_PROCESS']}")
                    
            except ValueError:
                print("Ошибка: Введите число")
            except KeyboardInterrupt:
                print("\nНастройка отменена")
                break
    
    def configure_cards_limit(self):
        """Интерактивная настройка лимита карточек"""
        while True:
            try:
                print("-" * 50)
                print(f"Текущий лимит карточек: {self.settings['CARDS_TO_PROCESS']}")
                cards_limit = input("Новый лимит карточек (1-1000): ").strip()
                
                if not cards_limit:
                    print("Настройка отменена")
                    break
                
                cards_limit = int(cards_limit)
                
                if 1 <= cards_limit <= 1000:
                    self.set('CARDS_TO_PROCESS', cards_limit)
                    
                    # Проверяем, что стартовая карточка не больше лимита
                    if self.settings['START_FROM_CARD'] > cards_limit:
                        self.set('START_FROM_CARD', 1)
                        print(f"⚠️ Стартовая карточка сброшена на 1 (была больше нового лимита)")
                    
                    print(f"✓ Лимит карточек установлен и сохранен: {cards_limit}")
                    break
                else:
                    print("Ошибка: Лимит должен быть от 1 до 1000")
                    
            except ValueError:
                print("Ошибка: Введите число")
            except KeyboardInterrupt:
                print("\nНастройка отменена")
                break
    
    def configure_generations_per_card(self):
        """Интерактивная настройка количества генераций на карточку"""
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
                    DELAYS['GENERATION_WAIT'] = wait_time
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