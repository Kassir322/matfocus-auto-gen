"""
Обработка файлов с промптами
"""
import os
import re

class FileHandler:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
    
    def load_prompts(self):
        """Загружает промпты из файла в новом формате (лицо/оборот с названием карточки)"""
        prompts_file = self.settings_manager.get('PROMPTS_FILE')
        print(f"[ПАРСЕР] Загружаем промпты из файла: {prompts_file}")
        prompts_by_card = {}
        card_names = {}  # Словарь для хранения названий карточек
        
        try:
            if not os.path.exists(prompts_file):
                print(f"[ОШИБКА] Файл {prompts_file} не найден!")
                return prompts_by_card
                
            for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
                try:
                    with open(prompts_file, 'r', encoding=encoding) as file:
                        print(f"[ЗАГРУЗКА] Используется кодировка: {encoding}")
                        
                        # Новый regex для формата "Карточка X лицо Название - Промпт Y: текст"
                        # Поддержка как старого формата (без названия), так и нового (с названием)
                        pattern = r'Карточка (\d+) (лицо|оборот) ([^-]+) - Промпт (\d+): (.+)'
                        
                        for line_num, line in enumerate(file, 1):
                            line = line.strip()
                            if line and 'Карточка' in line:
                                match = re.search(pattern, line)
                                if match:
                                    card_num = int(match.group(1))
                                    side_type = match.group(2)  # "лицо" или "оборот"
                                    card_name = match.group(3).strip()  # Название карточки
                                    prompt_num = int(match.group(4))
                                    prompt_text = match.group(5)
                                    
                                    # Сохраняем название карточки (если еще не сохранено)
                                    if card_num not in card_names:
                                        card_names[card_num] = card_name
                                    elif card_names[card_num] != card_name:
                                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} имеет разное название в разных строках!")
                                    
                                    # Инициализация структуры для карточки
                                    if card_num not in prompts_by_card:
                                        prompts_by_card[card_num] = {}
                                    
                                    # Инициализация структуры для пары промптов
                                    if prompt_num not in prompts_by_card[card_num]:
                                        prompts_by_card[card_num][prompt_num] = {}
                                    
                                    # Сохранение промпта по типу стороны
                                    prompts_by_card[card_num][prompt_num][side_type] = prompt_text
                                    
                                else:
                                    print(f"[ПРЕДУПРЕЖДЕНИЕ] Строка {line_num} не соответствует формату: {line[:50]}...")
                        break
                        
                except UnicodeDecodeError:
                    continue
            
            # Валидация полноты пар и преобразование в финальную структуру
            valid_prompts = {}
            total_pairs = 0
            
            for card_num in sorted(prompts_by_card.keys()):
                valid_pairs = []
                card_name = card_names.get(card_num, f"Карточка {card_num}")  # Название карточки или по умолчанию
                
                for pair_num in sorted(prompts_by_card[card_num].keys()):
                    pair_dict = prompts_by_card[card_num][pair_num]
                    
                    # Проверка полноты пары
                    if 'лицо' not in pair_dict:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} ({card_name}), Пара {pair_num}: отсутствует 'лицо'")
                    if 'оборот' not in pair_dict:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} ({card_name}), Пара {pair_num}: отсутствует 'оборот'")
                    
                    # Пара считается валидной только если есть оба промпта
                    if 'лицо' in pair_dict and 'оборот' in pair_dict:
                        valid_pairs.append(pair_dict)
                        total_pairs += 1
                    else:
                        print(f"[ПРЕДУПРЕЖДЕНИЕ] Карточка {card_num} ({card_name}), Пара {pair_num}: неполная пара, пропускается")
                
                if valid_pairs:
                    # Сохраняем структуру: номер карточки -> (название, список пар)
                    valid_prompts[card_num] = (card_name, valid_pairs)
            
            print(f"[ЗАГРУЗКА] Загружено {len(valid_prompts)} карточек с промптами")
            print(f"[ЗАГРУЗКА] Найдено {total_pairs} полных пар промптов")
            print(f"[ЗАГРУЗКА] Будет создано {total_pairs * 2} изображений")
            
            if valid_prompts:
                min_card = min(valid_prompts.keys())
                max_card = max(valid_prompts.keys())
                print(f"[ЗАГРУЗКА] Карточки от {min_card} до {max_card}")
            
            return valid_prompts
            
        except Exception as e:
            print(f"[ОШИБКА] При загрузке промптов: {e}")
            return {}
    
    def get_cards_to_process(self):
        """Получает список карточек для обработки в формате, совместимом с режимом генерации"""
        all_prompts = self.load_prompts()
        if not all_prompts:
            return []
        
        available_cards = sorted(all_prompts.keys())
        start_card = self.settings_manager.get('START_FROM_CARD')
        cards_to_process = self.settings_manager.get('CARDS_TO_PROCESS')
        generation_mode = self.settings_manager.get('GENERATION_MODE')
        
        # Вычисляем конечную карточку для логирования
        end_card = start_card + cards_to_process - 1
        
        print(f"[ПАРСЕР] Доступные карточки: {available_cards}")
        print(f"[ПАРСЕР] Диапазон: карточки {start_card}-{end_card}")
        print(f"[ПАРСЕР] Будет обработано карточек: {cards_to_process}")
        print(f"[ПАРСЕР] Режим генерации: {generation_mode}")
        
        cards_to_process_list = [] 
        cards_processed_count = 0
        
        for card_num in available_cards:
            if card_num >= start_card:
                # Новая структура: (название, список пар)
                card_name, pairs_list = all_prompts[card_num]
                print(f"[ПАРСЕР] Карточка {card_num} ({card_name}): {len(pairs_list)} пар")
                
                if generation_mode in ['multi_format', 'multi_format_with_refs']:
                    # Для мультиформатного режима возвращаем кортеж (номер, название, список пар)
                    cards_to_process_list.append((card_num, card_name, pairs_list))
                else:
                    # Для стандартного режима преобразуем пары в список промптов
                    prompts_list = []
                    for pair in pairs_list:
                        if 'лицо' in pair:
                            prompts_list.append(pair['лицо'])
                        if 'оборот' in pair:
                            prompts_list.append(pair['оборот'])
                    print(f"[ПАРСЕР] Карточка {card_num}: преобразовано в {len(prompts_list)} промптов")
                    cards_to_process_list.append((card_num, card_name, prompts_list))
                
                cards_processed_count += 1
                
                # Останавливаемся после обработки нужного количества карточек
                if cards_processed_count >= cards_to_process:
                    print(f"[ПАРСЕР] Достигнут лимит карточек: {cards_processed_count}/{cards_to_process}")
                    break
        
        print(f"[ПАРСЕР] Итого карточек для обработки: {len(cards_to_process_list)}")
        return cards_to_process_list

    def test_new_format(self):
        """Тестовый метод для проверки нового формата"""
        print("=== ТЕСТ НОВОГО ФОРМАТА ===")
        
        # Временно меняем файл на тестовый
        original_file = self.settings_manager.get('PROMPTS_FILE')
        self.settings_manager.set('PROMPTS_FILE', 'data/test_new_format.txt')
        
        try:
            prompts_data = self.load_prompts()
            
            print(f"Карточек загружено: {len(prompts_data)}")
            for card_num, pairs_list in prompts_data.items():
                print(f"Карточка {card_num}: {len(pairs_list)} пар")
                for i, pair in enumerate(pairs_list, 1):
                    print(f"  Пара {i}: лицо='{pair['лицо'][:30]}...', оборот='{pair['оборот'][:30]}...'")
            
            return True
            
        except Exception as e:
            print(f"Ошибка в тесте: {e}")
            return False
        finally:
            # Восстанавливаем оригинальный файл
            self.settings_manager.set('PROMPTS_FILE', original_file)